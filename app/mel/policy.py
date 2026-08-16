"""Machine-readable MEL promotion policy."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.domain.intelligence.models import LearnedAuthority
from app.mel.models import MelError

POLICY_PATH = Path(__file__).resolve().parents[1] / "rules" / "mel_promotion_policy.yaml"


@lru_cache(maxsize=1)
def load_promotion_policy() -> dict[str, Any]:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def first_cycle_authority_cap() -> LearnedAuthority:
    value = str(load_promotion_policy().get("authority_cap") or "ROUTING_HINT")
    return LearnedAuthority(value)


def auto_safe_eligible() -> bool:
    return bool(
        load_promotion_policy()
        .get("requirements", {})
        .get("AUTO_SAFE_POLICY", {})
        .get("eligible_in_first_cycle")
    )


def requirements_for(authority: LearnedAuthority) -> dict[str, Any]:
    block = load_promotion_policy().get("requirements", {}).get(authority.value)
    if not block:
        raise MelError(f"no promotion requirements for {authority.value}")
    return dict(block)
