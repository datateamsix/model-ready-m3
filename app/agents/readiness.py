"""Readiness reasoning boundary.

This agent interprets deterministic findings and proposes a remediation plan. It
never overrides a failing deterministic check and never marks a run MODEL_READY.
"""

READINESS_AGENT_SCOPE = {
    "owns": [
        "finding_interpretation",
        "severity_explanation",
        "remediation_planning",
        "approval_routing",
    ],
    "does_not_own": [
        "validator_results",
        "auto_safe_preconditions",
        "model_ready_gate",
    ],
}
