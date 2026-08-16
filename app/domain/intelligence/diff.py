"""Deterministic DOMAIN_VIEW comparison. Timestamps are not meaningful changes."""

from __future__ import annotations

from app.domain.intelligence.models import (
    ChangeType,
    DomainView,
    DomainViewChangeReceipt,
    DomainViewClaim,
    DomainViewDiff,
    SourceType,
)


def _index(view: DomainView) -> dict[str, DomainViewClaim]:
    return {claim.claim_id: claim for claim in view.claims}


def _operational(claim: DomainViewClaim) -> dict[str, object]:
    payload = claim.model_dump(mode="json")
    payload.pop("first_added_at", None)
    payload.pop("last_validated_at", None)
    return payload


def diff_domain_views(previous: DomainView, current: DomainView) -> DomainViewDiff:
    before = _index(previous)
    after = _index(current)
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified: list[str] = []
    authority_changes: list[dict[str, str]] = []
    scope_changes: list[dict[str, str]] = []
    source_updates: list[str] = []
    experiential: list[str] = []
    change_types: list[ChangeType] = []

    for claim_id in sorted(set(before) & set(after)):
        left = before[claim_id]
        right = after[claim_id]
        if _operational(left) == _operational(right):
            continue
        modified.append(claim_id)
        if left.authority != right.authority:
            authority_changes.append(
                {
                    "claim_id": claim_id,
                    "from": left.authority.value,
                    "to": right.authority.value,
                }
            )
            change_types.append(ChangeType.LESSON_AUTHORITY_CHANGE)
        if left.scope != right.scope:
            scope_changes.append(
                {
                    "claim_id": claim_id,
                    "from": left.scope.model_dump_json(),
                    "to": right.scope.model_dump_json(),
                }
            )
            change_types.append(ChangeType.LESSON_SCOPE_CHANGE)
        if left.source_type != right.source_type or left.source_refs != right.source_refs:
            source_updates.append(claim_id)
            if right.source_type is SourceType.PROMOTED_EXPERIENCE:
                experiential.append(claim_id)
            else:
                change_types.append(ChangeType.OFFICIAL_SOURCE_UPDATE)
        if left.status != right.status and right.status.value == "REVOKED":
            change_types.append(ChangeType.LESSON_REVOKED)
        if right.supersedes and right.supersedes == left.claim_id:
            change_types.append(ChangeType.LESSON_SUPERSEDED)

    for claim_id in added:
        claim = after[claim_id]
        if claim.source_type is SourceType.PROMOTED_EXPERIENCE:
            experiential.append(claim_id)
            change_types.append(ChangeType.EXPERIENCE_LEARNED)
        elif claim.source_type is SourceType.OFFICIAL_SOURCE:
            change_types.append(ChangeType.OFFICIAL_SOURCE_UPDATE)
        elif claim.source_type is SourceType.PREM3_POLICY:
            change_types.append(ChangeType.POLICY_UPDATE)
        else:
            change_types.append(ChangeType.HEURISTIC_UPDATE)

    if removed:
        change_types.append(ChangeType.LESSON_REVOKED)

    unique_types = list(dict.fromkeys(change_types))
    return DomainViewDiff(
        added_claim_ids=added,
        removed_claim_ids=removed,
        modified_claim_ids=modified,
        authority_changes=authority_changes,
        scope_changes=scope_changes,
        source_updates=source_updates,
        experiential_learning_changes=experiential,
        change_types=unique_types,
    )


def classify_learned_vs_source_update(diff: DomainViewDiff) -> dict[str, list[str]]:
    """Support 'What have you learned?' without calling source sync learning."""
    return {
        "experience_learned": list(diff.experiential_learning_changes),
        "source_or_policy_updates": [
            claim_id
            for claim_id in [*diff.added_claim_ids, *diff.modified_claim_ids]
            if claim_id not in diff.experiential_learning_changes
        ],
    }


def receipt_from_diff(
    previous: DomainView | None,
    current: DomainView,
    diff: DomainViewDiff,
    *,
    timestamp: str,
    source_reason: str,
) -> DomainViewChangeReceipt:
    experience_ids = [
        claim.experience_provenance.candidate_lesson_id
        for claim in current.claims
        if claim.claim_id in diff.experiential_learning_changes
        and claim.experience_provenance
        and claim.experience_provenance.candidate_lesson_id
    ]
    return DomainViewChangeReceipt(
        previous_version=previous.domain_view_version if previous else None,
        new_version=current.domain_view_version,
        previous_fingerprint=previous.content_fingerprint if previous else None,
        new_fingerprint=current.content_fingerprint,
        change_types=diff.change_types or [ChangeType.INITIAL_COMPILE],
        changed_claim_ids=sorted(
            {
                *diff.added_claim_ids,
                *diff.removed_claim_ids,
                *diff.modified_claim_ids,
            }
        ),
        source_reason=source_reason,
        experience_lesson_ids=experience_ids,
        timestamp=timestamp,
    )
