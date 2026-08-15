"""Compact Meridian context card. Cite rule IDs; do not dump full docs into prompts."""

from __future__ import annotations

from typing import Any

MERIDIAN_POCKET_CARD: dict[str, Any] = {
    "target": "google_meridian",
    "time_format": "yyyy-mm-dd",
    "preferred_grain": "weekly",
    "variable_families": [
        "geo",
        "time",
        "kpi",
        "revenue_per_kpi",
        "population",
        "controls",
        "media",
        "media_spend",
        "reach",
        "frequency",
        "rf_spend",
        "non_media_treatments",
        "organic_media",
        "organic_reach",
        "organic_frequency",
    ],
    "rules": {
        "MR-001": "Time values must normalize to yyyy-mm-dd.",
        "MR-002": "Do not zero-fill missing KPI/control values merely to pass completeness.",
        "MR-003": "All required variables must share one temporal grain; weekly is preferred.",
        "MR-006": "Do not sum CTR, CPC, ROAS, AOV, or other rates; reconstruct from components.",
        "MR-009": "Aggregate campaign rows to modeled channels using summable measures.",
        "MR-010": "No duplicate observations at canonical grain unless aggregation is intended.",
        "MR-017": "Spend units/currency must be numeric and consistent before aggregation.",
        "MR-019": "BigQuery published table must match the validated artifact (parity).",
        "MR-020": "MODEL_READY requires a complete Meridian handoff contract.",
    },
    "model_ready_requires": [
        "deterministic_readiness_pass",
        "bigquery_publish_pass",
        "publish_parity_pass",
        "meridian_handoff_contract_complete",
        "provenance_complete",
    ],
    "authority": "Deterministic tools own PASS/FAIL. Agent prose cannot set MODEL_READY.",
}
