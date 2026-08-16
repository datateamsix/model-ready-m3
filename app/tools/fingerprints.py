"""Canonical content fingerprints for local artifacts and BigQuery parity.

BigQuery can change physical dtypes (dbdate, Int64, float64 vs int64) without
changing values. Fingerprints are semantic, not byte-identical:

- dates become YYYY-MM-DD strings;
- integers become nullable Int64 after numeric coercion;
- floats are rounded to FLOAT_DECIMALS (6);
- key order is time, geo (mergesort);
- nulls become empty cells.

Values and grain remain invariant. Do not claim raw Arrow/BQ bytes match.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

import pandas as pd

FLOAT_DECIMALS = 6
DATE_COLUMNS = {"time", "date", "week_start", "week_start_date"}


def normalize_logical_type(
    dtype_name: str,
    series: pd.Series | None = None,
    column_name: str | None = None,
) -> str:
    if column_name in DATE_COLUMNS:
        return "date"
    if series is not None:
        if pd.api.types.is_datetime64_any_dtype(series):
            return "date"
        if pd.api.types.is_bool_dtype(series):
            return "bool"
        if pd.api.types.is_integer_dtype(series):
            return "int"
        if pd.api.types.is_float_dtype(series):
            return "float"
    name = str(dtype_name).lower()
    if "datetime" in name or name in {"dbdate", "date"}:
        return "date"
    if "bool" in name:
        return "bool"
    if "int" in name:
        return "int"
    if "float" in name or "double" in name or "numeric" in name:
        return "float"
    return "string"


def schema_signature(
    frame: pd.DataFrame, columns: Iterable[str] | None = None
) -> list[tuple[str, str]]:
    ordered = list(columns) if columns is not None else list(frame.columns)
    signature: list[tuple[str, str]] = []
    for column in ordered:
        signature.append(
            (column, normalize_logical_type(str(frame[column].dtype), frame[column], column))
        )
    return signature


def canonicalize_frame(
    frame: pd.DataFrame,
    *,
    columns: list[str],
    key_columns: list[str],
) -> pd.DataFrame:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"Fingerprint columns missing: {missing}")
    result = frame.loc[:, columns].copy()
    result = result.sort_values(key_columns, kind="mergesort").reset_index(drop=True)
    for column in columns:
        logical = normalize_logical_type(str(result[column].dtype), result[column], column)
        if logical == "date":
            parsed = pd.to_datetime(result[column], errors="coerce")
            result[column] = parsed.dt.strftime("%Y-%m-%d")
        elif logical == "int":
            result[column] = pd.to_numeric(result[column], errors="coerce").round().astype("Int64")
        elif logical == "float":
            result[column] = pd.to_numeric(result[column], errors="coerce").round(FLOAT_DECIMALS)
    return result


def content_fingerprint(
    frame: pd.DataFrame,
    *,
    columns: list[str],
    key_columns: list[str],
) -> str:
    canonical = canonicalize_frame(frame, columns=columns, key_columns=key_columns)
    lines: list[str] = ["\t".join(columns)]
    for row in canonical.itertuples(index=False, name=None):
        cells: list[str] = []
        for value in row:
            if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
                cells.append("")
            elif isinstance(value, float):
                cells.append(f"{value:.{FLOAT_DECIMALS}f}")
            else:
                cells.append(str(value))
        lines.append("\t".join(cells))
    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
