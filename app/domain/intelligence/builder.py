"""Compile, version, and persist DOMAIN_VIEW from structured sources.

The builder is not MEL. Promoted lessons are an input contract. MEL Episode
Core may supply evaluated lessons as data. This module does not rewrite
Python source to learn.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.contracts import utc_now
from app.domain.intelligence.diff import diff_domain_views, receipt_from_diff
from app.domain.intelligence.fingerprint import fingerprint_payload, operational_payload
from app.domain.intelligence.models import (
    ClaimStatus,
    DomainView,
    DomainViewClaim,
    DomainViewError,
    DomainViewSourceVersions,
    KnowledgeLayer,
    PromotedLessonInput,
    SourceType,
)
from app.domain.intelligence.render import render_domain_view_markdown
from app.domain.intelligence.sources import (
    DATA_DIR,
    REPO_ROOT,
    claims_from_base_file,
    claims_from_rule_catalogs,
    load_promoted_lessons,
    load_source_versions,
)
from app.domain.intelligence.validate import (
    layer_for_class,
    lesson_is_eligible,
    validate_claim_identity,
    validate_promoted_lesson,
)

CURRENT_JSON = DATA_DIR / "current" / "domain_view.json"
HISTORY_DIR = DATA_DIR / "history"
MARKDOWN_PATH = REPO_ROOT / "docs" / "context" / "domain-view" / "DOMAIN_VIEW.md"
RECEIPT_PATH = DATA_DIR / "current" / "domain_view_change_receipt.json"


def _next_version(previous: DomainView | None) -> str:
    if previous is None:
        return "1.0.0"
    major, minor, patch = (int(part) for part in previous.domain_view_version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def _lesson_to_claim(lesson: PromotedLessonInput) -> DomainViewClaim:
    return DomainViewClaim(
        claim_id=f"DV-EXP-{lesson.lesson_id}",
        statement=lesson.statement,
        knowledge_class=lesson.knowledge_class,
        layer=layer_for_class(lesson.knowledge_class),
        authority=lesson.authority,
        scope=lesson.scope,
        source_type=SourceType.PROMOTED_EXPERIENCE,
        source_refs=lesson.source_refs,
        source_version=lesson.lesson_id,
        evidence=lesson.evidence,
        regression_status=lesson.regression_status,
        behavior_effect=lesson.behavior_effect,
        applicability_conditions=list(lesson.applicability_conditions),
        first_added_at=lesson.last_validated_at,
        last_validated_at=lesson.last_validated_at,
        status=ClaimStatus.ACTIVE,
        prohibited_overrides=[
            "MERIDIAN_NORMATIVE",
            "PREM3_SAFETY_POLICY",
            "FINAL_MODEL_SPEC",
            "FINAL_PRIORS",
        ],
        experience_provenance=lesson.experience_provenance,
    )


def compile_claims(
    *,
    extra_lessons: list[PromotedLessonInput] | None = None,
    include_catalogs: bool = True,
    include_base: bool = True,
    promoted_path: Path | None = None,
) -> tuple[list[DomainViewClaim], str, int]:
    claims: list[DomainViewClaim] = []
    if include_catalogs:
        claims.extend(claims_from_rule_catalogs())
    if include_base:
        claims.extend(claims_from_base_file())
    lesson_version, file_lessons = load_promoted_lessons(promoted_path)
    accepted = 0
    for lesson in [*file_lessons, *(extra_lessons or [])]:
        if not lesson_is_eligible(lesson):
            continue
        validate_promoted_lesson(lesson, claims)
        claims.append(_lesson_to_claim(lesson))
        accepted += 1
    validate_claim_identity([claim.claim_id for claim in claims])
    if any(
        claim.layer is KnowledgeLayer.MERIDIAN_NORMATIVE
        and claim.source_type is SourceType.PROMOTED_EXPERIENCE
        for claim in claims
    ):
        raise DomainViewError("experience cannot be labeled MERIDIAN_NORMATIVE")
    return claims, lesson_version, accepted


def build_domain_view(
    *,
    previous: DomainView | None = None,
    extra_lessons: list[PromotedLessonInput] | None = None,
    generated_at: str | None = None,
    source_versions: DomainViewSourceVersions | None = None,
    include_catalogs: bool = True,
    include_base: bool = True,
    promoted_path: Path | None = None,
    status: str = "ACTIVE",
) -> DomainView:
    claims, lesson_version, accepted = compile_claims(
        extra_lessons=extra_lessons,
        include_catalogs=include_catalogs,
        include_base=include_base,
        promoted_path=promoted_path,
    )
    versions = source_versions or load_source_versions()
    digest = fingerprint_payload(
        operational_payload(
            claims,
            source_versions=versions.model_dump(mode="json"),
            promoted_lesson_set_version=lesson_version,
            promoted_lesson_count=accepted,
            status=status,
        )
    )
    if previous is not None and previous.content_fingerprint == digest:
        version = previous.domain_view_version
        previous_version = previous.previous_domain_view_version
    else:
        version = _next_version(previous)
        previous_version = previous.domain_view_version if previous else None
    return DomainView(
        domain_view_version=version,
        generated_at=generated_at or utc_now().isoformat(),
        source_versions=versions,
        promoted_lesson_set_version=lesson_version,
        promoted_lesson_count=accepted,
        content_fingerprint=digest,
        previous_domain_view_version=previous_version,
        status=status,
        claims=claims,
    )


def summarize_domain_view(view: DomainView) -> dict[str, object]:
    distribution: dict[str, int] = {}
    for claim in view.active_claims():
        key = claim.layer.value
        distribution[key] = distribution.get(key, 0) + 1
    return {
        "domain_view_version": view.domain_view_version,
        "content_fingerprint": view.content_fingerprint,
        "source_versions": view.source_versions.model_dump(mode="json"),
        "promoted_lesson_count": view.promoted_lesson_count,
        "claim_count": len(view.active_claims()),
        "authority_distribution": distribution,
        "previous_domain_view_version": view.previous_domain_view_version,
    }


def persist_domain_view(view: DomainView, previous: DomainView | None = None) -> None:
    CURRENT_JSON.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    MARKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = view.model_dump(mode="json")
    CURRENT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_path = HISTORY_DIR / f"domain_view_{view.domain_view_version}.json"
    history_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MARKDOWN_PATH.write_text(render_domain_view_markdown(view), encoding="utf-8")
    if previous is None or previous.content_fingerprint != view.content_fingerprint:
        diff = (
            diff_domain_views(previous, view)
            if previous is not None
            else diff_domain_views(
                DomainView(
                    domain_view_version="0.0.0",
                    generated_at=view.generated_at,
                    source_versions=view.source_versions,
                    promoted_lesson_set_version="0.0.0",
                    promoted_lesson_count=0,
                    content_fingerprint="",
                    claims=[],
                ),
                view,
            )
        )
        receipt = receipt_from_diff(
            previous,
            view,
            diff,
            timestamp=view.generated_at,
            source_reason="deterministic compile from structured intelligence sources",
        )
        RECEIPT_PATH.write_text(
            json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def load_current_domain_view() -> DomainView | None:
    if not CURRENT_JSON.exists():
        return None
    return DomainView.model_validate_json(CURRENT_JSON.read_text(encoding="utf-8"))


def rebuild_and_persist() -> DomainView:
    previous = load_current_domain_view()
    view = build_domain_view(previous=previous)
    persist_domain_view(view, previous)
    return view


__all__ = [
    "build_domain_view",
    "compile_claims",
    "load_current_domain_view",
    "persist_domain_view",
    "rebuild_and_persist",
    "summarize_domain_view",
]
