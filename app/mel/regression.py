"""Regression checks that must pass before DOMAIN_VIEW activation."""

from __future__ import annotations

from typing import Any

from app.mel.models import RegressionPlan, RegressionResult


def default_routing_plan() -> RegressionPlan:
    return RegressionPlan(
        matching_cases=["semantic_questions_open"],
        non_matching_cases=["no_semantic_questions"],
        guardrail_tests=[
            "MODEL_READY_INVARIANT",
            "OFFICIAL_MERIDIAN_ORIGIN_STABLE",
            "NUMERIC_DIAGNOSTICS_STABLE",
        ],
        model_ready_invariance=True,
        meridian_origin_separation=True,
        privacy_tests=True,
    )


def evaluate_routing_regression(
    *,
    matching_before: dict[str, Any],
    matching_after: dict[str, Any],
    nonmatching_before: dict[str, Any],
    nonmatching_after: dict[str, Any],
    model_ready_before: str,
    model_ready_after: str,
    meridian_origin_before: str,
    meridian_origin_after: str,
    numeric_before: dict[str, Any],
    numeric_after: dict[str, Any],
) -> RegressionResult:
    matching_changed = matching_before != matching_after
    nonmatching_stable = nonmatching_before == nonmatching_after
    ready_stable = model_ready_before == model_ready_after
    origin_stable = meridian_origin_before == meridian_origin_after
    numeric_stable = numeric_before == numeric_after
    passed = (
        matching_changed
        and nonmatching_stable
        and ready_stable
        and origin_stable
        and numeric_stable
    )
    return RegressionResult(
        passed=passed,
        matching_case_changed=matching_changed,
        non_matching_case_stable=nonmatching_stable,
        model_ready_stable=ready_stable,
        meridian_origin_stable=origin_stable,
        numeric_diagnostics_stable=numeric_stable,
        detail="routing regression compared matching/non-matching behavior",
    )
