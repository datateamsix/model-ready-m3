"""Deterministic field mapping application.

Semantic mapping decisions may originate from an agent or registry lookup, but the
actual rename/select operation is deterministic and auditable.
"""

from __future__ import annotations

import pandas as pd


def apply_mapping(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    missing_sources = sorted(set(mapping) - set(frame.columns))
    if missing_sources:
        raise KeyError(f"Mapping source columns not found: {missing_sources}")
    return frame.rename(columns=mapping).copy(deep=True)
