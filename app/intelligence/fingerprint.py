"""Deterministic content fingerprinting that ignores volatile timestamps."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.intelligence.contracts import VOLATILE_FINGERPRINT_KEYS


def content_fingerprint_payload(
    payload: Any, *, exclude: frozenset[str] = VOLATILE_FINGERPRINT_KEYS
) -> str:
    canonical = _strip_volatile(payload, exclude)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strip_volatile(value: Any, exclude: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_volatile(item, exclude) for key, item in value.items() if key not in exclude
        }
    if isinstance(value, list):
        return [_strip_volatile(item, exclude) for item in value]
    return value
