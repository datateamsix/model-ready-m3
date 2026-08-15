"""Contract tests for the deterministic Music Center synthetic fixture generator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


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
    google = pd.read_csv(dataset_dir / "google_ads_daily.csv")
    meta = pd.read_csv(dataset_dir / "meta_ads_weekly.csv", dtype=str)
    truth = pd.read_csv(dataset_dir / "expected_model_ready_weekly.csv")
    generation = json.loads((dataset_dir / "generation_manifest.json").read_text())
    expected = json.loads((output_root / "expected_manifest.json").read_text())

    assert expected["dataset_a"]["expected_defect_count"] == 5
    assert google.duplicated().sum() == 1
    assert set(meta["channel"].unique()) == {"Meta", "Paid Social", "paid_social"}
    assert meta["amount_spent"].str.match(r"^\$[\d,]+\.\d{2}$").all()

    assert truth["time"].nunique() == 131
    assert len(truth) == 524
    assert int(truth.isna().sum().sum()) == 0
    assert set(truth["geo"].unique()) == {"CA", "TX", "FL", "NY"}

    generated_files = generation["files"]
    assert generated_files["google_ads_daily.csv"]["rows"] == 11_005
    assert generated_files["meta_ads_weekly.csv"]["rows"] == 1_572
    assert generated_files["expected_model_ready_weekly.csv"]["rows"] == 524
    assert all(file_info["sha256"] for file_info in generated_files.values())
