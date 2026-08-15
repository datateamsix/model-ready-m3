import pandas as pd
import pytest

from app.tools.profiling import detect_grain
from app.tools.remediation import aggregate_to_week, canonicalize_channel_labels


def test_detect_grain_daily() -> None:
    frame = pd.DataFrame({"date": ["2026-01-01", "2026-01-02", "2026-01-03"]})
    result = detect_grain(frame, "date")
    assert result["grain"] == "daily"


def test_aggregate_to_week_sums_volume_not_rows_only() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2026-01-05", "2026-01-06", "2026-01-12"],
            "geo": ["TX", "TX", "TX"],
            "spend": [10.0, 15.0, 7.0],
        }
    )
    result = aggregate_to_week(
        frame,
        date_column="date",
        group_columns=["geo"],
        sum_columns=["spend"],
    )
    assert len(result) == 2
    first_week = result.loc[result["week_start"] == result["week_start"].min(), "spend"].iloc[0]
    assert first_week == 25.0


def test_canonicalize_channel_labels_maps_known_aliases() -> None:
    frame = pd.DataFrame({"channel": ["Meta", "Paid Social", "other"]})
    result = canonicalize_channel_labels(
        frame,
        "channel",
        {"Meta": "paid_social", "Paid Social": "paid_social"},
    )
    assert result["channel"].tolist() == ["paid_social", "paid_social", "other"]


def test_detect_grain_rejects_unparseable_dates() -> None:
    frame = pd.DataFrame({"date": ["not-a-date"]})
    with pytest.raises(ValueError):
        detect_grain(frame, "date")
