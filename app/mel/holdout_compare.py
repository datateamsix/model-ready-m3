"""Compare sealed Dataset C DOMAIN_VIEW v1 vs a future v2 application run.

Only DOMAIN_VIEW should be the independent variable. Advisory/routing behavior
may change. Deterministic calculations and MODEL_READY logic must not.
"""

from __future__ import annotations

from typing import Any

INVARIANT_DIMENSIONS = (
    "model_input_fingerprint",
    "schema_fingerprint",
    "parameter_calculations",
    "readiness_deterministic_checks",
    "official_meridian_findings",
    "model_ready_logic",
    "raw_data_values",
    "final_priors",
    "final_knots",
    "final_modelspec",
    "posterior",
)

ALLOWED_BEHAVIOR_CHANGES = (
    "question_routing",
    "diagnostic_routing",
    "finding_prioritization",
    "advisory_ordering",
    "handoff_emphasis",
    "source_acquisition_guidance",
)

COMPARISON_DIMENSIONS = (
    "tool_route",
    "question_route",
    "finding_priority",
    "advisory_output",
    "action_ownership",
    "model_ready_state",
    "official_meridian_evidence",
    "calculations",
)


def compare_holdout_runs(baseline_v1: dict[str, Any], later_v2: dict[str, Any]) -> dict[str, Any]:
    """Return a structured v1-vs-v2 comparison. Does not certify EXPERIENCE_APPLIED."""
    invariant_failures: list[str] = []
    for key in INVARIANT_DIMENSIONS:
        left = baseline_v1.get(key)
        right = later_v2.get(key)
        if left is not None and right is not None and left != right:
            invariant_failures.append(key)
    changed = [
        key
        for key in ALLOWED_BEHAVIOR_CHANGES
        if baseline_v1.get(key) is not None
        and later_v2.get(key) is not None
        and baseline_v1.get(key) != later_v2.get(key)
    ]
    return {
        "invariants_ok": not invariant_failures,
        "invariant_failures": invariant_failures,
        "allowed_changes_observed": changed,
        "comparison_dimensions": list(COMPARISON_DIMENSIONS),
        "experience_applied": False,
        "reason": (
            "Comparison only. EXPERIENCE_APPLIED requires a promoted lesson, "
            "explicit retrieval, matched applicability, and independent validation."
        ),
    }
