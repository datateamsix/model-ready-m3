"""Serialize official Meridian EDAOutcome objects into ModelReady receipts.

Does not recompute Meridian statistics. Compact artifacts drop large arrays.
"""

from __future__ import annotations

from typing import Any

from app.core.meridian_eda_contracts import (
    CATEGORY_KEYS,
    CHECK_TYPE_TO_CATEGORY,
    MeridianEDACategorySummary,
    MeridianEDAFinding,
    MeridianEDAPriorContext,
    MeridianEDAReceipt,
    category_for_check,
    count_severities,
)


def _enum_name(value: Any) -> str | None:
    if value is None:
        return None
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    text = str(value)
    return text.rsplit(".", 1)[-1]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return list(value)


def compact_artifact(artifact: Any, *, check_type: str, index: int) -> dict[str, Any]:
    level = _enum_name(getattr(artifact, "level", None))
    ref = f"{check_type}.{level or 'UNKNOWN'}.{index:02d}"
    payload: dict[str, Any] = {
        "artifact_ref": ref,
        "check_type": check_type,
        "analysis_level": level,
        "artifact_type": type(artifact).__name__,
    }
    for attr in (
        "variable",
        "extreme_corr_threshold",
        "kpi_stdev",
        "prior_negative_baseline_prob",
        "n_geos",
        "n_times",
        "n_knots",
        "n_controls",
        "n_treatments",
        "n_parameters",
        "n_data_points",
        "ratio",
    ):
        if hasattr(artifact, attr):
            payload[attr] = _json_scalar(getattr(artifact, attr))
    for attr, limit in (
        ("extreme_corr_var_pairs", 5),
        ("outlier_df", 5),
        ("cost_media_unit_inconsistency_df", 5),
    ):
        frame = getattr(artifact, attr, None)
        compact = _frame_head(frame, limit)
        if compact is not None:
            payload[attr] = compact
    return payload


def _json_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _json_scalar(item())
        except Exception:
            return str(value)
    try:
        return float(value)
    except Exception:
        return str(value)


def _frame_head(frame: Any, limit: int) -> list[dict[str, Any]] | None:
    if frame is None:
        return None
    to_dict = getattr(frame, "to_dict", None)
    if not callable(to_dict):
        return None
    try:
        records = to_dict(orient="records")
    except TypeError:
        return None
    if not isinstance(records, list):
        return None
    compact: list[dict[str, Any]] = []
    for row in records[:limit]:
        if isinstance(row, dict):
            compact.append({str(key): _json_scalar(val) for key, val in row.items()})
    return compact


def serialize_outcomes(
    outcomes: list[Any],
    *,
    run_id: str,
    source: dict[str, Any],
    meridian: dict[str, Any],
    prior_context: MeridianEDAPriorContext,
    html_report_uri: str | None,
    eda_config_uri: str | None,
    started_at: Any,
    completed_at: Any,
    duration_seconds: float | None,
) -> MeridianEDAReceipt:
    findings: list[MeridianEDAFinding] = []
    artifacts: list[dict[str, Any]] = []
    counters: dict[tuple[str, str, str, str], int] = {}
    successful = 0
    runtime_errors = 0
    for outcome in outcomes:
        check_type = _enum_name(getattr(outcome, "check_type", None))
        if check_type is None:
            continue
        category = category_for_check(check_type)
        outcome_findings = _as_list(getattr(outcome, "findings", None))
        outcome_artifacts = _as_list(getattr(outcome, "analysis_artifacts", None))
        artifact_by_id: dict[int, str] = {}
        for index, artifact in enumerate(outcome_artifacts, start=1):
            compact = compact_artifact(artifact, check_type=check_type, index=index)
            artifacts.append(compact)
            artifact_by_id[id(artifact)] = compact["artifact_ref"]
        if any(
            _enum_name(getattr(item, "finding_cause", None)) == "RUNTIME_ERROR"
            for item in outcome_findings
        ):
            runtime_errors += 1
        else:
            successful += 1
        for finding in outcome_findings:
            severity = _enum_name(getattr(finding, "severity", None)) or "INFO"
            cause = _enum_name(getattr(finding, "finding_cause", None)) or "NONE"
            associated = getattr(finding, "associated_artifact", None)
            if associated is not None:
                level = _enum_name(getattr(associated, "level", None))
            else:
                level = None
            key = (check_type, level or "NA", cause, severity)
            counters[key] = counters.get(key, 0) + 1
            finding_id = f"{check_type}.{level or 'NA'}.{cause}.{severity}.{counters[key]:02d}"
            findings.append(
                MeridianEDAFinding(
                    finding_id=finding_id,
                    check_type=check_type,
                    report_category=category,
                    severity=severity,
                    finding_cause=cause,
                    explanation=str(getattr(finding, "explanation", "") or ""),
                    analysis_level=level,
                    associated_artifact_ref=artifact_by_id.get(id(associated))
                    if associated is not None
                    else None,
                )
            )
    categories = _category_summaries(findings, model_scope=str(source.get("model_scope") or ""))
    severity = count_severities(findings)
    return MeridianEDAReceipt(
        run_id=run_id,
        source=source,
        meridian=meridian,
        eda_config_uri=eda_config_uri,
        html_report_uri=html_report_uri,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration_seconds,
        prior_context=prior_context,
        severity_summary=severity,
        check_summary={
            "total_checks": len(outcomes),
            "successful_checks": successful,
            "runtime_error_checks": runtime_errors,
            "official_check_types": list(CHECK_TYPE_TO_CATEGORY),
        },
        categories={item.category: item.model_dump(mode="json") for item in categories},
        findings=findings,
        analysis_artifacts=artifacts,
        status="EDA_COMPLETE",
    )


def _category_summaries(
    findings: list[MeridianEDAFinding], *, model_scope: str
) -> list[MeridianEDACategorySummary]:
    grouped: dict[str, list[MeridianEDAFinding]] = {key: [] for key in CATEGORY_KEYS}
    for finding in findings:
        grouped.setdefault(finding.report_category, []).append(finding)
    summaries: list[MeridianEDACategorySummary] = []
    for key in CATEGORY_KEYS:
        items = grouped.get(key) or []
        applicable = not (key == "population_scaling" and model_scope.lower() == "national")
        check_types = sorted(
            {check for check, category in CHECK_TYPE_TO_CATEGORY.items() if category == key}
        )
        summaries.append(
            MeridianEDACategorySummary(
                category=key,
                applicable=applicable,
                check_types=check_types,
                error_count=sum(item.severity == "ERROR" for item in items),
                attention_count=sum(item.severity == "ATTENTION" for item in items),
                info_count=sum(item.severity == "INFO" for item in items),
                finding_ids=[item.finding_id for item in items],
            )
        )
    return summaries


def compact_findings_for_agent(findings: list[MeridianEDAFinding]) -> list[dict[str, Any]]:
    return [
        {
            "finding_id": item.finding_id,
            "check_type": item.check_type,
            "report_category": item.report_category,
            "severity": item.severity,
            "finding_cause": item.finding_cause,
            "analysis_level": item.analysis_level,
            "explanation": item.explanation,
        }
        for item in findings
    ]
