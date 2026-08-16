"""Contract tests for the Summit & Pine Dataset C sealed holdout generator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from app.core.model_intent import load_model_intent
from app.intelligence.parameter import compute_parameter_budget
from app.intelligence.semantic import (
    detect_semantic_question_triggers,
    generate_semantic_readiness_interview,
)
from app.mel.fingerprint import fingerprint_payload
from app.synthetic.paths import DATASET_C_DIR
from app.tools.artifacts import sha256_canonical_text_file, sha256_file
from app.tools.inventory import inventory_files
from tests.unit.intelligence_support import dataset_c_snapshot

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "generate_dataset_c.py"
FIXTURE = DATASET_C_DIR

DATASET_C_PACKAGE_FP = "f1bfaa5ba98b8f6d94cccb6b7a19c1e50ab8e315567e82fa3cf22129193bf18f"
DATASET_C_SCHEMA_FP = "1da7e7a724fdf6b9522bf3816fefe14db9dca15c6e43b663ba7de04bc298003e"
DATASET_C_CONTRACT_FP = "d09c95deed895576765b4923f90c8a831c923687ab9016221d8e3c576a7dd522"
DATASET_C_INPUT_FP = "0a79f1c411a5268f15822d9d1d8afced8ac0171d0b6549479571640f134a4cee"
DATASET_C_BASELINE_FP = "7d3c94eb30b6d5a39d03cc2c35488faea669c61cab46aad9e2af70448abb4ffe"
DOMAIN_VIEW_FINGERPRINT = (
    "b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf"
)


def test_dataset_c_generation_contract(tmp_path: Path) -> None:
    output_root = tmp_path / "summit_and_pine"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output-root", str(output_root)],
        check=True,
        cwd=ROOT,
    )
    dataset_dir = output_root / "dataset_c"
    raw_dir = dataset_dir / "raw"
    truth = pd.read_csv(dataset_dir / "truth" / "expected_model_ready_weekly.csv")
    intent = load_model_intent(
        json.loads((raw_dir / "model_intent.json").read_text(encoding="utf-8"))
    )
    generation = json.loads((dataset_dir / "generation_manifest.json").read_text(encoding="utf-8"))
    package = json.loads((dataset_dir / "package_manifest.json").read_text(encoding="utf-8"))

    assert package["dataset_role"] == "SEALED_HOLDOUT"
    assert package["learning_eligibility"] == "DENIED"
    assert generation["seed"] == 20260816
    assert generation["business"] == "Summit & Pine"
    assert intent.kpi.field == "bookings"
    assert intent.kpi.canonical_field == "kpi_bookings"
    assert {channel.provider for channel in intent.paid_media} == {
        "google_ads",
        "pinterest_ads",
        "meta_ads",
    }
    assert {channel.channel for channel in intent.paid_media} == {
        "paid_search",
        "paid_social_upper",
        "paid_social_prospecting",
        "paid_social_retargeting",
    }
    assert truth["time"].nunique() == 156
    assert len(truth) == 780
    assert set(truth["geo"].unique()) == {"CO", "UT", "CA", "PN", "NE"}
    inventoried = {item["path"] for item in inventory_files(raw_dir)}
    assert "expected_model_ready_weekly.csv" not in inventoried
    assert "business_truth.json" not in inventoried
    assert "holdout_manifest.json" not in inventoried
    assert "model_intent.json" in inventoried


def test_dataset_c_generation_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "one"
    second = tmp_path / "two"
    for output_root in (first, second):
        subprocess.run(
            [sys.executable, str(SCRIPT), "--output-root", str(output_root)],
            check=True,
            cwd=ROOT,
        )
    left = json.loads(
        (first / "dataset_c" / "generation_manifest.json").read_text(encoding="utf-8")
    )
    right = json.loads(
        (second / "dataset_c" / "generation_manifest.json").read_text(encoding="utf-8")
    )
    assert left["package_fingerprint"] == right["package_fingerprint"]
    assert {name: info["sha256"] for name, info in left["files"].items()} == {
        name: info["sha256"] for name, info in right["files"].items()
    }


def test_checked_in_dataset_c_matches_generator(tmp_path: Path) -> None:
    output_root = tmp_path / "summit_and_pine"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output-root", str(output_root)],
        check=True,
        cwd=ROOT,
    )
    generated = json.loads(
        (output_root / "dataset_c" / "generation_manifest.json").read_text(encoding="utf-8")
    )
    checked = json.loads((FIXTURE / "generation_manifest.json").read_text(encoding="utf-8"))
    generated_files = generated["files"]
    checked_files = checked["files"]
    mismatched = [
        name
        for name, info in checked_files.items()
        if name.startswith("raw/")
        and name.endswith(".csv")
        and generated_files[name]["sha256"] != info["sha256"]
    ]
    assert mismatched == []
    assert (
        generated_files["truth/expected_model_ready_weekly.csv"]["sha256"]
        == checked_files["truth/expected_model_ready_weekly.csv"]["sha256"]
    )
    assert generated["package_fingerprint"] == checked["package_fingerprint"]
    assert generated["package_fingerprint"] == DATASET_C_PACKAGE_FP
    assert sha256_canonical_text_file(FIXTURE / "raw" / "google_ads_daily.csv") == checked_files[
        "raw/google_ads_daily.csv"
    ]["sha256"]


def test_dataset_c_seeded_defects_are_present() -> None:
    raw = FIXTURE / "raw"
    google = pd.read_csv(raw / "google_ads_daily.csv")
    pinterest = pd.read_csv(raw / "pinterest_ads_daily.csv")
    retarget = pd.read_csv(raw / "meta_ads_retargeting_weekly.csv")
    pms = pd.read_csv(raw / "pms_bookings_weekly.csv")
    stripe = pd.read_csv(raw / "stripe_weekly.csv", dtype={"booking_revenue": str})
    availability = pd.read_csv(raw / "availability_weekly.csv")
    inactive = pd.read_csv(raw / "documented_inactive_periods.csv")
    truth = pd.read_csv(FIXTURE / "truth" / "expected_model_ready_weekly.csv")
    issues = json.loads((FIXTURE / "sealed" / "expected_issues.json").read_text(encoding="utf-8"))

    assert issues["expected_defect_count"] == 12
    assert "cost_micros" in google.columns
    assert {"ctr", "cpa"} <= set(google.columns)
    assert int(google.duplicated().sum()) == 1
    assert set(google["geo"].unique()) >= {"CO Rockies", "NorCal", "PNW", "Wasatch"}
    assert pinterest["date"].nunique() > truth["time"].nunique()
    assert int(retarget.duplicated().sum()) == 1
    assert pms["week_ending"].str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
    mondays = pd.to_datetime(truth["time"]).dt.day_name().unique().tolist()
    assert mondays == ["Monday"]
    sundays = pd.to_datetime(pms["week_ending"]).dt.day_name().unique().tolist()
    assert sundays == ["Sunday"]
    assert stripe["booking_revenue"].str.match(r"^\$[\d,]+\.\d{2}$").any()
    assert not stripe["booking_revenue"].str.match(r"^\$[\d,]+\.\d{2}$").all()
    assert len(availability) == 779
    assert len(inactive) == 4
    gap = truth[
        (truth["geo"] == "CA") & (truth["time"].isin(["2024-06-03", "2024-06-10", "2024-06-17"]))
    ]
    assert gap["paid_search_spend"].isna().all()
    missing_avail = truth[(truth["geo"] == "CO") & (truth["time"] == "2024-10-07")]
    assert missing_avail["availability_index"].isna().all()
    inactive_spend = truth[
        (truth["geo"] == "PN")
        & (truth["time"].isin(["2024-04-01", "2024-04-08", "2024-04-15", "2024-04-22"]))
    ]
    assert (inactive_spend["paid_social_prospecting_spend"] == 0).all()


def test_dataset_c_forbidden_and_safe_actions_are_persisted() -> None:
    forbidden = json.loads(
        (FIXTURE / "sealed" / "expected_forbidden_actions.json").read_text(encoding="utf-8")
    )
    safe = json.loads(
        (FIXTURE / "sealed" / "expected_safe_actions.json").read_text(encoding="utf-8")
    )
    actions = {item["action"] for item in forbidden["actions"]}
    assert "zero_fill_unknown_google_gap" in actions
    assert "zero_fill_missing_availability_control" in actions
    assert "impute_kpi_bookings" in actions
    assert "merge_prospecting_and_retargeting" in actions
    assert "infer_causal_role_from_correlation" in actions
    assert "extract_candidate_lesson_from_dataset_c" in actions
    assert "use_holdout_evidence_to_alter_domain_view" in actions
    assert "select_final_priors_or_knots_or_modelspec" in actions
    assert "fit_posterior_or_final_mmm" in actions
    safe_actions = {item["action"] for item in safe["actions"]}
    assert "convert_google_cost_micros_to_currency" in safe_actions
    assert "zero_fill_meta_prospecting_documented_inactive_pn" in safe_actions
    assert not (FIXTURE / "sealed" / "expected_lesson.json").exists()
    assert not (FIXTURE / "raw" / "business_truth.json").exists()


def test_dataset_c_positive_and_negative_conditions() -> None:
    payload = json.loads(
        (FIXTURE / "sealed" / "expected_semantic_conditions.json").read_text(encoding="utf-8")
    )
    conditions = payload["conditions"]
    positive = [item for item in conditions if item["control"] == "positive"]
    negative = [item for item in conditions if item["control"] == "negative"]
    assert len(positive) >= 3
    assert len(negative) >= 3
    families = {item["expected_question_family"] for item in positive}
    assert {
        "PROMOTION_TIMING",
        "PRICE_DISCOUNT_TIMING",
        "DOWNSTREAM_MEDIA",
        "REMARKETING_TARGETING",
        "ORGANIC_MEDIA_TIMING",
    } <= families
    assert all(item["input_blocker"] is False for item in positive)
    assert all("must_not_infer" in item for item in negative)


def test_dataset_c_semantic_triggers_match_families_not_wording() -> None:
    expected = json.loads(
        (FIXTURE / "sealed" / "expected_semantic_triggers.json").read_text(encoding="utf-8")
    )
    snapshot = dataset_c_snapshot()
    interview = generate_semantic_readiness_interview(snapshot)
    families = {item["question_family"] for item in detect_semantic_question_triggers(snapshot)}
    assert families == set(expected["expected_families"])
    assert interview["causal_roles_assigned"] is False
    assert interview["generic_questionnaire"] is False
    assert "REMARKETING_TARGETING" in families
    assert expected["cannot_independently_block_model_ready"] is True


def test_dataset_c_run_intelligence_is_computed_not_guessed() -> None:
    expected = json.loads(
        (FIXTURE / "sealed" / "expected_run_intelligence.json").read_text(encoding="utf-8")
    )
    snapshot = dataset_c_snapshot()
    budget = compute_parameter_budget(snapshot)
    assert budget["n_geos"] == expected["n_geos"] == 5
    assert budget["n_times"] == expected["n_times"] == 156
    assert budget["n_data_points"] == expected["n_data_points"] == 780
    assert budget["n_controls"] == 5
    assert budget["n_treatments"] == 6
    assert budget["lenient"]["ratio"] == expected["lenient_ratio"]
    assert budget["interpretation"]["pressure_band"] == expected["pressure_band"]
    assert budget["interpretation"]["blocks_model_ready"] is False
    assert abs(float(expected["lenient_ratio"]) - 3.74) > 0.2
    assert abs(float(expected["lenient_ratio"]) - 5.538462) > 0.2
    assert expected["input_fingerprint"] == DATASET_C_INPUT_FP
    assert expected["never_drop_confounder_for_ratio"] is True


def test_dataset_c_holdout_seal_and_baseline_are_pre_learning() -> None:
    holdout = json.loads(
        (FIXTURE / "learning" / "holdout_manifest.json").read_text(encoding="utf-8")
    )
    sealed = json.loads(
        (FIXTURE / "sealed" / "holdout_manifest.json").read_text(encoding="utf-8")
    )
    baseline = json.loads(
        (FIXTURE / "baseline" / "domain_view_v1" / "baseline_result.json").read_text(
            encoding="utf-8"
        )
    )
    generation = json.loads((FIXTURE / "generation_manifest.json").read_text(encoding="utf-8"))
    assert holdout == sealed
    assert holdout["sealed_before_candidate_extraction"] is True
    assert holdout["lesson_ids_visible_at_seal"] == []
    assert holdout["promoted_lesson_count_at_seal"] == 0
    assert holdout["training_access"] == "DENIED"
    assert holdout["candidate_generation_access"] == "DENIED"
    assert holdout["reflection_training_access"] == "DENIED"
    assert holdout["evaluation_only"] is True
    assert holdout["seed"] == 20260816
    assert holdout["input_package_fingerprint"] == DATASET_C_PACKAGE_FP
    assert holdout["schema_fingerprint"] == DATASET_C_SCHEMA_FP
    assert holdout["expected_contract_fingerprint"] == DATASET_C_CONTRACT_FP
    assert holdout["domain_view_fingerprint_at_seal"] == DOMAIN_VIEW_FINGERPRINT
    assert holdout["sealed_at"] == "2026-08-16T19:00:00+00:00"
    assert generation["package_fingerprint"] == DATASET_C_PACKAGE_FP
    assert baseline["domain_view_fingerprint"] == DOMAIN_VIEW_FINGERPRINT
    assert baseline["promoted_lesson_count"] == 0
    assert baseline["causal_roles_assigned"] is False
    assert baseline["official_eda_status"] == "NOT_RUN_IN_GENERATOR"
    assert baseline["model_ready_state"] == "NOT_CLAIMED_LOCAL_BASELINE"
    assert baseline["training_access"] == "DENIED"
    assert baseline["result_fingerprint"] == DATASET_C_BASELINE_FP
    stripped = {key: value for key, value in baseline.items() if key != "result_fingerprint"}
    assert fingerprint_payload(stripped) == DATASET_C_BASELINE_FP


def test_dataset_c_mutation_changes_package_fingerprint() -> None:
    google = FIXTURE / "raw" / "google_ads_daily.csv"
    original = google.read_bytes()
    try:
        google.write_bytes(original + b"\n")
        mutated = sha256_file(google)
        checked = json.loads((FIXTURE / "generation_manifest.json").read_text(encoding="utf-8"))
        assert mutated != checked["files"]["raw/google_ads_daily.csv"]["sha256"]
    finally:
        google.write_bytes(original)
    restored = sha256_canonical_text_file(google)
    checked = json.loads((FIXTURE / "generation_manifest.json").read_text(encoding="utf-8"))
    assert restored == checked["files"]["raw/google_ads_daily.csv"]["sha256"]
