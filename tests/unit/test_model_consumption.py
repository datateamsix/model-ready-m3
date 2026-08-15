from __future__ import annotations

import pandas as pd
import pytest

from app.core.contracts import (
    BigQueryPublishReceipt,
    ParityCheck,
    ReadinessCheck,
    ReadinessReceipt,
)
from app.core.errors import ValidationBlockedError
from app.core.model_intent import DATASET_A_MODEL_INTENT
from app.tools.gate import evaluate_final_model_ready_gate, evaluate_model_ready_gate
from app.tools.meridian_contract import generate_meridian_input_contract
from app.tools.model_consumption import build_confirmation_receipt, build_consumption_receipt
from app.tools.provenance import FRAME_SOURCE_ROLES
from app.tools.schema_compiler import compile_model_consumption_schema
from app.tools.validation import REQUIRED_DATASET_A_TOOLS


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": ["2024-01-01"],
            "geo": ["CA"],
            "kpi_orders": [1],
            "kpi_revenue": [1.0],
            "revenue_per_kpi": [1.0],
            "population": [1],
            "paid_search_impressions": [1],
            "paid_search_spend": [1.0],
            "shopping_impressions": [1],
            "shopping_spend": [1.0],
            "paid_social_impressions": [1],
            "paid_social_spend": [1.0],
            "organic_sessions": [1],
            "consumer_sentiment_index": [1.0],
            "competitor_discount_index": [0.1],
            "music_center_promo": [0],
        }
    )


def _passing_gate_inputs():
    frame = _frame()
    readiness = ReadinessReceipt(
        run_id="run-1",
        status="PASS",
        blocking_checks_passed=True,
        checks=[
            ReadinessCheck(rule_id="MR-001", passed=True),
            ReadinessCheck(rule_id="MR-018", passed=True),
        ],
    )
    publish = BigQueryPublishReceipt(
        run_id="run-1",
        status="PUBLISHED",
        project_id="modelready-m3",
        dataset_id="modelready_models",
        table_id="model_input_run_1",
        row_count=1,
        schema_fingerprint="abc",
        artifact_fingerprint="def",
        published_fingerprint="def",
        parity_status="PASS",
    )
    contract = generate_meridian_input_contract(
        run_id="run-1",
        intent=DATASET_A_MODEL_INTENT,
        frame=frame,
        project_id="modelready-m3",
        dataset_id="modelready_models",
        table_id="model_input_run_1",
    )
    records = []
    for tool in REQUIRED_DATASET_A_TOOLS:
        item = {
            "tool": tool,
            "source_sha256": "a" * 64,
            "output_sha256": "b" * 64,
        }
        if tool == "build_model_ready_frame":
            item["sources"] = [{"role": role, "sha256": "c" * 64} for role in FRAME_SOURCE_ROLES]
        records.append(item)
    provenance = {"dataset_fingerprint": "d" * 64, "records": records}
    return readiness, publish, contract, provenance


def _passing_eda() -> dict:
    return {
        "run_id": "run-1",
        "html_report_uri": "gs://artifacts/eda/meridian_eda_report.html",
        "posterior_sampling": False,
        "model_fitted": False,
        "findings": [],
        "status": "EDA_COMPLETE",
        "severity_summary": {
            "error_count": 0,
            "attention_count": 0,
            "info_count": 0,
            "max_severity": "INFO",
        },
        "prior_context": {
            "source": "MERIDIAN_DEFAULT",
            "used_for": "EDA_PRIOR_DIAGNOSTICS_ONLY",
            "approved_for_final_modeling": False,
            "n_draws_prior": 500,
            "seed": 0,
        },
    }


def test_consumption_receipt_fails_closed_without_registry() -> None:
    schema = compile_model_consumption_schema(intent=DATASET_A_MODEL_INTENT)
    receipt = build_consumption_receipt(
        run_id="run-1",
        target_model="google_meridian",
        versioned_table="p.d.t",
        consumption_view="p.d.v",
        schema=schema,
        actual_schema=[],
        expected_content_fingerprint="abc",
        versioned_fingerprint="abc",
        view_fingerprint="abc",
        row_count=1,
        verification_checks=[ParityCheck(name="ok", passed=True, evidence={})],
        registry_recorded=False,
    )
    assert receipt["status"] == "PROMOTION_FAILED"


def test_confirmation_requires_every_check() -> None:
    receipt = build_confirmation_receipt(
        run_id="run-1",
        manifest_uri="gs://artifacts/manifest.json",
        versioned_table="p.d.t",
        consumption_view="p.d.v",
        checks={"physical_schema_matches": True, "partitioning_matches": False},
        target_model="google_meridian",
    )
    assert receipt["status"] == "NOT_MODEL_READY"


def test_final_gate_blocks_when_view_or_registry_fails() -> None:
    readiness, publish, contract, provenance = _passing_gate_inputs()
    evaluate_model_ready_gate(
        readiness=readiness,
        publish=publish,
        meridian_contract=contract,
        provenance=provenance,
    )
    confirmation = {
        "status": "MODEL_READY",
        "checks": {
            "physical_schema_matches": True,
            "stable_view_matches": False,
            "registry_recorded": True,
        },
    }
    with pytest.raises(ValidationBlockedError, match="MODEL_READY blocked"):
        evaluate_final_model_ready_gate(
            readiness=readiness,
            publish=publish,
            meridian_contract=contract,
            provenance=provenance,
            confirmation=confirmation,
            consumption={"status": "PROMOTION_VERIFIED"},
            eda=_passing_eda(),
            html_persisted=True,
        )


def test_final_gate_blocks_when_confirmation_omits_physical_schema() -> None:
    readiness, publish, contract, provenance = _passing_gate_inputs()
    confirmation = {
        "status": "MODEL_READY",
        "checks": {
            "stable_view_matches": True,
            "registry_recorded": True,
        },
    }
    with pytest.raises(ValidationBlockedError):
        evaluate_final_model_ready_gate(
            readiness=readiness,
            publish=publish,
            meridian_contract=contract,
            provenance=provenance,
            confirmation=confirmation,
            consumption={"status": "PROMOTION_VERIFIED"},
            eda=_passing_eda(),
            html_persisted=True,
        )
