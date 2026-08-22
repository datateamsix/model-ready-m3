"""Orchestrate PreM3 run intelligence from a verified diagnostic snapshot."""

from __future__ import annotations

from typing import Any

from app.domain.intelligence.builder import load_current_domain_view
from app.intelligence.analyzers import (
    analyze_channel_scope_candidates,
    analyze_channel_spend_distribution,
    analyze_collinearity,
    analyze_geo_coverage,
    analyze_history_sufficiency,
    analyze_media_spend_consistency,
    analyze_media_variation,
    analyze_population_relationships,
    analyze_reach_frequency_structure,
    analyze_spend_range,
    check_pre_period_media,
    classify_missing_data_evidence,
)
from app.intelligence.contracts import CALCULATOR_VERSION
from app.intelligence.feasibility import build_computational_readiness, build_modeling_feasibility
from app.intelligence.fingerprint import content_fingerprint_payload
from app.intelligence.parameter import compute_parameter_budget
from app.intelligence.registry import load_intelligence_config
from app.intelligence.reports import (
    build_guided_remediation,
    build_pre_eda_report,
    build_semantic_interview_markdown,
)
from app.intelligence.scenarios import simulate_model_scope_scenarios
from app.intelligence.semantic import (
    detect_semantic_question_triggers,
    generate_semantic_readiness_interview,
)
from app.intelligence.snapshot import DiagnosticSnapshot
from app.mel.models import MelError
from app.mel.promote import load_active_view
from app.mel.routing_apply import apply_routing_plan, observed_semantic_conditions


