"""Table file I/O for deterministic tools."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_table(path: str | Path) -> pd.DataFrame:
    target = Path(path)
    suffix = target.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(target)
    if suffix == ".parquet":
        return pd.read_parquet(target)
    raise ValueError(f"Unsupported table suffix: {suffix}")


def write_table(frame: pd.DataFrame, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(target, index=False)
        return target
    if suffix == ".parquet":
        frame.to_parquet(target, index=False)
        return target
    raise ValueError(f"Unsupported table suffix: {suffix}")
