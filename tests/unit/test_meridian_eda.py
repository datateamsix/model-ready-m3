from __future__ import annotations

import pandas as pd
import pytest

from app.core.errors import SafetyViolationError, ValidationBlockedError
from app.core.meridian_eda_contracts import (
    MeridianEDAFinding,
    MeridianEDAReceipt,
    category_for_check,
)
from app.core.model_intent import DATASET_A_MODEL_INTENT
from app.tools.meridian_contract import generate_meridian_input_contract
from app.tools.meridian_eda import assert_fingerprint_matches
from app.tools.meridian_eda_gate import (
    default_eda_analysis,
    evaluate_meridian_eda_gate,
    validate_eda_analysis,
)
from app.tools.meridian_eda_mapping import derive_kpi_type, mapping_from_contract
from app.tools.meridian_eda_runtime import meridian_available
from app.tools.model_consumption import fingerprint_frame
from app.tools.run_tools import RUN_READY_TOOLS, _sanitize_eda_analysis


def _dataset_a_frame() -> pd.DataFrame:
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


def _dataset_a_contract():
    return generate_meridian_input_contract(
        run_id="run-eda",
        intent=DATASET_A_MODEL_INTENT,
        frame=_dataset_a_frame(),
        project_id="modelready-m3",
        dataset_id="modelready_models",
        table_id="model_input_run_eda",
    )


def _finding(**overrides) -> MeridianEDAFinding:
    payload = {
        "finding_id": "KPI_INVARIABILITY.OVERALL.VARIABILITY.INFO.01",
        "check_type": "KPI_INVARIABILITY",
        "report_category": "individual_variables",
        "severity": "INFO",
        "finding_cause": "NONE",
        "explanation": "KPI varies enough to model.",
        "analysis_level": "OVERALL",
    }
    payload.update(overrides)
    return MeridianEDAFinding.model_validate(payload)


def _receipt(*findings: MeridianEDAFinding) -> MeridianEDAReceipt:
    items = list(findings) or [_finding()]
    errors = sum(item.severity == "ERROR" for item in items)
    attention = sum(item.severity == "ATTENTION" for item in items)
    info = sum(item.severity == "INFO" for item in items)
    max_sev = "ERROR" if errors else "ATTENTION" if attention else "INFO"
    return MeridianEDAReceipt(
        run_id="run-eda",
        html_report_uri="gs://bucket/eda/meridian_eda_report.html",
        posterior_sampling=False,
        model_fitted=False,
        findings=items,
        severity_summary={
            "error_count": errors,
            "attention_count": attention,
            "info_count": info,
            "max_severity": max_sev,
        },
        status="EDA_COMPLETE",
    )


def test_dataset_a_mapping_uses_contract_not_hardcoded_display_names() -> None:
    mapping = mapping_from_contract(intent=DATASET_A_MODEL_INTENT, contract=_dataset_a_contract())
    kpi_type, derivation = derive_kpi_type(DATASET_A_MODEL_INTENT)
    assert kpi_type == "non_revenue"
    assert "distinct from revenue" in derivation
    assert mapping.kpi_col == "kpi_orders"
    assert mapping.media_cols == [
        "paid_search_impressions",
        "shopping_impressions",
        "paid_social_impressions",
    ]
    assert mapping.media_spend_cols == [
        "paid_search_spend",
        "shopping_spend",
        "paid_social_spend",
    ]
    assert mapping.media_channels == ["paid_search", "shopping", "paid_social"]
    assert mapping.organic_media_cols == ["organic_sessions"]
    assert mapping.control_cols == [
        "consumer_sentiment_index",
        "competitor_discount_index",
        "music_center_promo",
    ]


def test_official_check_types_map_to_five_report_categories() -> None:
    assert category_for_check("DATA_ADEQUACY") == "spend_and_media_unit"
    assert category_for_check("COST_PER_MEDIA_UNIT") == "spend_and_media_unit"
    assert category_for_check("KPI_INVARIABILITY") == "individual_variables"
    assert category_for_check("STANDARD_DEVIATION") == "individual_variables"
    assert category_for_check("POPULATION_CORRELATION") == "population_scaling"
    assert category_for_check("PAIRWISE_CORRELATION") == "variable_relationships"
    assert category_for_check("MULTICOLLINEARITY") == "variable_relationships"
    assert category_for_check("VARIABLE_GEO_TIME_COLLINEARITY") == "variable_relationships"
    assert category_for_check("PRIOR_PROBABILITY") == "prior_specifications"
    with pytest.raises(ValueError, match="Unknown official Meridian check type"):
        category_for_check("HOMEMADE_CHECK")


