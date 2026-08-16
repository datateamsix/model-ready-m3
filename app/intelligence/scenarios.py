"""Read-only model-scope scenario engine. Never mutates production input."""

from __future__ import annotations

from typing import Any

from app.core.errors import ValidationBlockedError
from app.intelligence.contracts import DecisionClass, ScopeScenarioType
from app.intelligence.parameter import compute_parameter_budget
from app.intelligence.snapshot import DiagnosticSnapshot


def simulate_model_scope_scenarios(
    snapshot: DiagnosticSnapshot,
    scenarios: list[dict[str, Any]] | None = None,
    *,
    baseline_budget: dict[str, Any] | None = None,
    scope_candidates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_budget or compute_parameter_budget(snapshot)
    requested = scenarios or _default_scenarios(snapshot, baseline, scope_candidates)
    results: list[dict[str, Any]] = []
    for spec in requested:
        results.append(_run_scenario(snapshot, baseline, spec))
    return {
        "read_only": True,
        "mutated_production_input": False,
        "baseline": _budget_compact(baseline),
        "scenarios": results,
        "input_fingerprint_unchanged": snapshot.endpoint.input_fingerprint,
    }


def _default_scenarios(
    snapshot: DiagnosticSnapshot,
    baseline: dict[str, Any],
    scope_candidates: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = [
        {
            "scenario_type": ScopeScenarioType.ADDITIONAL_HISTORY.value,
            "additional_periods": 52,
        },
        {
            "scenario_type": ScopeScenarioType.MODELER_REVIEWED_TIME_COMPLEXITY.value,
            "n_knots": max(1, int(baseline["n_knots"] // 2)),
        },
    ]
    candidates = list((scope_candidates or {}).get("candidates") or [])
    if len(candidates) >= 2:
        scenarios.append(
            {
                "scenario_type": ScopeScenarioType.CANDIDATE_CHANNEL_CONSOLIDATION.value,
                "channels": [candidates[0]["channel"], candidates[1]["channel"]],
            }
        )
    elif snapshot.n_treatments >= 2:
        names = [spec.channel for spec in snapshot.channels[:2]]
        scenarios.append(
            {
                "scenario_type": ScopeScenarioType.CANDIDATE_CHANNEL_CONSOLIDATION.value,
                "channels": names,
            }
        )
    optional = [
        name
        for name in snapshot.optional_predictors
        if name in snapshot.contract.controls and name not in snapshot.confirmed_confounders
    ]
    if optional:
        scenarios.append(
            {
                "scenario_type": ScopeScenarioType.OPTIONAL_NON_CONFOUNDING_VARIABLE_SCOPE.value,
                "drop_controls": optional[:1],
            }
        )
    return scenarios


def _run_scenario(
    snapshot: DiagnosticSnapshot,
    baseline: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    scenario_type = str(spec.get("scenario_type") or "")
    n_geos = int(baseline["n_geos"])
    n_times = int(baseline["n_times"])
    n_knots = int(baseline["n_knots"])
    n_controls = int(baseline["n_controls"])
    n_treatments = int(baseline["n_treatments"])
    n_media = int(baseline["n_media_treatments"])
    authority = DecisionClass.ADVISORY.value
    limitation = ""
    if scenario_type == ScopeScenarioType.ADDITIONAL_HISTORY.value:
        extra = int(spec.get("additional_periods") or 0)
        n_times = n_times + extra
        authority = DecisionClass.USER_REQUIRED.value
        limitation = "Hypothetical period counts only. Future data values were not fabricated."
    elif scenario_type == ScopeScenarioType.ADDITIONAL_VALID_GEOS.value:
        extra = int(spec.get("additional_geos") or 0)
        n_geos = n_geos + extra
        authority = DecisionClass.APPROVAL_REQUIRED.value
        limitation = "Hypothetical geo counts only. No geo was dropped or added in production."
    elif scenario_type == ScopeScenarioType.CANDIDATE_CHANNEL_CONSOLIDATION.value:
        channels = list(spec.get("channels") or [])
        if len(channels) < 2:
            raise ValidationBlockedError("Consolidation scenario requires at least two channels.")
        n_treatments = max(1, n_treatments - (len(channels) - 1))
        n_media = max(1, n_media - (len(channels) - 1))
        authority = DecisionClass.APPROVAL_REQUIRED.value
        limitation = (
            "This does not establish that the channels are semantically valid to merge. "
            "Merge remains APPROVAL_REQUIRED."
        )
    elif scenario_type == ScopeScenarioType.OPTIONAL_NON_CONFOUNDING_VARIABLE_SCOPE.value:
        drop = list(spec.get("drop_controls") or [])
        forbidden = [name for name in drop if name in snapshot.confirmed_confounders]
        if forbidden:
            raise ValidationBlockedError(
                "Scope scenarios will not drop a confirmed confounder to improve a ratio: "
                + ", ".join(forbidden)
            )
        allowed = set(snapshot.optional_predictors)
        if drop and not set(drop) <= allowed:
            raise ValidationBlockedError(
                "Optional variable scenarios require variables already marked optional/"
                "non-confounding."
            )
        n_controls = max(0, n_controls - len(drop))
        authority = DecisionClass.MODELER_REVIEW_REQUIRED.value
        limitation = "Only optional non-confounding predictors may be removed in a scenario."
    elif scenario_type == ScopeScenarioType.MODELER_REVIEWED_TIME_COMPLEXITY.value:
        n_knots = int(spec.get("n_knots") or n_knots)
        authority = DecisionClass.MODELER_REVIEW_REQUIRED.value
        limitation = (
            "Knot changes are MODELER_REVIEW_REQUIRED diagnostic sensitivity. "
            "This does not select final ModelSpec knots."
        )
    else:
        raise ValidationBlockedError(f"Unsupported scope scenario type: {scenario_type}")
    factor = float(baseline["shadow"]["factor"])
    n_geo_effects = max(n_geos - 1, 0)
    n_data_points = n_geos * n_times
    lenient = n_geo_effects + n_knots + n_controls + n_treatments
    strict = (n_treatments * n_geos) + (n_controls * n_geos) + n_knots + n_geo_effects
    shadow = n_geo_effects + n_knots + n_controls + int(factor * n_media)
    metrics = {
        "n_geos": n_geos,
        "n_times": n_times,
        "n_knots": n_knots,
        "n_controls": n_controls,
        "n_treatments": n_treatments,
        "n_data_points": n_data_points,
        "lenient_n_parameters": lenient,
        "lenient_ratio": round(n_data_points / lenient, 6) if lenient else None,
        "strict_n_parameters": strict,
        "strict_ratio": round(n_data_points / strict, 6) if strict else None,
        "shadow_n_parameters": shadow,
        "shadow_ratio": round(n_data_points / shadow, 6) if shadow else None,
    }
    return {
        "scenario_type": scenario_type,
        "read_only": True,
        "mutated_production_input": False,
        "assumptions": spec,
        "baseline_metrics": _budget_compact(baseline),
        "scenario_metrics": metrics,
        "change": {
            "lenient_ratio": _delta(baseline["lenient"]["ratio"], metrics["lenient_ratio"]),
            "strict_ratio": _delta(baseline["strict"]["ratio"], metrics["strict_ratio"]),
        },
        "required_authority": authority,
        "known_limitations": limitation,
        "drop_confounder": False,
    }


def _budget_compact(budget: dict[str, Any]) -> dict[str, Any]:
    return {
        "n_geos": budget["n_geos"],
        "n_times": budget["n_times"],
        "n_knots": budget["n_knots"],
        "n_controls": budget["n_controls"],
        "n_treatments": budget["n_treatments"],
        "n_data_points": budget["n_data_points"],
        "lenient_ratio": budget["lenient"]["ratio"],
        "strict_ratio": budget["strict"]["ratio"],
        "shadow_ratio": budget["shadow"]["ratio"],
    }


def _delta(before: float | None, after: float | None) -> float | None:
    if before is None or after is None:
        return None
    return round(after - before, 6)
