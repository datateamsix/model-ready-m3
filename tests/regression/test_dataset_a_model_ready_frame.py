"""Full-frame regression: independently assembled Dataset A vs truth/.

Runtime M3 never loads the truth file. This harness does so only after assembly.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.model_intent import INTEGER_MODEL_COLUMNS, MODEL_READY_COLUMNS
from app.core.run_coordinator import RunCoordinator

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_A_RAW = REPO_ROOT / "tests" / "fixtures" / "music_center" / "dataset_a" / "raw"
DATASET_A_TRUTH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "music_center"
    / "dataset_a"
    / "truth"
    / "expected_model_ready_weekly.csv"
)


def test_dataset_a_independently_matches_regression_truth(tmp_path: Path) -> None:
    coordinator = RunCoordinator(DATASET_A_RAW, tmp_path / "artifacts")
    coordinator.run_local()
    produced = pd.read_csv(coordinator.model_ready_path)
    truth = pd.read_csv(DATASET_A_TRUTH)

    assert list(produced.columns) == MODEL_READY_COLUMNS
    assert list(truth.columns) == MODEL_READY_COLUMNS
    assert len(produced) == 524
    assert len(truth) == 524
    assert int(produced.isna().sum().sum()) == 0

    produced_sorted = produced.sort_values(["time", "geo"]).reset_index(drop=True)
    truth_sorted = truth.sort_values(["time", "geo"]).reset_index(drop=True)
    assert produced_sorted[["time", "geo"]].equals(truth_sorted[["time", "geo"]])
    assert set(produced_sorted["geo"].unique()) == {"CA", "FL", "NY", "TX"}

    for column in INTEGER_MODEL_COLUMNS:
        if "impressions" in column:
            delta = (produced_sorted[column] - truth_sorted[column]).abs().max()
            assert delta <= 8, f"{column} daily-rounding delta {delta} exceeds 8"
        else:
            pd.testing.assert_series_equal(
                produced_sorted[column],
                truth_sorted[column],
                check_names=False,
                check_dtype=False,
            )

    spend_cols = ["paid_search_spend", "shopping_spend", "paid_social_spend"]
    for column in spend_cols:
        delta = (produced_sorted[column] - truth_sorted[column]).abs().max()
        assert delta < 0.05, f"{column} spend delta {delta}"

    pd.testing.assert_series_equal(
        produced_sorted["kpi_revenue"],
        truth_sorted["kpi_revenue"],
        check_names=False,
        check_dtype=False,
    )
    revenue_delta = (
        (produced_sorted["revenue_per_kpi"] - truth_sorted["revenue_per_kpi"]).abs().max()
    )
    assert revenue_delta <= 0.01

    for column in ("consumer_sentiment_index", "competitor_discount_index"):
        pd.testing.assert_series_equal(
            produced_sorted[column],
            truth_sorted[column],
            check_names=False,
            check_dtype=False,
        )
