"""Deterministic Meridian EDA gate. Agent prose never owns ERROR vs MODEL_READY."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.errors import ValidationBlockedError
from app.core.meridian_eda_contracts import (
    EDA_MODEL_SPEC_DEFAULT,
    EDA_MODEL_SPEC_GEO_TIME_INVARIANT,
    M3EDAAnalysis,
    MeridianCorrectionItem,
    MeridianEDAReceipt,
    MeridianEDASeverity,
    MeridianResolutionStep,
    MeridianUserFeedback,
    count_severities,
)


def knots_identifiable(receipt: MeridianEDAReceipt) -> bool:
    """Official Meridian requires knots < n_time when time-only controls exist."""
    spec = receipt.model_spec
    adequacy = receipt.data_adequacy
    if not adequacy.is_complete():
        return False
    n_knots = _as_number(adequacy.n_knots)
    n_times = _as_number(adequacy.n_times)
    if n_knots is None or n_times is None or n_knots < 1 or n_times < 1:
        return False
    if spec.source == EDA_MODEL_SPEC_GEO_TIME_INVARIANT:
        spec_knots = spec.knots if isinstance(spec.knots, int) else spec.n_knots
        spec_knots_n = _as_number(spec_knots)
        spec_time = _as_number(spec.n_time)
        return (
            spec_knots_n is not None
            and spec_time is not None
            and spec_knots_n < spec_time
            and n_knots < n_times
            and spec_knots_n == n_knots
            and spec_time == n_times
        )
    if spec.n_time is not None and _as_number(spec.n_time) != n_times:
        return False
    return n_knots <= n_times


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


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
    spec = receipt_obj.model_spec
    adequacy = receipt_obj.data_adequacy
    evidence = {
        "html_persisted": html_ok,
        "receipt_status": receipt_obj.status,
        "posterior_sampling": receipt_obj.posterior_sampling,
        "model_fitted": receipt_obj.model_fitted,
        "prior_approved_for_final_modeling": receipt_obj.prior_context.approved_for_final_modeling,
        "prior_used_for": receipt_obj.prior_context.used_for,
        "model_spec_source": spec.source,
        "model_spec_knots": spec.knots,
        "model_spec_n_time": spec.n_time,
        "model_spec_enable_aks": spec.enable_aks,
        "model_spec_approved_for_final_modeling": spec.approved_for_final_modeling,
        "n_geos": adequacy.n_geos,
        "n_times": adequacy.n_times,
        "n_knots": adequacy.n_knots,
        "n_controls": adequacy.n_controls,
        "n_treatments": adequacy.n_treatments,
        "n_parameters": adequacy.n_parameters,
        "n_data_points": adequacy.n_data_points,
        "data_adequacy_ratio": adequacy.ratio,
        "data_adequacy_captured": adequacy.is_complete(),
        "knots_identifiable": knots_identifiable(receipt_obj),
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
    if spec.approved_for_final_modeling or spec.enable_aks:
        raise ValidationBlockedError(
            f"EDA ModelSpec cannot be approved for final modeling or AKS: {evidence}"
        )
    if spec.source not in {EDA_MODEL_SPEC_DEFAULT, EDA_MODEL_SPEC_GEO_TIME_INVARIANT}:
        raise ValidationBlockedError(f"EDA ModelSpec source is not official: {evidence}")
    if not adequacy.is_complete():
        raise ValidationBlockedError(
            f"Official Meridian data-adequacy parameters were not captured: {evidence}"
        )
    if not evidence["knots_identifiable"]:
        raise ValidationBlockedError(
            f"Official Meridian knots are not identifiable for EDA: {evidence}"
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
        "outcome": "PRE_MODELING_COMPLETE",
        "review_recommended": severity["attention_count"] > 0,
        "evidence": evidence,
    }


def build_meridian_feedback(
    *,
    receipt: MeridianEDAReceipt,
    gate: dict[str, Any] | None = None,
) -> MeridianUserFeedback:
    """Official Meridian text only. Agent prose does not invent corrections."""
    errors = [item for item in receipt.findings if item.severity == MeridianEDASeverity.ERROR]
    attention = [
        item for item in receipt.findings if item.severity == MeridianEDASeverity.ATTENTION
    ]
    corrections: list[MeridianCorrectionItem] = []
    if receipt.model_spec.source == EDA_MODEL_SPEC_GEO_TIME_INVARIANT:
        official = receipt.model_spec.reason or ""
        interpretation = (
            "Official Meridian refused default knots=n_time because a time-only "
            "control is perfectly collinear with time. EDA used ModelSpec(knots="
            f"{receipt.model_spec.knots}) for n_time={receipt.model_spec.n_time}. "
            "This is PRE_MODELING_EDA_ONLY and is not a final modeling recommendation."
        )
        corrections.append(
            MeridianCorrectionItem(
                item_id="SYSTEM-KNOTS-FALLBACK",
                owner="SYSTEM_HANDLED",
                agent_can_fix=False,
                source="MERIDIAN_CONSTRUCTION",
                official_feedback=official,
                official_message=official,
                prem3_interpretation=interpretation,
                recommended_user_action=(
                    "Treat knots as an EDA compatibility choice. Final knot "
                    "selection remains a modeler decision."
                ),
                what_to_correct=interpretation,
            )
        )
    for item in errors:
        corrections.append(
            MeridianCorrectionItem(
                item_id=item.finding_id,
                owner="USER_REQUIRED",
                agent_can_fix=False,
                source="MERIDIAN_EDA_FINDING",
                finding_id=item.finding_id,
                severity=item.severity,
                official_feedback=item.explanation,
                official_message=item.explanation,
                prem3_interpretation=_error_interpretation(item.check_type),
                recommended_user_action=_error_action(item.check_type),
                what_to_correct=item.explanation,
            )
        )
    for item in attention:
        corrections.append(
            MeridianCorrectionItem(
                item_id=item.finding_id,
                owner="USER_REVIEW",
                agent_can_fix=False,
                source="MERIDIAN_EDA_FINDING",
                finding_id=item.finding_id,
                severity=item.severity,
                official_feedback=item.explanation,
                official_message=item.explanation,
                prem3_interpretation=(
                    "Official Meridian ATTENTION is review-recommended, not blocking."
                ),
                recommended_user_action="Review with the modeler before final fitting.",
                what_to_correct=item.explanation,
            )
        )
    blocked = bool(errors) or (gate or {}).get("status") == "FAIL"
    official = " ".join(item.explanation for item in errors) if errors else ""
    if blocked:
        status = "EDA_BLOCKED"
        summary = (
            "Official Meridian EDA ran and produced ERROR findings. "
            "M3 cannot autonomously repair these. The user or modeler must correct the input."
        )
        steps = [
            MeridianResolutionStep(
                step=1,
                action="Read the official Meridian ERROR text and affected variables.",
                owner="MODELER",
                evidence_required="Official finding IDs and explanations from the EDA receipt.",
            ),
            MeridianResolutionStep(
                step=2,
                action=_error_action(errors[0].check_type if errors else "DATA_ADEQUACY"),
                owner=_error_owner(errors[0].check_type if errors else "DATA_ADEQUACY"),
                evidence_required="Corrected source export or modeler-approved specification.",
            ),
            MeridianResolutionStep(
                step=3,
                action="Rerun ModelReady after the official condition is resolved.",
                owner="ANALYST",
                evidence_required="Updated raw package or documented modeler decision.",
            ),
        ]
        return MeridianUserFeedback(
            run_id=receipt.run_id,
            status=status,
            meridian_accepted_input=True,
            eda_ran=True,
            user_action_required=True,
            summary=summary,
            corrections=corrections,
            resolution_id=f"{receipt.run_id}-eda-error",
            resolution_status="USER_REQUIRED",
            agent_can_fix=False,
            source_type="EDA_ERROR",
            source_finding_ids=[item.finding_id for item in errors],
            official_message=official,
            problem_summary=summary,
            why_it_matters=(
                "Official ERROR findings very likely prevent model convergence. "
                "Posterior sampling is blocked until they are resolved."
            ),
            recommended_steps=steps,
            retry_condition="Official Meridian EDA returns zero ERROR findings.",
            safe_to_model=False,
            feasibility="USER_REQUIRED",
            fixability=_error_fixability(errors[0].check_type if errors else "DATA_ADEQUACY"),
        )
    review = bool(attention)
    return MeridianUserFeedback(
        run_id=receipt.run_id,
        status="PRE_MODELING_COMPLETE",
        meridian_accepted_input=True,
        eda_ran=True,
        user_action_required=False,
        summary=(
            "Official Meridian accepted the input and completed pre-modeling EDA. "
            "ATTENTION items are review-recommended, not agent-fixable."
            if review
            else "Official Meridian accepted the input and completed pre-modeling EDA."
        ),
        corrections=corrections,
        resolution_id=f"{receipt.run_id}-eda-complete",
        resolution_status="MODEL_READY",
        agent_can_fix=False,
        source_type="EDA_ATTENTION" if review else "EDA_COMPLETE",
        source_finding_ids=[item.finding_id for item in attention],
        official_message="",
        problem_summary=(
            "No official ERROR findings. ATTENTION items deserve modeler review."
            if review
            else "No official ERROR or ATTENTION findings."
        ),
        why_it_matters=(
            "ATTENTION does not block MODEL_READY, but final knot/prior choices "
            "remain a modeling decision."
            if review
            else "Official EDA did not flag blocking data issues."
        ),
        recommended_steps=[],
        retry_condition="",
        safe_to_model=True,
        feasibility="MODEL_READY_REVIEW_RECOMMENDED" if review else "MODEL_READY",
        fixability="MODELER_REVIEW_REQUIRED" if review else "AGENT_FIXABLE",
    )


def build_meridian_refusal_feedback(
    *,
    run_id: str,
    official_message: str,
) -> MeridianUserFeedback:
    message = official_message.strip()
    interpretation = (
        "Official Meridian refused to construct the EDA model context. "
        "M3 cannot drop controls, change grain, or choose final knots."
    )
    return MeridianUserFeedback(
        run_id=run_id,
        status="MERIDIAN_INPUT_REJECTED",
        meridian_accepted_input=False,
        eda_ran=False,
        user_action_required=True,
        summary=(
            "Official Meridian rejected the model input before EDA. "
            "M3 cannot autonomously change the rejected variables. "
            "Pass the official feedback to the user."
        ),
        corrections=[
            MeridianCorrectionItem(
                item_id="MERIDIAN-INPUT-REJECTED",
                owner="USER_REQUIRED",
                agent_can_fix=False,
                source="MERIDIAN_CONSTRUCTION",
                official_feedback=message,
                official_message=message,
                prem3_interpretation=interpretation,
                recommended_user_action=(
                    "Change the rejected input with the analyst or modeler, then rerun."
                ),
                what_to_correct=message,
            )
        ],
        resolution_id=f"{run_id}-meridian-input-rejected",
        resolution_status="USER_REQUIRED",
        agent_can_fix=False,
        source_type="INPUT_REJECTION",
        official_message=message,
        problem_summary=interpretation,
        why_it_matters=(
            "Meridian will not evaluate this input. Modeling cannot start until "
            "the official construction error is resolved."
        ),
        recommended_steps=[
            MeridianResolutionStep(
                step=1,
                action="Read the official Meridian rejection message.",
                owner="MODELER",
                evidence_required="Unmodified official_message text.",
            ),
            MeridianResolutionStep(
                step=2,
                action=(
                    "Adjust the rejected variable, grain, or data coverage. "
                    "Do not ask M3 to silently drop a control or channel."
                ),
                owner="ANALYST",
                evidence_required="Updated source export or documented modeler decision.",
            ),
            MeridianResolutionStep(
                step=3,
                action="Rerun ModelReady against the corrected package.",
                owner="ANALYST",
                evidence_required="New raw package fingerprint.",
            ),
        ],
        retry_condition="Official Meridian accepts the reconstructed InputData.",
        safe_to_model=False,
        feasibility="USER_REQUIRED",
        fixability="MODELER_REVIEW_REQUIRED",
    )


def _error_interpretation(check_type: str) -> str:
    if check_type == "DATA_ADEQUACY":
        return "The loaded data does not contain enough defensible information to model."
    if check_type in {"PAIRWISE_CORRELATION", "MULTICOLLINEARITY"}:
        return "Severe collinearity is a specification judgment, not an AUTO_SAFE repair."
    if check_type == "KPI_INVARIABILITY":
        return "The KPI does not vary enough for a defensible response model."
    return "Official Meridian marked this check as ERROR. M3 cannot auto-repair it."


def _error_action(check_type: str) -> str:
    if check_type == "DATA_ADEQUACY":
        return (
            "Collect more historical periods, geos, or required population/spend "
            "coverage before retrying."
        )
    if check_type in {"PAIRWISE_CORRELATION", "MULTICOLLINEARITY"}:
        return "Resolve the collinear variables with the modeler. Do not silently drop them."
    if check_type == "KPI_INVARIABILITY":
        return "Provide missing KPI periods or a KPI that actually varies."
    return "Correct the official Meridian ERROR using the finding explanation."


def _error_owner(check_type: str) -> str:
    if check_type == "DATA_ADEQUACY":
        return "DATA_ENGINEER"
    if check_type in {"PAIRWISE_CORRELATION", "MULTICOLLINEARITY"}:
        return "MODELER"
    return "ANALYST"


def _error_fixability(check_type: str) -> str:
    if check_type == "DATA_ADEQUACY":
        return "STRUCTURAL_DATA_GAP"
    if check_type in {"PAIRWISE_CORRELATION", "MULTICOLLINEARITY"}:
        return "MODELER_REVIEW_REQUIRED"
    return "USER_FIXABLE"


def validate_eda_analysis(
    analysis: M3EDAAnalysis | dict[str, Any],
    receipt: MeridianEDAReceipt,
) -> M3EDAAnalysis:
    if isinstance(analysis, M3EDAAnalysis):
        obj = analysis
    else:
        obj = M3EDAAnalysis.model_validate(normalize_eda_analysis(analysis, receipt))
    known = {item.finding_id for item in receipt.findings}
    unknown = sorted(obj.referenced_finding_ids() - known)
    if unknown:
        raise ValidationBlockedError(
            f"M3 EDA analysis references unknown finding IDs: {unknown}"
        )
    return obj


def normalize_eda_analysis(
    analysis: dict[str, Any], receipt: MeridianEDAReceipt
) -> dict[str, Any]:
    """Coerce Gemini interpretation into the typed analysis contract.

    Does not calculate EDA or change official severities.
    """
    recommendations: list[dict[str, Any]] = []
    raw_recs = analysis.get("recommendations") or []
    if isinstance(raw_recs, list):
        for index, item in enumerate(raw_recs, start=1):
            if not isinstance(item, dict):
                continue
            message = str(item.get("recommendation") or item.get("message") or "")
            recommendations.append(
                {
                    "recommendation_id": str(
                        item.get("recommendation_id") or item.get("id") or f"REC-{index:02d}"
                    ),
                    "priority": str(item.get("priority") or "ATTENTION"),
                    "recommendation": message,
                    "rationale": str(item.get("rationale") or item.get("reason") or message),
                    "source_finding_ids": [
                        str(fid)
                        for fid in (
                            item.get("source_finding_ids") or item.get("finding_ids") or []
                        )
                    ],
                    "evidence_type": str(item.get("evidence_type") or "SOURCE_FINDING"),
                }
            )
    summary = (
        analysis.get("executive_summary")
        or analysis.get("summary")
        or analysis.get("assessment")
        or default_eda_analysis(receipt).executive_summary
    )
    return {
        "run_id": analysis.get("run_id") or receipt.run_id,
        "source_eda_receipt_uri": analysis.get("source_eda_receipt_uri"),
        "analysis_source": analysis.get("analysis_source") or "AGENT",
        "executive_summary": str(summary),
        "overall_assessment": str(analysis.get("overall_assessment") or ""),
        "blocking_findings": list(analysis.get("blocking_findings") or []),
        "attention_findings": list(analysis.get("attention_findings") or []),
        "informational_findings": list(analysis.get("informational_findings") or []),
        "category_analysis": analysis.get("category_analysis")
        if isinstance(analysis.get("category_analysis"), dict)
        else {},
        "cross_category_observations": list(
            analysis.get("cross_category_observations") or []
        ),
        "recommendations": recommendations,
        "modeler_review_items": list(analysis.get("modeler_review_items") or []),
        "recommended_handoff_action": str(
            analysis.get("recommended_handoff_action") or "MODEL_READY"
        ),
    }


def accept_eda_analysis(
    analysis: M3EDAAnalysis | dict[str, Any] | None,
    receipt: MeridianEDAReceipt,
    *,
    source_uri: str | None = None,
) -> M3EDAAnalysis:
    """Keep Gemini interpretation optional. Deterministic default owns the fallback."""
    if analysis is None:
        return default_eda_analysis(receipt, source_uri=source_uri)
    try:
        return validate_eda_analysis(analysis, receipt)
    except (ValidationError, ValidationBlockedError, ValueError):
        return default_eda_analysis(receipt, source_uri=source_uri)


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
    feedback = build_meridian_feedback(receipt=receipt, gate=eda_gate)
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
        "## Official ModelSpec (EDA only)",
        f"- source: `{receipt.model_spec.source}`",
        f"- knots: `{receipt.model_spec.knots}`",
        f"- n_time: `{receipt.model_spec.n_time}`",
        f"- enable_aks: `{receipt.model_spec.enable_aks}`",
        f"- approved_for_final_modeling: `{receipt.model_spec.approved_for_final_modeling}`",
        "",
        "## Official data-adequacy parameters",
        f"- n_geos: `{receipt.data_adequacy.n_geos}`",
        f"- n_times: `{receipt.data_adequacy.n_times}`",
        f"- n_knots: `{receipt.data_adequacy.n_knots}`",
        f"- n_controls: `{receipt.data_adequacy.n_controls}`",
        f"- n_treatments: `{receipt.data_adequacy.n_treatments}`",
        f"- n_parameters: `{receipt.data_adequacy.n_parameters}`",
        f"- n_data_points: `{receipt.data_adequacy.n_data_points}`",
        f"- ratio: `{receipt.data_adequacy.ratio}`",
        "",
        "## User resolution pack",
        f"- status: `{feedback.status}`",
        f"- resolution_status: `{feedback.resolution_status}`",
        f"- feasibility: `{feedback.feasibility}`",
        f"- fixability: `{feedback.fixability}`",
        f"- agent_can_fix: `{feedback.agent_can_fix}`",
        f"- source_type: `{feedback.source_type}`",
        f"- meridian_accepted_input: `{feedback.meridian_accepted_input}`",
        f"- eda_ran: `{feedback.eda_ran}`",
        f"- user_action_required: `{feedback.user_action_required}`",
        f"- safe_to_model: `{feedback.safe_to_model}`",
        f"- official_message: {feedback.official_message or 'None'}",
        f"- prem3_interpretation: {feedback.problem_summary}",
        f"- why_it_matters: {feedback.why_it_matters}",
        f"- retry_condition: {feedback.retry_condition or 'None'}",
    ]
    if feedback.corrections:
        for item in feedback.corrections:
            lines.append(
                f"- `{item.item_id}` owner={item.owner} agent_can_fix={item.agent_can_fix}: "
                f"{item.what_to_correct}"
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## EDA Category Summary",
        ]
    )
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
