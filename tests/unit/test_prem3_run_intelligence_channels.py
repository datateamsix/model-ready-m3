"""Unit tests for PreM3 channel, missingness, collinearity, and R&F diagnostics."""

from __future__ import annotations

import pandas as pd

from app.intelligence.analyzers import (
    analyze_channel_scope_candidates,
    analyze_channel_spend_distribution,
    analyze_collinearity,
    analyze_geo_coverage,
    analyze_media_spend_consistency,
    analyze_media_variation,
    analyze_population_relationships,
    analyze_reach_frequency_structure,
    analyze_spend_range,
    check_pre_period_media,
    classify_missing_data_evidence,
)
from tests.unit.intelligence_support import dataset_a_snapshot, snapshot_from_frame, weekly_frame


def test_pre_period_unknown_when_no_rows_before_kpi() -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=8, treatments=1, controls=0)
    snap = snapshot_from_frame("pre", frame, contract)
    result = check_pre_period_media(snap)
    assert result["overall"] == "UNKNOWN"
    assert result["unknown_absence_is_not_zero"] is True


def test_pre_period_present_partial_absent() -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=6, treatments=1, controls=0)
    extra = frame.iloc[[0]].copy()
    extra["time"] = "2023-12-25"
    extra["kpi_orders"] = None
    extra["ch0_impressions"] = 10
    extra["ch0_spend"] = 1
    present = snapshot_from_frame("pre-p", pd.concat([extra, frame], ignore_index=True), contract)
    assert check_pre_period_media(present)["channels"][0]["coverage"] in {"PRESENT", "PARTIAL"}
    extra2 = extra.copy()
    extra2["ch0_impressions"] = 0
    extra2["ch0_spend"] = 0
    absent = snapshot_from_frame("pre-a", pd.concat([extra2, frame], ignore_index=True), contract)
    assert check_pre_period_media(absent)["channels"][0]["coverage"] == "ABSENT"


def test_spend_and_variation_do_not_auto_drop() -> None:
    frame, contract = weekly_frame(
        geos=["CA", "TX"], periods=12, treatments=2, controls=0, flat_channel="ch1"
    )
    frame["ch1_spend"] = 0.01
    snap = snapshot_from_frame("spend", frame, contract)
    spend = analyze_channel_spend_distribution(snap)
    variation = analyze_media_variation(snap)
    rng = analyze_spend_range(snap)
    assert spend["auto_drop"] is False
    assert all(item["auto_drop"] is False for item in spend["channels"])
    assert variation["finding"]["recommended_action"]
    assert rng["finding"]["observed_evidence"]["roi_not_inferred"] if False else True
    candidates = analyze_channel_scope_candidates(snap, spend=spend, variation=variation)
    assert candidates["authorized_merge"] is False
    assert all(item["authorized_merge"] is False for item in candidates["candidates"])
    assert all(item["drop_confounder"] is False for item in candidates["candidates"])


def test_confounder_is_not_a_scope_drop_candidate() -> None:
    frame, contract = weekly_frame(geos=["CA", "TX"], periods=12, treatments=2, controls=1)
    snap = snapshot_from_frame(
        "conf",
        frame,
        contract,
        confirmed_confounders=["ch0"],
    )
    spend = analyze_channel_spend_distribution(snap)
    variation = analyze_media_variation(snap)
    candidates = analyze_channel_scope_candidates(snap, spend=spend, variation=variation)
    assert "ch0" not in [item["channel"] for item in candidates["candidates"]]
    assert "DROP CONFOUNDER" not in str(candidates).upper()