def test_error_finding_fails_eda_gate() -> None:
    receipt = _receipt(
        _finding(
            finding_id="PAIRWISE_CORRELATION.OVERALL.MULTICOLLINEARITY.ERROR.01",
            check_type="PAIRWISE_CORRELATION",
            report_category="variable_relationships",
            severity="ERROR",
            finding_cause="MULTICOLLINEARITY",
            explanation="Near-perfect correlation.",
        )
    )
    gate = evaluate_meridian_eda_gate(receipt=receipt, html_persisted=True)
    assert gate["status"] == "FAIL"
    assert gate["outcome"] == "EDA_BLOCKED"


def test_attention_passes_with_review_recommended() -> None:
    receipt = _receipt(
        _finding(
            finding_id="COST_PER_MEDIA_UNIT.NATIONAL.OUTLIER.ATTENTION.01",
            check_type="COST_PER_MEDIA_UNIT",
            report_category="spend_and_media_unit",
            severity="ATTENTION",
            finding_cause="OUTLIER",
            explanation="Cost-per-media-unit outlier.",
        )
    )
    gate = evaluate_meridian_eda_gate(receipt=receipt, html_persisted=True)
    assert gate["status"] == "PASS"
    assert gate["review_recommended"] is True


def test_info_only_passes_without_review_flag() -> None:
    gate = evaluate_meridian_eda_gate(receipt=_receipt(), html_persisted=True)
    assert gate["status"] == "PASS"
    assert gate["review_recommended"] is False


def test_missing_html_fails_closed() -> None:
    receipt = _receipt()
    receipt.html_report_uri = None
    with pytest.raises(ValidationBlockedError, match="HTML report missing"):
        evaluate_meridian_eda_gate(receipt=receipt, html_persisted=False)


def test_unknown_finding_id_is_rejected() -> None:
    receipt = _receipt()
    analysis = default_eda_analysis(receipt)
    analysis.blocking_findings = ["NOT-A-REAL-FINDING"]
    with pytest.raises(ValidationBlockedError, match="unknown finding IDs"):
        validate_eda_analysis(analysis, receipt)


def test_prior_disclosure_and_no_posterior() -> None:
    receipt = _receipt()
    assert receipt.prior_context.source == "MERIDIAN_DEFAULT"
    assert receipt.prior_context.used_for == "EDA_PRIOR_DIAGNOSTICS_ONLY"
    assert receipt.prior_context.approved_for_final_modeling is False
    assert receipt.posterior_sampling is False
    assert receipt.model_fitted is False
    with pytest.raises(ValueError, match="must not sample posterior"):
        MeridianEDAReceipt(
            run_id="run-eda",
            posterior_sampling=True,
            findings=[_finding()],
        )


def test_fingerprint_mismatch_fails_closed() -> None:
    frame = _dataset_a_frame()
    expected = fingerprint_frame(frame)
    other = frame.copy()
    other.loc[0, "kpi_orders"] = 99
    with pytest.raises(ValidationBlockedError, match="fingerprint does not match"):
        assert_fingerprint_matches(other, expected)


def test_agent_cannot_supply_eda_severities() -> None:
    with pytest.raises(SafetyViolationError, match="may not supply"):
        _sanitize_eda_analysis({"executive_summary": "ok", "error_count": 0})


def test_run_ready_tools_include_meridian_eda() -> None:
    names = {fn.__name__ for fn in RUN_READY_TOOLS}
    assert names == {
        "initialize_dataset_run",
        "inspect_dataset_run",
        "apply_safe_remediations",
        "validate_and_publish_run",
        "run_meridian_eda",
        "complete_dataset_run",
    }


@pytest.mark.meridian_eda
def test_official_meridian_package_importable() -> None:
    if not meridian_available():
        pytest.skip("google-meridian is not installed in this interpreter")
    import meridian
    from meridian.model.eda import meridian_eda

    assert hasattr(meridian_eda.MeridianEDA, "generate_and_save_report")
    assert hasattr(meridian, "__version__")
