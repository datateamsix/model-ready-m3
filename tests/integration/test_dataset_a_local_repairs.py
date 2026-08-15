"""Local Phase 1 repair path against Music Center dataset_a.

Does not call Cloud Run. Does not read expected_model_ready_weekly.csv as a tool input.
That file is regression truth only, compared after deterministic repairs.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from app.tools.adk_tools import (
    aggregate_file_to_week,
    canonicalize_channel_labels_in_file,
    detect_duplicates_in_file,
    detect_grain_in_file,
    inventory_package,
    lookup_provider_card,
    normalize_dates_in_file,
    normalize_numeric_values_in_file,
    remove_exact_duplicates_from_file,
    validate_readiness_file,
)


def _generate_dataset_a(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    output_root = tmp_path / "music_center"
    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "generate_demo_data.py"),
            "--output-root",
            str(output_root),
            "--dataset",
            "dataset_a",
        ],
        check=True,
        cwd=repo_root,
    )
    return output_root / "dataset_a"


def test_dataset_a_auto_safe_repairs_and_match_regression_truth(tmp_path: Path) -> None:
    dataset_dir = _generate_dataset_a(tmp_path)
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "repaired"
    raw_dir.mkdir()
    out_dir.mkdir()
    for name in ("google_ads_daily.csv", "meta_ads_weekly.csv"):
        shutil.copy(dataset_dir / name, raw_dir / name)

    inventory = inventory_package(str(raw_dir))
    assert {item["path"] for item in inventory["files"]} == {
        "google_ads_daily.csv",
        "meta_ads_weekly.csv",
    }
    assert lookup_provider_card("google_ads_daily.csv")["entry"]["trust"] == "executable"
    assert lookup_provider_card("meta_ads_weekly.csv")["entry"]["trust"] == "executable"

    google_raw = str(raw_dir / "google_ads_daily.csv")
    assert detect_grain_in_file(google_raw, "date")["grain"] == "daily"
    dups = detect_duplicates_in_file(google_raw, ["date", "geo", "campaign"])
    assert dups["duplicate_count"] == 2
    google_deduped = str(out_dir / "google_deduped.csv")
    dedup = remove_exact_duplicates_from_file(google_raw, google_deduped)
    assert dedup["input_rows"] == 11_005
    assert dedup["output_rows"] == 11_004
    google_weekly = str(out_dir / "google_weekly.csv")
    weekly = aggregate_file_to_week(
        google_deduped,
        "date",
        ["geo", "channel"],
        ["impressions", "clicks", "cost"],
        google_weekly,
    )
    assert weekly["output_rows"] == 1_048
    google_ready = validate_readiness_file(
        google_weekly,
        ["week_start", "geo", "channel", "cost"],
        ["week_start", "geo", "channel"],
        "week_start",
    )
    assert google_ready["all_passed"] is True

    meta_raw = str(raw_dir / "meta_ads_weekly.csv")
    meta_dates = str(out_dir / "meta_dates.csv")
    normalize_dates_in_file(meta_raw, "week_start", meta_dates)
    meta_numeric = str(out_dir / "meta_numeric.csv")
    normalize_numeric_values_in_file(meta_dates, "amount_spent", meta_numeric)
    meta_channels = str(out_dir / "meta_channels.csv")
    channels = canonicalize_channel_labels_in_file(
        meta_numeric,
        "channel",
        {"Meta": "paid_social", "Paid Social": "paid_social", "paid_social": "paid_social"},
        meta_channels,
    )
    assert channels["unmapped_values"] == []
    meta_weekly = str(out_dir / "meta_weekly.csv")
    aggregate_file_to_week(
        meta_channels,
        "week_start",
        ["geo", "channel"],
        ["impressions", "clicks", "amount_spent"],
        meta_weekly,
    )
    meta_ready = validate_readiness_file(
        meta_weekly,
        ["week_start", "geo", "channel", "amount_spent"],
        ["week_start", "geo", "channel"],
        "week_start",
    )
    assert meta_ready["all_passed"] is True

    raw_google = pd.read_csv(google_raw)
    assert len(raw_google) == 11_005
    truth = pd.read_csv(dataset_dir / "expected_model_ready_weekly.csv")
    google_frame = pd.read_csv(google_weekly)
    meta_frame = pd.read_csv(meta_weekly)
    google_spend = (
        google_frame.groupby(["week_start", "geo", "channel"], as_index=False)["cost"]
        .sum()
        .rename(columns={"week_start": "time", "cost": "spend"})
    )
    search = google_spend[google_spend["channel"] == "paid_search"][["time", "geo", "spend"]]
    shopping = google_spend[google_spend["channel"] == "shopping"][["time", "geo", "spend"]]
    social = meta_frame.rename(columns={"week_start": "time", "amount_spent": "spend"})[
        ["time", "geo", "spend"]
    ]
    merged = truth.merge(search, on=["time", "geo"], how="left", suffixes=("", "_search"))
    merged = merged.merge(shopping, on=["time", "geo"], how="left", suffixes=("", "_shopping"))
    merged = merged.merge(social, on=["time", "geo"], how="left", suffixes=("", "_social"))
    assert (merged["paid_search_spend"] - merged["spend"]).abs().max() < 0.05
    assert (merged["shopping_spend"] - merged["spend_shopping"]).abs().max() < 0.05
    assert (merged["paid_social_spend"] - merged["spend_social"]).abs().max() < 0.05