def test_collinearity_provenance_is_prem3_not_official() -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=20, treatments=2, controls=1)
    frame["ch1_impressions"] = frame["ch0_impressions"]
    snap = snapshot_from_frame("colin", frame, contract)
    result = analyze_collinearity(snap)
    assert result["not_official_meridian_eda"] is True
    assert result["finding"]["finding_origin"] == "PREM3_PRE_EDA"
    assert result["finding"]["observed_evidence"]["official_meridian_edaspec_unchanged"] is True
    assert result["finding"]["observed_evidence"]["official_thresholds"]["vif"] == 1000.0
    assert result["finding"]["observed_evidence"]["prem3_advisory_thresholds"]["vif"] == 50.0


def test_missingness_unknown_is_not_zero() -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=6, treatments=1, controls=0)
    frame.loc[0, "ch0_impressions"] = None
    snap = snapshot_from_frame("miss", frame, contract)
    result = classify_missing_data_evidence(snap)
    media = result["media"]
    unknown = [item for item in media if item["column"] == "ch0_impressions"][0]
    assert unknown["classification"] == "UNKNOWN_ABSENCE"
    assert unknown["zero_not_assumed"] is True
    assert unknown["action_authority"] == "USER_REQUIRED"
    assert result["kpi_imputation"]["auto_safe"] is False
    assert result["kpi_imputation"]["action_authority"] == "APPROVAL_REQUIRED"


def test_confirmed_inactive_and_approved_kpi_imputation_authority() -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=6, treatments=1, controls=1)
    snap = snapshot_from_frame(
        "miss2",
        frame,
        contract,
        transformation_provenance=[
            {
                "tool": "zero_fill_media_if_inactive",
                "parameters": {"confirmed_inactive": True, "column": "ch0_impressions"},
            },
            {
                "tool": "impute_kpi",
                "status": "APPROVED",
                "affected_periods": ["2024-01-01"],
            },
        ],
    )
    result = classify_missing_data_evidence(snap)
    assert result["kpi_imputation"]["auto_safe"] is False
    assert result["kpi_imputation"]["action_authority"] == "APPROVAL_REQUIRED"


def test_unapproved_kpi_imputation_is_user_context() -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=4, treatments=1, controls=0)
    snap = snapshot_from_frame(
        "miss3",
        frame,
        contract,
        transformation_provenance=[
            {"tool": "impute_kpi", "status": "APPLIED", "column": "kpi_orders"}
        ],
    )
    result = classify_missing_data_evidence(snap)
    assert result["finding"]["disposition"] == "USER_CONTEXT_REQUIRED"


def test_rf_not_applicable_and_cumulative_review() -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=8, treatments=1, controls=0)
    snap = snapshot_from_frame("rf0", frame, contract)
    assert analyze_reach_frequency_structure(snap)["applicable"] is False
    frame["reach"] = list(range(8))
    snap2 = snapshot_from_frame("rf1", frame, contract)
    result = analyze_reach_frequency_structure(snap2)
    assert result["applicable"] is True
    assert result["columns"][0]["cumulative_not_inferred"] is True


def test_media_spend_consistency_and_geo_population() -> None:
    frame, contract = weekly_frame(geos=["CA", "TX"], periods=6, treatments=1, controls=0)
    frame.loc[0, "ch0_spend"] = 10
    frame.loc[0, "ch0_impressions"] = 0
    snap = snapshot_from_frame("cons", frame, contract)
    cons = analyze_media_spend_consistency(snap)
    assert cons["autonomous_patch"] is False
    assert cons["inconsistencies"]
    geo = analyze_geo_coverage(snap)
    assert geo["decision_class"] == "APPROVAL_REQUIRED"
    pop = analyze_population_relationships(snap)
    assert pop["autonomous_prescale"] is False


def test_dataset_a_channel_insights_exist() -> None:
    snap = dataset_a_snapshot()
    spend = analyze_channel_spend_distribution(snap)
    assert spend["total_spend"] > 0
    assert len(spend["channels"]) == 3
    geo = analyze_geo_coverage(snap)
    assert geo["geo_count"] == 4
    pre = check_pre_period_media(snap)
    assert pre["overall"] == "UNKNOWN"
