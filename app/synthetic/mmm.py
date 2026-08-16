"""Shared deterministic helpers for PreM3 synthetic MMM fixtures.

Music Center Dataset A/B (`scripts/generate_demo_data.py`), Stride & Field
Dataset B (`scripts/generate_dataset_b.py`), and Summit & Pine Dataset C
(`scripts/generate_dataset_c.py`) share these primitives so new fixtures
extend the existing generator stack instead of forking a second RNG or
hashing scheme.

Dataset C remains a sealed holdout. Sharing helpers does not make it
training evidence.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

import pandas as pd

from app.tools.artifacts import sha256_file

__all__ = [
    "csv_file_meta",
    "format_currency_usd",
    "json_file_meta",
    "monday_weeks",
    "sha256_file",
    "split_weekly_total",
    "stable_rng",
    "write_csv",
    "write_json",
]


def stable_rng(seed: int, *parts: object) -> random.Random:
    """Seed a stdlib RNG from SHA-256 of `seed` plus ordered parts.

    Identical to the Music Center generator's original `_stable_rng`.
    """
    raw = "|".join(str(part) for part in (seed, *parts))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def split_weekly_total(total: float, rng: random.Random) -> list[float]:
    """Split a weekly total across seven days with stable noise.

    Identical to the Music Center generator's original `_split_weekly_total`.
    """
    weights = [max(0.35, 1.0 + rng.uniform(-0.22, 0.22)) for _ in range(7)]
    denom = sum(weights)
    values = [total * weight / denom for weight in weights]
    adjustment = total - sum(values)
    values[-1] += adjustment
    return values


def monday_weeks(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="W-MON")


def format_currency_usd(value: float) -> str:
    return f"${value:,.2f}"


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def csv_file_meta(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "sha256": sha256_file(path),
    }


def json_file_meta(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "rows": None,
        "columns": sorted(payload),
        "sha256": sha256_file(path),
    }
