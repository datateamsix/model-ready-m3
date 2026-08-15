"""Deterministic Meridian EDA gate. Agent prose never owns ERROR vs MODEL_READY."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.errors import ValidationBlockedError
from app.core.meridian_eda_contracts import (
    M3EDAAnalysis,
    MeridianEDAReceipt,
    MeridianEDASeverity,
    count_severities,
)


def load_eda_receipt(value: MeridianEDAReceipt | dict[str, Any] | str | Path) -> MeridianEDAReceipt:
    if isinstance(value, MeridianEDAReceipt):
        return value
    if isinstance(value, dict):
        return MeridianEDAReceipt.model_validate(value)
    return MeridianEDAReceipt.model_validate_json(Path(value).read_text(encoding="utf-8"))


def evaluate_meridian_eda_gate(
    *,
    receipt: MeridianEDAReceipt | dict[str, Any] | str | Path,
    html_path: str | Path | None = None,
    html_persisted: bool | None = None,
) -> dict[str, Any]:
    receipt_obj = load_eda_receipt(receipt)
    html_ok = bool(html_persisted)
    if html_path is not None:
        path = Path(html_path)
        html_ok = path.is_file() and path.stat().st_size > 0
    elif receipt_obj.html_report_uri:
        html_ok = True
    findings = list(receipt_obj.findings)
    severity = count_severities(findings)
    errors = [item.finding_id for item in findings if item.severity == MeridianEDASeverity.ERROR]
    evidence = {
        "html_persisted": html_ok,
        "receipt_status": receipt_obj.status,
        "posterior_sampling": receipt_obj.posterior_sampling,
        "model_fitted": receipt_obj.model_fitted,
        "prior_approved_for_final_modeling": receipt_obj.prior_context.approved_for_final_modeling,
        "prior_used_for": receipt_obj.prior_context.used_for,
        **severity,
        "error_finding_ids": errors,
    }
    if not html_ok:
        raise ValidationBlockedError(f"Meridian EDA HTML report missing: {evidence}")
    if receipt_obj.posterior_sampling or receipt_obj.model_fitted:
        raise ValidationBlockedError(f"Meridian EDA illegally fitted a model: {evidence}")
    if receipt_obj.prior_context.approved_for_final_modeling:
        raise ValidationBlockedError(
            f"EDA priors cannot be approved for final modeling: {evidence}"
        )
    if not findings and severity["max_severity"] != "INFO":
        raise ValidationBlockedError(f"Meridian EDA receipt is internally inconsistent: {evidence}")
    if errors:
        return {
            "status": "FAIL",
            "outcome": "EDA_BLOCKED",
            "review_recommended": True,
            "evidence": evidence,
        }
    return {
        "status": "PASS",
        "outcome": "EDA_PASS",
        "review_recommended": severity["attention_count"] > 0,
        "evidence": evidence,
    }


def validate_eda_analysis(
    analysis: M3EDAAnalysis | dict[str, Any],
    receipt: MeridianEDAReceipt,
) -> M3EDAAnalysis:
    if isinstance(analysis, M3EDAAnalysis):
        obj = analysis
    else:
        obj = M3EDAAnalysis.model_validate(analysis)
    known = {item.finding_id for item in receipt.findings}
    unknown = sorted(obj.referenced_finding_ids() - known)
    if unknown:
        raise ValidationBlockedError(
            f"M3 EDA analysis references unknown finding IDs: {unknown}"
        )
    return obj


def default_eda_analysis(
    receipt: MeridianEDAReceipt, *, source_uri: str | None = None
) -> M3EDAAnalysis:
    errors = [item.finding_id for item in receipt.findings if item.severity == "ERROR"]
    attention = [item.finding_id for item in receipt.findings if item.severity == "ATTENTION"]
    info = [item.finding_id for item in receipt.findings if item.severity == "INFO"]
    action = "EDA_BLOCKED" if errors else "MODEL_READY"
    summary = (
        "Official Meridian EDA completed. This summary lists source finding IDs "
        "from the Meridian receipt; it is not a substitute for agent interpretation."
    )
    return M3EDAAnalysis(
        run_id=receipt.run_id,
        source_eda_receipt_uri=source_uri or receipt.html_report_uri,
        analysis_source="DETERMINISTIC_RECEIPT_SUMMARY",
        executive_summary=summary,
        overall_assessment=action,
        blocking_findings=errors,
        attention_findings=attention,
        informational_findings=info,
        recommended_handoff_action=action,
        recommendations=[],
    )


def render_pre_modeling_handoff(
    *,
    run_id: str,
    data_engineering: dict[str, Any],
    model_input: dict[str, Any],
    destination: dict[str, Any],
    receipt: MeridianEDAReceipt,
    analysis: M3EDAAnalysis,
    eda_gate: dict[str, Any],
) -> str:
    lines = [
        "# Pre-modeling handoff",
        "",
        "## Run",
        f"- run_id: `{run_id}`",
        f"- target: `{receipt.target_model}`",
        "",
        "## Data Engineering Summary",
        f"- detected issues: {data_engineering.get('detected')}",
        f"- resolved issues: {data_engineering.get('resolved')}",
        f"- open issues: {data_engineering.get('open')}",
        "",
        "## Model Input",
        f"- endpoint: `{model_input.get('endpoint')}`",
        f"- fingerprint: `{model_input.get('fingerprint')}`",
        f"- rows: {model_input.get('rows')}",
        f"- columns: {model_input.get('columns')}",
        "",
        "## Destination Verification",
        f"- versioned table: `{destination.get('versioned_table')}`",
        f"- consumption view: `{destination.get('consumption_view')}`",
        f"- physical schema: {destination.get('physical_schema_status')}",
        "",
        "## Meridian EDA",
        f"- package: `{receipt.meridian.get('version')}`",
        f"- html: `{receipt.html_report_uri}`",
        f"- max severity: `{receipt.severity_summary.get('max_severity')}`",
        f"- ERROR: {receipt.severity_summary.get('error_count', 0)}",
        f"- ATTENTION: {receipt.severity_summary.get('attention_count', 0)}",
        f"- INFO: {receipt.severity_summary.get('info_count', 0)}",
        f"- gate: `{eda_gate.get('status')}`",
        f"- review_recommended: `{eda_gate.get('review_recommended')}`",
        "",
        "## EDA Category Summary",
    ]
    for key, payload in (receipt.categories or {}).items():
        lines.append(
            f"- {key}: errors={payload.get('error_count', 0)} "
            f"attention={payload.get('attention_count', 0)} "
            f"info={payload.get('info_count', 0)} applicable={payload.get('applicable')}"
        )
    lines.extend(
        [
            "",
            "## M3 Analytical Assessment",
            analysis.executive_summary,
            "",
            analysis.overall_assessment,
            "",
            "## Recommendations",
        ]
    )
    if analysis.recommendations:
        for rec in analysis.recommendations:
            lines.append(
                f"- `{rec.recommendation_id}` ({rec.priority}, {rec.evidence_type}): "
                f"{rec.recommendation} source={','.join(rec.source_finding_ids)}"
            )
    else:
        lines.append("- None supplied beyond official Meridian findings.")
    lines.extend(["", "## Items for Modeler Review"])
    if analysis.modeler_review_items:
        lines.extend(f"- {item}" for item in analysis.modeler_review_items)
    elif analysis.attention_findings:
        lines.extend(f"- `{item}`" for item in analysis.attention_findings)
    else:
        lines.append("- No ATTENTION findings.")
    lines.extend(
        [
            "",
            "## Prior Context",
            f"- source: `{receipt.prior_context.source}`",
            f"- used_for: `{receipt.prior_context.used_for}`",
            f"- approved_for_final_modeling: `{receipt.prior_context.approved_for_final_modeling}`",
            f"- n_draws_prior: `{receipt.prior_context.n_draws_prior}`",
            f"- seed: `{receipt.prior_context.seed}`",
            "",
            "## Handoff Status",
            f"- recommended_action: `{analysis.recommended_handoff_action}`",
            "- next_role: DATA SCIENTIST / MODELER",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def finding_ids(receipt: MeridianEDAReceipt) -> set[str]:
    return {item.finding_id for item in receipt.findings}


def compact_category_payload(receipt: MeridianEDAReceipt) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, payload in receipt.categories.items():
        compact[key] = {
            "max": _category_max(payload),
            "errors": payload.get("error_count", 0),
            "attention": payload.get("attention_count", 0),
            "info": payload.get("info_count", 0),
            "finding_ids": payload.get("finding_ids") or [],
        }
    return compact


def _category_max(payload: dict[str, Any]) -> str:
    if payload.get("error_count"):
        return MeridianEDASeverity.ERROR.value
    if payload.get("attention_count"):
        return MeridianEDASeverity.ATTENTION.value
    return MeridianEDASeverity.INFO.value
