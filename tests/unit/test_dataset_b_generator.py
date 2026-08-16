"""Contract tests for the Stride & Field Dataset B synthetic generator.

The generator extends Music Center helpers in `app.synthetic.mmm`. It must not
overwrite Music Center Dataset B or mutate the sealed Dataset C holdout.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from app.core.model_intent import load_model_intent
from app.intelligence.parameter import compute_parameter_budget
from app.intelligence.semantic import detect_semantic_question_triggers
from app.synthetic.paths import DATASET_B_DIR, DATASET_C_DIR, MUSIC_CENTER_ROOT
from app.tools.artifacts import sha256_file
from app.tools.inventory import inventory_files
from tests.unit.intelligence_support import dataset_b_snapshot

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "generate_dataset_b.py"
FIXTURE = DATASET_B_DIR
MUSIC_CENTER_B = MUSIC_CENTER_ROOT / "dataset_b"
DATASET_C = DATASET_C_DIR


def test_dataset_b_semantic_interview_does_not_assign_causal_roles() -> None:
    from app.intelligence.semantic import generate_semantic_readiness_interview

    expected = json.loads(
        (FIXTURE / "expected" / "expected_semantic_triggers.json").read_text(encoding="utf-8")
    )
    interview = generate_semantic_readiness_interview(dataset_b_snapshot())
    assert interview["causal_roles_assigned"] is False
    assert interview["generic_questionnaire"] is False
    families = {item["question_family"] for item in interview["questions"]}
    assert families == set(expected["expected_families"])
    assert interview["semantic_status"] in {
        "MODELER_REVIEW_REQUIRED",
        "QUESTIONS_OPEN",
        "USER_CONTEXT_REQUIRED",
    }


def test_dataset_b_generation_contract(tmp_path: Path) -> None:
    output_root = tmp_path / "stride_and_field"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output-root", str(output_root)],
        check=True,
        cwd=ROOT,
    )
    dataset_dir = output_root / "dataset_b"
    raw_dir = dataset_dir / "raw"
    truth = pd.read_csv(dataset_dir / "truth" / "expected_model_ready_weekly.csv")
    microsoft = pd.read_csv(raw_dir / "microsoft_ads_daily.csv")
    tiktok = pd.read_csv(raw_dir / "tiktok_ads_daily.csv", dtype={"spend": str})
    amazon = pd.read_csv(raw_dir / "amazon_ads_weekly.csv")
    intent = load_model_intent(
        json.loads((raw_dir / "model_intent.json").read_text(encoding="utf-8"))
    )
    generation = json.loads((dataset_dir / "generation_manifest.json").read_text(encoding="utf-8"))
    expected = json.loads((output_root / "expected_manifest.json").read_text(encoding="utf-8"))

    assert expected["expected_defect_count"] == 12
    assert expected["business"] == "Stride & Field"
    assert intent.kpi.field == "orders"
    assert intent.revenue.field == "net_revenue"
    assert {channel.provider for channel in intent.paid_media} == {
        "microsoft_ads",
        "tiktok_ads",
        "amazon_ads",
    }
    assert "google_ads" not in {channel.provider for channel in intent.paid_media}
    assert truth["time"].nunique() == 156
    assert len(truth) == 936
    assert set(truth["geo"].unique()) == {"NE", "MA", "SE", "MW", "MT", "WE"}
    assert generation["seed"] == 20260817
    assert generation["files"]["truth/expected_model_ready_weekly.csv"]["rows"] == 936
    assert not (raw_dir / "expected_model_ready_weekly.csv").exists()
    inventoried = {item["path"] for item in inventory_files(raw_dir)}
    assert "expected_model_ready_weekly.csv" not in inventoried
    assert "model_intent.json" in inventoried
    assert microsoft.duplicated().sum() == 1
    assert tiktok["spend"].str.match(r"^\$[\d,]+\.\d{2}$").any()
    assert not tiktok["spend"].str.match(r"^\$[\d,]+\.\d{2}$").all()
    assert set(amazon["geo"].unique()) >= {"West Coast", "Northeast", "SE"}


def test_dataset_b_generation_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "one"
    second = tmp_path / "two"
    for output_root in (first, second):
        subprocess.run(
            [sys.executable, str(SCRIPT), "--output-root", str(output_root)],
            check=True,
            cwd=ROOT,
        )
    left = first / "dataset_b" / "generation_manifest.json"
    right = second / "dataset_b" / "generation_manifest.json"
    left_files = json.loads(left.read_text(encoding="utf-8"))["files"]
    right_files = json.loads(right.read_text(encoding="utf-8"))["files"]
    assert {name: info["sha256"] for name, info in left_files.items()} == {
        name: info["sha256"] for name, info in right_files.items()
    }


def test_dataset_b_seeded_defects_are_present() -> None:
    raw = FIXTURE / "raw"
    microsoft = pd.read_csv(raw / "microsoft_ads_daily.csv")
    tiktok = pd.read_csv(raw / "tiktok_ads_daily.csv", dtype={"spend": str})
    amazon = pd.read_csv(raw / "amazon_ads_weekly.csv")
    klaviyo = pd.read_csv(raw / "klaviyo_weekly.csv")
    weather = pd.read_csv(raw / "weather_weekly.csv")
    inactive = pd.read_csv(raw / "documented_inactive_periods.csv")
    truth = pd.read_csv(FIXTURE / "truth" / "expected_model_ready_weekly.csv")
    issues = json.loads((FIXTURE / "expected" / "expected_issues.json").read_text(encoding="utf-8"))

    assert issues["expected_defect_count"] == 12
    assert microsoft["timeperiod"].str.match(r"^\d{2}/\d{2}/\d{4}$").all()
    assert set(microsoft["campaign"].unique()) >= {
        "Brand Search",
        "Branded Search",
        "Search - Brand",
    }
    assert int(microsoft.duplicated().sum()) == 1
    assert tiktok["date"].nunique() > truth["time"].nunique()
    assert "product_group" in amazon.columns
    assert "attributed_sales" in amazon.columns
    assert {"open_rate", "click_rate", "send_count"} <= set(klaviyo.columns)
    assert len(weather) == 934
    assert len(inactive) == 4
    gap = truth[
        (truth["geo"] == "SE") & (truth["time"].isin(["2024-09-02", "2024-09-09", "2024-09-16"]))
    ]
    assert gap["retail_media_spend"].isna().all()
    missing_weather = truth[
        ((truth["geo"] == "MT") & (truth["time"] == "2024-07-01"))
        | ((truth["geo"] == "SE") & (truth["time"] == "2025-01-06"))
    ]
    assert missing_weather["weather_index"].isna().all()
    inactive_spend = truth[
        (truth["geo"] == "MT")
        & (truth["time"].isin(["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22"]))
    ]
    assert (inactive_spend["paid_social_video_spend"] == 0).all()


def test_dataset_b_forbidden_actions_are_persisted() -> None:
    payload = json.loads(
        (FIXTURE / "expected" / "expected_forbidden_actions.json").read_text(encoding="utf-8")
    )
    actions = {item["action"] for item in payload["actions"]}
    assert "zero_fill_unknown_amazon_gap" in actions
    assert "zero_fill_missing_weather_control" in actions
    assert "treat_klaviyo_open_rate_or_click_rate_as_additive_exposure" in actions
    assert "promote_a_lesson_because_dataset_b_exists" in actions
    assert "alter_dataset_c_summit_and_pine" in actions
    assert not (FIXTURE / "expected" / "expected_lesson.json").exists()
    assert not (FIXTURE / "expected" / "golden_promoted_lesson.json").exists()
    assert not (FIXTURE / "expected" / "expected_domain_view_v2.json").exists()


def test_dataset_b_semantic_triggers_match_families_not_wording() -> None:
    expected = json.loads(
        (FIXTURE / "expected" / "expected_semantic_triggers.json").read_text(encoding="utf-8")
    )
    snapshot = dataset_b_snapshot()
    families = {item["question_family"] for item in detect_semantic_question_triggers(snapshot)}
    assert families == set(expected["expected_families"])
    assert {
        "PROMOTION_TIMING",
        "PRICE_DISCOUNT_TIMING",
        "DOWNSTREAM_MEDIA",
        "ORGANIC_MEDIA_TIMING",
    } <= families
    assert expected["cannot_independently_block_model_ready"] is True


def test_dataset_b_run_intelligence_is_computed_not_guessed() -> None:
    expected = json.loads(
        (FIXTURE / "expected" / "expected_run_intelligence.json").read_text(encoding="utf-8")
    )
    snapshot = dataset_b_snapshot()
    budget = compute_parameter_budget(snapshot)
    assert budget["n_geos"] == expected["n_geos"] == 6
    assert budget["n_times"] == expected["n_times"] == 156
    assert budget["n_data_points"] == expected["n_data_points"] == 936
    assert budget["lenient"]["ratio"] == expected["lenient_ratio"]
    assert budget["interpretation"]["pressure_band"] == expected["pressure_band"]
    assert budget["interpretation"]["blocks_model_ready"] is False
    assert abs(float(expected["lenient_ratio"]) - 3.74) > 0.2
    assert expected["never_drop_confounder_for_ratio"] is True


def test_dataset_b_does_not_overwrite_music_center_or_dataset_c() -> None:
    music = json.loads((MUSIC_CENTER_B / "generation_manifest.json").read_text(encoding="utf-8"))
    holdout = json.loads(
        (DATASET_C / "learning" / "holdout_manifest.json").read_text(encoding="utf-8")
    )
    assert music["business"] == "Music Center"
    assert music["dataset"] == "dataset_b"
    assert holdout["dataset_identity"] == "dataset_c_summit_and_pine"
    assert holdout["sealed_before_candidate_extraction"] is True
    assert holdout["lesson_ids_visible_at_seal"] == []
    assert holdout["training_access"] == "DENIED"
    assert holdout["holdout_role"] == "SEALED_HOLDOUT"
    source = SCRIPT.read_text(encoding="utf-8")
    assert "generate_dataset_c" not in source
    assert "tests/fixtures/summit_and_pine" not in source
    assert "app.mel.holdout" not in source
    assert "app.synthetic.mmm" in source
    assert "overwrite_music_center_dataset_b" in source


def test_checked_in_dataset_b_matches_generator(tmp_path: Path) -> None:
    output_root = tmp_path / "stride_and_field"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output-root", str(output_root)],
        check=True,
        cwd=ROOT,
    )
    generated = json.loads(
        (output_root / "dataset_b" / "generation_manifest.json").read_text(encoding="utf-8")
    )
    checked = json.loads((FIXTURE / "generation_manifest.json").read_text(encoding="utf-8"))
    generated_truth = generated["files"]["truth/expected_model_ready_weekly.csv"]["sha256"]
    checked_truth = checked["files"]["truth/expected_model_ready_weekly.csv"]["sha256"]
    assert generated_truth == checked_truth
    assert sha256_file(FIXTURE / "raw" / "microsoft_ads_daily.csv") == checked["files"][
        "raw/microsoft_ads_daily.csv"
    ]["sha256"]
