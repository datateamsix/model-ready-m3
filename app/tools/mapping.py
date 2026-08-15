"""Deterministic field mapping application.

Semantic mapping decisions may originate from an agent or registry lookup, but the
actual rename/select operation is deterministic and auditable.
"""

from __future__ import annotations

import pandas as pd

from app.tools.safety import validate_provider_mapping


def apply_mapping(
    frame: pd.DataFrame,
    mapping: dict[str, str],
    provider_id: str | None = None,
) -> pd.DataFrame:
    missing_sources = sorted(set(mapping) - set(frame.columns))
    if missing_sources:
        raise KeyError(f"Mapping source columns not found: {missing_sources}")
    if provider_id:
        validate_provider_mapping(provider_id, mapping)
    return frame.rename(columns=mapping).copy(deep=True)
