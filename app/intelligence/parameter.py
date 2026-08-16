"""Parameter-budget diagnostics: lenient, strict, and shadow views.

Ratios are deterministic. Interpretation thresholds are MMM heuristics and
cannot independently block MODEL_READY.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import ValidationBlockedError
from app.intelligence.contracts import (
    AuthorityRef,
    DecisionClass,
    KnowledgeClass,
    Prem3DiagnosticDisposition,
    Prem3PreEdaFinding,
    ResponsibleActor,
)
from app.intelligence.registry import load_intelligence_config, rule_authority
from app.intelligence.snapshot import DiagnosticSnapshot


def compute_parameter_budget(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    config = load_intelligence_config().parameter_budget
    n_geos = snapshot.n_geos
    n_times = snapshot.n_times
    n_knots = snapshot.knots.n_knots
    n_controls = snapshot.n_controls
    n_treatments = snapshot.n_treatments
    n_media = snapshot.n_paid_media + len(snapshot.contract.organic_media)
    if n_geos < 1 or n_times < 1:
        raise ValidationBlockedError("compute_parameter_budget received invalid n_geos or n_times.")
    if n_knots < 1:
        raise ValidationBlockedError("compute_parameter_budget received invalid n_knots.")
    n_data_points = n_geos * n_times
    n_geo_effects = max(n_geos - 1, 0)
    n_parameters_lenient = n_geo_effects + n_knots + n_controls + n_treatments
    n_parameters_strict = (n_treatments * n_geos) + (n_controls * n_geos) + n_knots + n_geo_effects
    factor = float(config.shadow_media_complexity_factor)
    n_parameters_shadow = n_geo_effects + n_knots + n_controls + int(factor * n_media)
    ratio_lenient = _ratio(n_data_points, n_parameters_lenient)
    ratio_strict = _ratio(n_data_points, n_parameters_strict)
    ratio_shadow = _ratio(n_data_points, n_parameters_shadow)
    guidance = float(config.observations_per_parameter_guidance)
    severe = float(config.severe_ratio_guidance)
    pressure = _pressure_band(ratio_lenient, guidance, severe)
    disposition = (
        Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
        if pressure != "ADEQUATE"
        else Prem3DiagnosticDisposition.PASS
    )
    pb001 = rule_authority("PREM3-PB-001")
    finding = Prem3PreEdaFinding(
        finding_id="PREM3-PREEDA-PARAMETER-BUDGET",
        dimension="PARAMETER_PRESSURE",
        disposition=disposition,
        knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
        decision_class=DecisionClass.ADVISORY,
        title="Parameter-pressure diagnostic",
        what_was_calculated=(
            "Lenient, strict/no-pooling, and shadow complexity parameter budgets "
            "from verified n_geos, n_times, n_knots, n_controls, and n_treatments."
        ),
        observed_evidence={
            "n_geos": n_geos,
            "n_times": n_times,
            "n_data_points": n_data_points,
            "n_controls": n_controls,
            "n_treatments": n_treatments,
            "n_media_treatments": n_media,
            "pressure_band": pressure,
            "lenient_ratio": ratio_lenient,
            "strict_ratio": ratio_strict,
            "shadow_ratio": ratio_shadow,
        },
        why_it_matters=(
            "A low observations-per-parameter ratio is a modeling-feasibility signal. "
            "It is not an official Meridian failure and cannot independently deny MODEL_READY."
        ),
        best_practice=(
            "Foundational MMM guidance often cites roughly 7–10 observations per "
            "parameter as a review threshold. Authority: MMM_EVIDENCE_HEURISTIC."
        ),
        recommended_action=(
            "Review history, eligible channel consolidation, or optional non-confounding "
            "scope with the modeler. Do not drop a confirmed confounder to improve the ratio."
        ),
        responsible_actor=ResponsibleActor.MODELER,
        blocks_model_ready=False,
        review_recommended=pressure != "ADEQUATE",
        source_authority=AuthorityRef(
            knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
            decision_class=DecisionClass.ADVISORY,
            rule_id="PREM3-PB-001",
            source_url=str(pb001.get("source_url") or ""),
            source_tier=str(pb001.get("source_tier") or ""),
            blocks_model_ready=False,
            threshold_authority=config.threshold_authority,
        ),
        formula=(
            "n_data_points = n_geos * n_times; "
            "n_parameters_lenient = (n_geos-1)+n_knots+n_controls+n_treatments; "
            "n_parameters_strict = (n_treatments*n_geos)+(n_controls*n_geos)+n_knots+(n_geos-1); "
            "n_parameters_shadow = (n_geos-1)+n_knots+n_controls+(factor*n_media)"
        ),
        assumptions={
            "n_knots": n_knots,
            "n_knots_source": snapshot.knots.n_knots_source.value,
            "n_knots_authority": snapshot.knots.authority,
            "n_knots_scope": snapshot.knots.scope,
            "approved_for_final_modeling": False,
        },
    )
    return {
        "n_geos": n_geos,
        "n_times": n_times,
        "n_knots": n_knots,
        "n_knots_source": snapshot.knots.n_knots_source.value,
        "n_knots_authority": snapshot.knots.authority,
        "n_knots_scope": snapshot.knots.scope,
        "approved_for_final_modeling": False,
        "n_controls": n_controls,
        "n_treatments": n_treatments,
        "n_media_treatments": n_media,
        "n_data_points": n_data_points,
        "lenient": {
            "label": "LENIENT_MERIDIAN_ALIGNED_DIAGNOSTIC",
            "origin": "PREM3_PRE_EDA",
            "n_parameters": n_parameters_lenient,
            "ratio": ratio_lenient,
            "formula": "n_parameters=(n_geos-1)+n_knots+n_controls+n_treatments",
            "official_meridian_parameter_count": False,
        },
        "strict": {
            "label": "PREM3_DIAGNOSTIC",
            "origin": "PREM3_PRE_EDA",
            "n_parameters": n_parameters_strict,
            "ratio": ratio_strict,
            "formula": (
                "n_parameters_strict=(n_treatments*n_geos)+(n_controls*n_geos)+n_knots+(n_geos-1)"
            ),
            "official_meridian_parameter_count": False,
        },
        "shadow": {
            "label": "PREM3_SHADOW_COMPLEXITY_DIAGNOSTIC",
            "origin": "PREM3_PRE_EDA",
            "n_parameters": n_parameters_shadow,
            "ratio": ratio_shadow,
            "factor": factor,
            "factor_source": config.shadow_source,
            "rule_version": load_intelligence_config().version,
            "formula": ("n_parameters_shadow=(n_geos-1)+n_knots+n_controls+(factor*n_media)"),
            "official_meridian_parameter_count": False,
            "blocks_model_ready": False,
        },
        "interpretation": {
            "knowledge_class": "MMM_EVIDENCE_HEURISTIC",
            "threshold": guidance,
            "severe_threshold": severe,
            "threshold_authority": config.threshold_authority,
            "pressure_band": pressure,
            "review_recommended": pressure != "ADEQUATE",
            "blocks_model_ready": False,
            "never_drop_confounder_for_ratio": True,
        },
        "finding": finding.model_dump(mode="json"),
    }


def _ratio(points: int, parameters: int) -> float | None:
    if parameters <= 0:
        return None
    return round(points / parameters, 6)


def _pressure_band(ratio: float | None, guidance: float, severe: float) -> str:
    if ratio is None:
        return "UNKNOWN"
    if ratio >= guidance:
        return "ADEQUATE"
    if ratio >= severe:
        return "HIGH"
    return "SEVERE"
