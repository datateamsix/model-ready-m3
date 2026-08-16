"""Deterministic MEL fingerprints. Volatile timestamps are excluded."""

from __future__ import annotations

import hashlib
import json
from typing import Any

VOLATILE_KEYS = frozenset(
    {
        "generated_at",
        "created_at",
        "updated_at",
        "timestamp",
        "episode_started_at",
        "episode_closed_at",
        "candidate_created_at",
        "promotion_timestamp",
        "activated_at",
        "revoked_at",
        "sealed_at",
        "queried_at",
        "calculated_at",
        "recorded_at",
    }
)


def _strip(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip(item)
            for key, item in sorted(value.items())
            if key not in VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_strip(item) for item in value]
    return value


def fingerprint_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        _strip(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
