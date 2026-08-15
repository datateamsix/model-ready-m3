"""Safe deterministic remediation helpers."""

from __future__ import annotations

import pandas as pd

from app.tools.safety import assert_summable_columns, resolve_date_format


def normalize_dates(
    frame: pd.DataFrame,
    column: str,
    expected_format: str,
) -> pd.DataFrame:
    """Normalize dates using an explicit source format; fail closed on mismatch."""
    result = frame.copy(deep=True)
    fmt = resolve_date_format(expected_format)
    parsed = pd.to_datetime(result[column], format=fmt, errors="coerce")
    invalid = int(parsed.isna().sum())
    if invalid:
        raise ValueError(
            f"{invalid} values in {column} do not match expected format {expected_format}."
        )
    result[column] = parsed.dt.strftime("%Y-%m-%d")
    return result


def remove_exact_duplicates(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicate rows without mutating the source frame."""
    return frame.drop_duplicates().reset_index(drop=True).copy(deep=True)


def normalize_numeric_values(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """Coerce simple currency/commas to numeric values; fail on lossy conversion."""
    result = frame.copy(deep=True)
    cleaned = result[column].astype("string").str.replace(r"[$,%]", "", regex=True).str.strip()
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


def aggregate_campaign_to_channel(
    frame: pd.DataFrame,
    *,
    grain_columns: list[str],
    sum_columns: list[str],
    provider_id: str | None = None,
) -> pd.DataFrame:
    """Aggregate campaign/ad-group rows to modeled channel grain using summable metrics."""
    assert_summable_columns(sum_columns, provider_id)
    missing = [column for column in [*grain_columns, *sum_columns] if column not in frame.columns]
    if missing:
        raise KeyError(f"Aggregation columns not found: {missing}")
    result = frame.copy(deep=True)
    aggregated = result.groupby(grain_columns, dropna=False, as_index=False)[sum_columns].sum()
    return aggregated.copy(deep=True)


def aggregate_to_week(
    frame: pd.DataFrame,
    *,
    date_column: str,
    group_columns: list[str],
    sum_columns: list[str],
    week_column: str = "week_start",
    provider_id: str | None = None,
) -> pd.DataFrame:
    """Aggregate summable columns to Monday-start weeks (period W-SUN)."""
    assert_summable_columns(sum_columns, provider_id)
    result = frame.copy(deep=True)
    parsed = pd.to_datetime(result[date_column], format="%Y-%m-%d", errors="raise")
    result[week_column] = parsed.dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
    groups = [week_column, *[column for column in group_columns if column != date_column]]
    aggregated = result.groupby(groups, dropna=False, as_index=False)[sum_columns].sum()
    return aggregated.copy(deep=True)
