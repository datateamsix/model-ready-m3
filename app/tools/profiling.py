"""Deterministic dataset profiling primitives."""

from __future__ import annotations

from typing import Any

import pandas as pd


def profile_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
    """Return a compact, deterministic profile suitable for rule evaluation."""
    return {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": [str(column) for column in frame.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        "missing": {str(column): int(value) for column, value in frame.isna().sum().items()},
        "duplicate_rows": int(frame.duplicated().sum()),
    }


def detect_duplicates(frame: pd.DataFrame, subset: list[str] | None = None) -> dict[str, Any]:
    mask = frame.duplicated(subset=subset, keep=False)
    return {
        "duplicate_count": int(mask.sum()),
        "subset": subset or [],
        "row_indexes": [int(index) for index in frame.index[mask].tolist()],
    }


def detect_grain(frame: pd.DataFrame, date_column: str) -> dict[str, Any]:
    """Infer daily/weekly/monthly grain from unique parsed dates."""
    parsed = pd.to_datetime(frame[date_column], errors="raise")
    unique = parsed.sort_values().drop_duplicates()
    if len(unique) < 2:
        return {
            "grain": "unknown",
            "median_days": None,
            "unique_periods": int(len(unique)),
            "date_column": date_column,
        }
    deltas = unique.diff().dt.days.dropna()
    median_days = float(deltas.median())
    grain = "irregular"
    if median_days <= 1.5:
        grain = "daily"
    elif 5.0 <= median_days <= 9.0:
        grain = "weekly"
    elif 27.0 <= median_days <= 32.0:
        grain = "monthly"
    return {
        "grain": grain,
        "median_days": median_days,
        "unique_periods": int(len(unique)),
        "date_column": date_column,
    }
