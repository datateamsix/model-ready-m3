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