def run_pre_eda_diagnostics(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    budget = compute_parameter_budget(snapshot)
    history = analyze_history_sufficiency(snapshot)
    pre_period = check_pre_period_media(snapshot)
    spend = analyze_channel_spend_distribution(snapshot)
    variation = analyze_media_variation(snapshot)
    spend_range = analyze_spend_range(snapshot)
    geo = analyze_geo_coverage(snapshot)
    population = analyze_population_relationships(snapshot)
    collinearity = analyze_collinearity(snapshot)
    consistency = analyze_media_spend_consistency(snapshot)
    missing = classify_missing_data_evidence(snapshot)
    rf = analyze_reach_frequency_structure(snapshot)
    candidates = analyze_channel_scope_candidates(
        snapshot, spend=spend, variation=variation, parameter_budget=budget
    )
    triggers = detect_semantic_question_triggers(snapshot, spend=spend)
    interview = generate_semantic_readiness_interview(snapshot, triggers=triggers)
    domain = _domain_view_meta()
    view = load_active_view()
    learned_routing = apply_routing_plan(
        view,
        observed_conditions=observed_semantic_conditions(interview),
    )
    config = load_intelligence_config()
    diagnostics = {
        "parameter_budget": budget,
        "history": history,
        "pre_period_media": pre_period,
        "spend_distribution": spend,
        "media_variation": variation,
        "spend_range": spend_range,
        "geo_coverage": geo,
        "population_relationships": population,
        "collinearity": collinearity,
        "media_spend_consistency": consistency,
        "missingness_evidence": missing,
        "reach_frequency": rf,
        "scope_candidates": candidates,
        "semantic_triggers": triggers,
        "semantic_interview": interview,
        "source_endpoint": snapshot.endpoint.model_dump(mode="json"),
    }
    computational = build_computational_readiness(diagnostics)
    official_eda = snapshot.eda_receipt
    feasibility = build_modeling_feasibility(
        snapshot,
        computational=computational,
        semantic=interview,
        official_eda=official_eda,
    )
    guidance = build_guided_remediation(diagnostics)
    summary = _behavior_summary(snapshot, diagnostics, interview, feasibility, guidance)
    receipt = {
        "run_id": snapshot.endpoint.run_id,
        "finding_origin": "PREM3_PRE_EDA",
        "source_endpoint": snapshot.endpoint.model_dump(mode="json"),
        "resolved_source": snapshot.endpoint.resolved_source,
        "input_fingerprint": snapshot.endpoint.input_fingerprint,
        "schema_fingerprint": snapshot.endpoint.schema_fingerprint,
        "domain_view_version": domain["domain_view_version"],
        "domain_view_fingerprint": domain["domain_view_fingerprint"],
        "rule_registry_version": config.version,
        "intelligence_version": config.intelligence_version,
        "calculator_version": CALCULATOR_VERSION,
        "n_knots": snapshot.knots.n_knots,
        "n_knots_source": snapshot.knots.n_knots_source.value,
        "diagnostics": {
            "parameter_budget": _without_finding_blob(budget),
            "history": history,
            "pre_period_media": pre_period,
            "spend_distribution": spend,
            "media_variation": variation,
            "spend_range": spend_range,
            "geo_coverage": geo,
            "population_relationships": population,
            "collinearity": collinearity,
            "media_spend_consistency": consistency,
            "missingness_evidence": missing,
            "reach_frequency": rf,
            "scope_candidates": candidates,
        },
        "computational_readiness": computational,
        "semantic_trigger_summary": {
            "trigger_count": len(triggers),
            "families": [item["question_family"] for item in triggers],
        },
        "learned_routing": {
            "retrieved": learned_routing["retrieved"],
            "applicability_match": learned_routing["applicability_match"],
            "retrieved_claim_ids": learned_routing["retrieved_claim_ids"],
            "retrieval_reason": learned_routing["retrieval_reason"],
            "records": learned_routing["records"],
            "recommended_presentation_order": learned_routing[
                "recommended_presentation_order"
            ],
            "handoff_action_order": learned_routing["handoff_action_order"],
            "applied": learned_routing["applied"],
        },
        "official_meridian_findings_included": False,
    }
    receipt["artifact_fingerprint"] = content_fingerprint_payload(receipt)
    report_md = build_pre_eda_report({**summary, "guided_remediation": guidance})
    interview_md = build_semantic_interview_markdown(interview)
    return {
        "receipt": receipt,
        "report_markdown": report_md,
        "computational_readiness": computational,
        "modeling_feasibility": feasibility,
        "semantic_interview": interview,
        "semantic_interview_markdown": interview_md,
        "guided_remediation": guidance,
        "learned_routing": learned_routing,
        "summary": summary,
        "snapshot_meta": {
            "row_count": snapshot.endpoint.row_count,
            "n_geos": snapshot.n_geos,
            "n_times": snapshot.n_times,
        },
    }


def run_scope_scenarios(
    snapshot: DiagnosticSnapshot,
    *,
    diagnostics: dict[str, Any] | None = None,
    scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    bundle = diagnostics or run_pre_eda_diagnostics(snapshot)
    receipt = bundle["receipt"]
    result = simulate_model_scope_scenarios(
        snapshot,
        scenarios,
        baseline_budget=receipt["diagnostics"]["parameter_budget"]
        if "parameter_budget" in receipt["diagnostics"]
        else bundle["receipt"]["diagnostics"]["parameter_budget"],
        scope_candidates=receipt["diagnostics"]["scope_candidates"],
    )
    result["run_id"] = snapshot.endpoint.run_id
    result["input_fingerprint"] = snapshot.endpoint.input_fingerprint
    result["domain_view_version"] = receipt["domain_view_version"]
    result["domain_view_fingerprint"] = receipt["domain_view_fingerprint"]
    result["artifact_fingerprint"] = content_fingerprint_payload(result)
    return result


def _without_finding_blob(budget: dict[str, Any]) -> dict[str, Any]:
    return budget


def _domain_view_meta() -> dict[str, str]:
    try:
        view = load_active_view()
    except MelError:
        view = load_current_domain_view()
    if view is None:
        return {"domain_view_version": "missing", "domain_view_fingerprint": "missing"}
    return {
        "domain_view_version": view.domain_view_version,
        "domain_view_fingerprint": view.content_fingerprint,
    }


def _behavior_summary(
    snapshot: DiagnosticSnapshot,
    diagnostics: dict[str, Any],
    interview: dict[str, Any],
    feasibility: dict[str, Any],
    guidance: list[dict[str, Any]],
) -> dict[str, Any]:
    budget = diagnostics["parameter_budget"]
    history = diagnostics["history"]["observed_fact"]
    spend = diagnostics["spend_distribution"]
    variation = diagnostics["media_variation"]
    pre = diagnostics["pre_period_media"]
    assess = (
        f"The verified input contains {snapshot.endpoint.row_count} rows, "
        f"{snapshot.n_geos} geos, and {snapshot.n_times} {snapshot.time_grain} periods "
        f"({history.get('first_kpi_period')} to {history.get('last_kpi_period')}). "
        "The data contract used for these diagnostics is the independently verified "
        "model-consumption endpoint. "
        f"Parameter pressure is {budget['interpretation']['pressure_band']} "
        f"(lenient ratio {budget['lenient']['ratio']})."
    )
    advise = (
        "The parameter-pressure conclusion is a PreM3/MMM heuristic "
        f"({budget['interpretation']['knowledge_class']}), not an official Meridian failure. "
        "Official Meridian EDA remains a separate evidence system. "
        "Channel consolidation and knot changes remain approval/modeler-reviewed."
    )
    top = (spend.get("channels") or [{}])[:2]
    weak = variation.get("limited_variation_channels") or []
    insight = (
        f"Top spend channels: {', '.join(item.get('channel', '') for item in top) or 'n/a'}. "
        f"Limited-variation channels: {', '.join(weak) or 'none flagged'}. "
        f"Pre-period media coverage: {pre.get('overall')}. "
        f"Semantic questions triggered: {interview.get('question_count')}."
    )
    next_owner = guidance[0]["responsible_actor"] if guidance else "PREM3"
    guide = (
        "PreM3 can persist these diagnostics and run read-only scope scenarios. "
        "It will not merge channels, drop confounders, impute KPI/controls, "
        "or declare MODEL_READY. "
        f"Likely next owner: {next_owner}. Next system step: official Meridian EDA "
        "against the same verified input."
        if feasibility.get("official_meridian_eda_status") == "PENDING"
        else (
            "Official Meridian EDA status is already persisted; "
            "interpret it separately from PreM3 diagnostics."
        )
    )
    return {
        "assess": {"narrative": assess, "source": "deterministic_state"},
        "advise": {"narrative": advise, "source": "registry_authority"},
        "insight": {"narrative": insight, "source": "run_calculations"},
        "guide": {"narrative": guide, "source": "resolution_contract"},
        "model_ready_not_set": True,
    }
