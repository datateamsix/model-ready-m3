from pathlib import Path

import pandas as pd
import pytest

from app.core.contracts import BigQueryPublishReceipt, ReadinessCheck, ReadinessReceipt
from app.core.errors import (
    ApprovalRequiredError,
    IllegalTransitionError,
    RegistryTrustError,
    SafetyViolationError,
    ValidationBlockedError,
)
from app.core.model_intent import DATASET_A_MODEL_INTENT
from app.core.state import RunStage, assert_legal_transition
from app.tools.adk_tools import (
    apply_mapping_to_file,
    canonicalize_channel_labels_in_file,
    get_meridian_pocket_card,
    lookup_provider_card,
)
from app.tools.fingerprints import content_fingerprint
from app.tools.gate import evaluate_model_ready_gate
from app.tools.io import write_table
from app.tools.mapping import apply_mapping
from app.tools.meridian_contract import generate_meridian_input_contract
from app.tools.remediation import aggregate_to_week
from app.tools.safety import assert_summable_columns, validate_provider_mapping


def test_lookup_provider_card_found() -> None:
    result = lookup_provider_card("shopify")
    assert result["found"] is True
    assert result["entry"]["provider_id"] == "shopify"


def test_apply_mapping_blocks_directory_provider(tmp_path: Path) -> None:
    path = tmp_path / "tiktok.csv"
    write_table(pd.DataFrame({"spend": [1]}), path)
    with pytest.raises(RegistryTrustError):
        apply_mapping_to_file(
            str(path),
            {"spend": "media_spend"},
            str(tmp_path / "out.csv"),
            provider_id="tiktok_ads",
        )


def test_canonicalize_tool_reports_unmapped(tmp_path: Path) -> None:
    path = tmp_path / "meta.csv"
    write_table(pd.DataFrame({"channel": ["Meta", "unknown"]}), path)
    result = canonicalize_channel_labels_in_file(
        str(path),
        "channel",
        {"Meta": "paid_social"},
        str(tmp_path / "out.csv"),
    )
    assert result["unmapped_values"] == ["unknown"]


def test_evaluate_model_ready_gate_blocks_without_evidence() -> None:
    readiness = ReadinessReceipt(
        run_id="run-1",
        status="PASS",
        blocking_checks_passed=True,
        checks=[ReadinessCheck(rule_id="MR-001", passed=True)],
    )
    publish = BigQueryPublishReceipt(
        run_id="run-1",
        status="PUBLISHED",
        project_id="modelready-m3",
        dataset_id="modelready_models",
        table_id="model_input_run_1",
        row_count=524,
        schema_fingerprint="abc",
        artifact_fingerprint="def",
        published_fingerprint="def",
        parity_status="FAIL",
    )
    frame = pd.DataFrame(
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
    contract = generate_meridian_input_contract(
        run_id="run-1",
        intent=DATASET_A_MODEL_INTENT,
        frame=frame,
        project_id="modelready-m3",
        dataset_id="modelready_models",
        table_id="model_input_run_1",
    )
    with pytest.raises(ValidationBlockedError):
        evaluate_model_ready_gate(
            readiness=readiness,
            publish=publish,
            meridian_contract=contract,
            provenance={"records": [{"source_sha256": "a", "output_sha256": "b"}]},
        )


def test_evaluate_model_ready_gate_blocks_weak_provenance() -> None:
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
        row_count=524,
        schema_fingerprint="abc",
        artifact_fingerprint="def",
        published_fingerprint="def",
        parity_status="PASS",
    )
    frame = pd.DataFrame(
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
    contract = generate_meridian_input_contract(
        run_id="run-1",
        intent=DATASET_A_MODEL_INTENT,
        frame=frame,
        project_id="modelready-m3",
        dataset_id="modelready_models",
        table_id="model_input_run_1",
    )
    with pytest.raises(ValidationBlockedError, match="provenance_pass"):
        evaluate_model_ready_gate(
            readiness=readiness,
            publish=publish,
            meridian_contract=contract,
            provenance={"records": [{"source_sha256": "a", "output_sha256": "b"}]},
        )


def test_pocket_card_forbids_prose_model_ready() -> None:
    card = get_meridian_pocket_card()
    assert "deterministic_readiness_pass" in card["model_ready_requires"]
    assert "official_meridian_pre_modeling_eda_zero_errors" in card["model_ready_requires"]
    assert "official_meridian_data_adequacy_parameters_captured" in card["model_ready_requires"]
    assert "official_meridian_knots_identifiable" in card["model_ready_requires"]
    assert "MR-006" in card["rules"]


def test_summing_ctr_is_blocked() -> None:
    frame = pd.DataFrame({"date": ["2026-01-01"], "geo": ["TX"], "ctr": [0.1]})
    with pytest.raises(SafetyViolationError):
        aggregate_to_week(
            frame,
            date_column="date",
            group_columns=["geo"],
            sum_columns=["ctr"],
            provider_id="google_ads",
        )


def test_assert_summable_rejects_cpc() -> None:
    with pytest.raises(SafetyViolationError):
        assert_summable_columns(["cpc"])


def test_mapping_rejects_contradictory_semantic() -> None:
    with pytest.raises(ApprovalRequiredError):
        validate_provider_mapping("meta_ads", {"amount_spent": "kpi"})


def test_mapping_allows_trusted_spend_semantic() -> None:
    frame = pd.DataFrame({"amount_spent": [1.0]})
    result = apply_mapping(frame, {"amount_spent": "media_spend"}, provider_id="meta_ads")
    assert "media_spend" in result.columns


def test_illegal_transition_is_blocked() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_legal_transition(RunStage.NEW, RunStage.MODEL_READY)


def test_content_fingerprint_is_stable() -> None:
    frame = pd.DataFrame(
        {"time": ["2024-01-08", "2024-01-01"], "geo": ["TX", "CA"], "kpi_orders": [2, 1]}
    )
    first = content_fingerprint(
        frame, columns=["time", "geo", "kpi_orders"], key_columns=["time", "geo"]
    )
    second = content_fingerprint(
        frame, columns=["time", "geo", "kpi_orders"], key_columns=["time", "geo"]
    )
    assert first == second
