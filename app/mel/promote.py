"""Stage, regress, and activate DOMAIN_VIEW as versioned data.

Does not rewrite Python source. Ordinary agents cannot set the active view.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.core.contracts import utc_now
from app.domain.intelligence.builder import build_domain_view, load_current_domain_view
from app.domain.intelligence.diff import diff_domain_views
from app.domain.intelligence.models import (
    DomainView,
    KnowledgeClass,
    PromotedLessonInput,
    PromotionStatus,
)
from app.mel.fingerprint import fingerprint_payload
from app.mel.models import (
    CandidateLesson,
    DomainViewRegistryEntry,
    DomainViewRegistryStatus,
    LearningReceiptEnum,
    LessonEvaluation,
    MelError,
    PromotionReceipt,
    RegressionResult,
)

REGISTRY_NAME = "domain_view_registry.json"


def _lesson_input(candidate: CandidateLesson) -> PromotedLessonInput:
    knowledge = (
        KnowledgeClass.ADVISORY_LEARNED_PATTERN
        if candidate.requested_authority.value in {"ADVISORY", "ROUTING_HINT"}
        else KnowledgeClass.VALIDATED_EXPERIENCE_PATTERN
    )
    return PromotedLessonInput(
        lesson_id=candidate.candidate_lesson_id,
        statement=candidate.statement,
        knowledge_class=knowledge,
        authority=candidate.requested_authority,
        scope=candidate.scope,
        source_refs=list(candidate.source_episode_ids),
        evidence=list(candidate.supporting_evidence_refs),
        regression_status="PASSED",
        behavior_effect=candidate.expected_behavior_change,
        promotion_status=PromotionStatus.PROMOTED,
        last_validated_at=utc_now().date().isoformat(),
    )


def stage_domain_view(
    candidate: CandidateLesson,
    *,
    previous: DomainView | None = None,
) -> DomainView:
    baseline = previous or load_current_domain_view()
    if baseline is None:
        raise MelError("cannot stage DOMAIN_VIEW without bootstrap v1")
    return build_domain_view(
        previous=baseline,
        extra_lessons=[_lesson_input(candidate)],
        status="STAGED",
    )


def activate_promoted_view(
    *,
    candidate: CandidateLesson,
    evaluation: LessonEvaluation,
    staged: DomainView,
    previous: DomainView,
    regression: RegressionResult,
    registry_dir: Path,
) -> PromotionReceipt:
    if evaluation.decision.value != "PROMOTE":
        raise MelError("cannot activate a non-promoted candidate")
    if not regression.passed:
        raise MelError("cannot activate before regression PASS")
    if staged.content_fingerprint == previous.content_fingerprint:
        raise MelError("EXPERIENCE_LEARNED requires a DOMAIN_VIEW change")
    diff = diff_domain_views(previous, staged)
    if not diff.experiential_learning_changes:
        raise MelError("staged view has no promoted-experience claim")
    claim_id = diff.experiential_learning_changes[0]
    active = staged.model_copy(update={"status": "ACTIVE"})
    _write_registry(registry_dir, previous, active, candidate.candidate_lesson_id)
    _write_view(registry_dir / f"domain_view_{active.domain_view_version}.json", active)
    receipt = PromotionReceipt(
        candidate_lesson_id=candidate.candidate_lesson_id,
        source_episode_ids=list(candidate.source_episode_ids),
        evaluation_id=evaluation.evaluation_id,
        old_domain_view_version=previous.domain_view_version,
        old_domain_view_fingerprint=previous.content_fingerprint,
        new_domain_view_version=active.domain_view_version,
        new_domain_view_fingerprint=active.content_fingerprint,
        promoted_claim_id=claim_id,
        lesson_type=candidate.lesson_type,
        scope=candidate.scope,
        authority=candidate.requested_authority,
        behavior_effect=candidate.expected_behavior_change,
        regression_result=regression,
        promotion_timestamp=utc_now().isoformat(),
        receipt_type=LearningReceiptEnum.EXPERIENCE_LEARNED,
    )
    _write_json(
        registry_dir / "experience" / "promotion_receipt.json",
        receipt.model_dump(mode="json"),
    )
    return receipt


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_view(path: Path, view: DomainView) -> None:
    _write_json(path, view.model_dump(mode="json"))


def _write_registry(
    registry_dir: Path,
    previous: DomainView,
    active: DomainView,
    lesson_id: str,
) -> None:
    registry_dir.mkdir(parents=True, exist_ok=True)
    path = registry_dir / REGISTRY_NAME
    now = utc_now().isoformat()
    entries: list[dict[str, Any]] = []
    if path.is_file():
        entries = json.loads(path.read_text(encoding="utf-8")).get("entries") or []
    for item in entries:
        if item.get("status") == DomainViewRegistryStatus.ACTIVE.value:
            item["status"] = DomainViewRegistryStatus.SUPERSEDED.value
    entries.append(
        DomainViewRegistryEntry(
            domain_view_version=previous.domain_view_version,
            fingerprint=previous.content_fingerprint,
            previous_version=previous.previous_domain_view_version,
            status=DomainViewRegistryStatus.SUPERSEDED,
            promoted_lesson_ids=[],
            created_at=previous.generated_at,
            activated_at=None,
        ).model_dump(mode="json")
    )
    entries.append(
        DomainViewRegistryEntry(
            domain_view_version=active.domain_view_version,
            fingerprint=active.content_fingerprint,
            previous_version=previous.domain_view_version,
            status=DomainViewRegistryStatus.ACTIVE,
            promoted_lesson_ids=[lesson_id],
            created_at=now,
            activated_at=now,
        ).model_dump(mode="json")
    )
    pointer = {
        "active_version": active.domain_view_version,
        "active_fingerprint": active.content_fingerprint,
        "entries": entries,
        "pointer_fingerprint": fingerprint_payload(
            {
                "active_version": active.domain_view_version,
                "active_fingerprint": active.content_fingerprint,
            }
        ),
    }
    path.write_text(json.dumps(pointer, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_active_view(registry_dir: Path | None = None) -> DomainView:
    """Fail safe to checked-in bootstrap if no runtime pointer exists."""
    if registry_dir is None:
        raw = os.getenv("MODELREADY_DOMAIN_VIEW_REGISTRY_DIR", "").strip()
        registry_dir = Path(raw) if raw else None
    if registry_dir is not None:
        pointer = registry_dir / REGISTRY_NAME
        if pointer.is_file():
            payload = json.loads(pointer.read_text(encoding="utf-8"))
            version = payload.get("active_version")
            staged = registry_dir / f"domain_view_{version}.json"
            if staged.is_file():
                return DomainView.model_validate_json(staged.read_text(encoding="utf-8"))
    bootstrap = load_current_domain_view()
    if bootstrap is None:
        raise MelError("no DOMAIN_VIEW is available")
    return bootstrap
