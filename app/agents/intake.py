"""Intake/resolver reasoning boundary.

Provider/report identification and candidate field semantics belong here. The
actual profiling/mapping operations remain deterministic tools.
"""

INTAKE_AGENT_SCOPE = {
    "owns": [
        "provider_identification",
        "report_type_identification",
        "candidate_field_semantics",
        "mapping_confidence",
    ],
    "does_not_own": [
        "dataframe_transforms",
        "final_readiness",
        "bigquery_parity",
    ],
}
