import pandas as pd

from app.tools.profiling import detect_duplicates, profile_dataframe


def test_profile_detects_duplicate_rows() -> None:
    frame = pd.DataFrame({"date": ["2026-01-01", "2026-01-01"], "spend": [10, 10]})
    profile = profile_dataframe(frame)
    assert profile["row_count"] == 2
    assert profile["duplicate_rows"] == 1


def test_detect_duplicates_can_use_canonical_grain() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-01", "2026-01-08"],
            "channel": ["Search", "Search", "Search"],
        }
    )
    result = detect_duplicates(frame, ["date", "channel"])
    assert result["duplicate_count"] == 2
