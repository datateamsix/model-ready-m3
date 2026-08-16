"""Content-addressable DOMAIN_VIEW fingerprint.

Volatile fields such as generated_at and version labels are excluded so a
rebuild of the same operational knowledge yields the same digest.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.domain.intelligence.models import DomainView, DomainViewClaim


def _claim_payload(claim: DomainViewClaim) -> dict[str, Any]:
    payload = claim.model_dump(mode="json")
    payload.pop("first_added_at", None)
    payload.pop("last_validated_at", None)
    return payload


def operational_payload(
    claims: list[DomainViewClaim],
    *,
    source_versions: dict[str, Any],
    promoted_lesson_set_version: str,
    promoted_lesson_count: int,
    status: str,
) -> dict[str, Any]:
    ordered = sorted((_claim_payload(claim) for claim in claims), key=lambda item: item["claim_id"])
    return {
        "claims": ordered,
        "source_versions": source_versions,
        "promoted_lesson_set_version": promoted_lesson_set_version,
        "promoted_lesson_count": promoted_lesson_count,
        "status": status,
    }


def fingerprint_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def fingerprint_view_content(view: DomainView) -> str:
    return fingerprint_payload(
        operational_payload(
            view.claims,
            source_versions=view.source_versions.model_dump(mode="json"),
            promoted_lesson_set_version=view.promoted_lesson_set_version,
            promoted_lesson_count=view.promoted_lesson_count,
            status=view.status,
        )
    )
