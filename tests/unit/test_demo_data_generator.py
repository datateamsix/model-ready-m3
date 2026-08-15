"""Contract tests for the deterministic Music Center synthetic fixture generator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from app.core.model_intent import load_model_intent
from app.tools.inventory import inventory_files


def test_dataset_a_generation_contract(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "generate_demo_data.py"
    output_root = tmp_path / "music_center"

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-root",
            str(output_root),
            "--dataset",
            "dataset_a",
        ],
        check=True,
        cwd=repo_root,
    )

    dataset_dir = output_root / "dataset_a"
    raw_dir = dataset_dir / "raw"
    truth_dir = dataset_dir / "truth"
    google = pd.read_csv(raw_dir / "google_ads_daily.csv")
    meta = pd.read_csv(raw_dir / "meta_ads_weekly.csv", dtype=str)
    truth = pd.read_csv(truth_dir / "expected_model_ready_weekly.csv")
    intent = load_model_intent(
        json.loads((raw_dir / "model_intent.json").read_text(encoding="utf-8"))
    )
    generation = json.loads((dataset_dir / "generation_manifest.json").read_text())
    expected = json.loads((output_root / "expected_manifest.json").read_text())

    assert expected["dataset_a"]["expected_defect_count"] == 5
    assert google.duplicated().sum() == 1
    assert set(meta["channel"].unique()) == {"Meta", "Paid Social", "paid_social"}
    assert meta["amount_spent"].str.match(r"^\$[\d,]+\.\d{2}$").all()
    assert intent.kpi.field == "orders"
    assert intent.revenue.field == "net_revenue"

    assert truth["time"].nunique() == 131
    assert len(truth) == 524
    assert int(truth.isna().sum().sum()) == 0
    assert set(truth["geo"].unique()) == {"CA", "TX", "FL", "NY"}

    generated_files = generation["files"]
    assert generated_files["raw/google_ads_daily.csv"]["rows"] == 11_005
    assert generated_files["raw/meta_ads_weekly.csv"]["rows"] == 1_572
    assert generated_files["truth/expected_model_ready_weekly.csv"]["rows"] == 524
    assert all(file_info["sha256"] for file_info in generated_files.values())
    assert not (raw_dir / "expected_model_ready_weekly.csv").exists()
    assert not (dataset_dir / "expected_model_ready_weekly.csv").exists()

    inventoried = {item["path"] for item in inventory_files(raw_dir)}
    assert "expected_model_ready_weekly.csv" not in inventoried
    assert not any("expected_model_ready" in str(path) for path in inventoried)
    assert "model_intent.json" in inventoried
    assert "google_ads_daily.csv" in inventoried
