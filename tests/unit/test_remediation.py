import pandas as pd
import pytest

from app.tools.remediation import normalize_dates, normalize_numeric_values, remove_exact_duplicates


def test_remove_exact_duplicates_does_not_mutate_source() -> None:
    source = pd.DataFrame({"a": [1, 1, 2]})
    result = remove_exact_duplicates(source)
    assert len(source) == 3
    assert len(result) == 2


def test_normalize_numeric_values_handles_currency_strings() -> None:
    source = pd.DataFrame({"spend": ["$1,200.50", "25"]})
    result = normalize_numeric_values(source, "spend")
    assert result["spend"].tolist() == [1200.5, 25.0]


def test_normalize_dates_outputs_iso_date() -> None:
    source = pd.DataFrame({"date": ["01/15/2026"]})
    result = normalize_dates(source, "date", "MM/DD/YYYY")
    assert result.loc[0, "date"] == "2026-01-15"


def test_normalize_dates_fails_closed_on_format_mismatch() -> None:
    source = pd.DataFrame({"date": ["2026-01-15"]})
    with pytest.raises(ValueError):
        normalize_dates(source, "date", "MM/DD/YYYY")
