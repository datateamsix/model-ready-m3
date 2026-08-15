"""Safe deterministic remediation helpers."""

from __future__ import annotations

import pandas as pd


def normalize_dates(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """Normalize unambiguous date values to YYYY-MM-DD in a copied frame."""
    result = frame.copy(deep=True)
    parsed = pd.to_datetime(result[column], errors="raise", utc=False)
    result[column] = parsed.dt.strftime("%Y-%m-%d")
    return result


def remove_exact_duplicates(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicate rows without mutating the source frame."""
    return frame.drop_duplicates().reset_index(drop=True).copy(deep=True)


def normalize_numeric_values(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """Coerce simple currency/commas to numeric values; fail on lossy conversion."""
    result = frame.copy(deep=True)
    cleaned = (
        result[column]
        .astype("string")
        .str.replace(r"[$,]", "", regex=True)
        .str.strip()
    )
    result[column] = pd.to_numeric(cleaned, errors="raise")
    return result
