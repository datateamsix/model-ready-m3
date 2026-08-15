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
        .str.replace(r"[$,%]", "", regex=True)
        .str.strip()
    )
    result[column] = pd.to_numeric(cleaned, errors="raise")
    return result


def canonicalize_channel_labels(
    frame: pd.DataFrame,
    column: str,
    mapping: dict[str, str],
) -> pd.DataFrame:
    """Rewrite channel labels using an explicit mapping; unmapped values stay as strings."""
    result = frame.copy(deep=True)
    result[column] = result[column].map(lambda value: mapping.get(str(value), str(value)))
    return result


def aggregate_to_week(
    frame: pd.DataFrame,
    *,
    date_column: str,
    group_columns: list[str],
    sum_columns: list[str],
    week_column: str = "week_start",
) -> pd.DataFrame:
    """Aggregate summable columns to Monday-start weeks (period W-SUN)."""
    result = frame.copy(deep=True)
    parsed = pd.to_datetime(result[date_column], errors="raise")
    result[week_column] = parsed.dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
    groups = [week_column, *[column for column in group_columns if column != date_column]]
    aggregated = result.groupby(groups, dropna=False, as_index=False)[sum_columns].sum()
    return aggregated.copy(deep=True)
