"""ExperienceReflection: evaluation of a closed episode. No operational authority."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

from app.core.contracts import utc_now
from app.core.run_repository import RunRepository
from app.mel.episode import load_episode, persist_episode
from app.mel.fingerprint import fingerprint_payload
from app.mel.models import (
    AlignmentRelation,
    DatasetRole,
    EvidenceRef,
    ExpectationStatus,
    ExperienceEpisode,
    ExperienceReflection,
    LearningReceiptEnum,
    MelError,
    ReflectionItem,
    ReflectionRole,
    ReflectionSurface,
)
from app.tools.artifacts import write_json_artifact

REFLECTION_RELATIVE = "experience/experience_reflection.json"
REFLECTION_VERSION = "1.0.0"
FORBIDDEN_REFLECTION_KEYS = (
    "chain_of_thought",
    "scratchpad",
    "hidden_reasoning",
    "private_thoughts",
    "cot",
    "raw_thinking",
)


def reflection_id_for(episode_id: str, episode_fingerprint: str) -> str:
    digest = hashlib.sha256(
        f"reflection:{episode_id}:{episode_fingerprint}".encode()
    ).hexdigest()[:16]
    return f"ref-{digest}"


def _item(
    surface: ReflectionSurface,
    item_id: str,
    statement: str,
    origin: str,
    evidence_refs: list[str] | None = None,
) -> ReflectionItem:
    return ReflectionItem(
        item_id=item_id,
        surface=surface,
        statement=statement,
        origin=origin,
        evidence_refs=evidence_refs or [],
    )


def _persisted_expectation(
    episode: ExperienceEpisode,
) -> tuple[ExpectationStatus, list[ReflectionItem]]:
    summary = episode.summary or {}
    recorded = summary.get("expected_resolution") or summary.get("expected_routing")
    if not recorded:
        return ExpectationStatus.NOT_RECORDED, [
            _item(
                ReflectionSurface.EXPECTED,
                "expected-not-recorded",
                "No persisted expectation was recorded before the outcome.",
                "EPISODE",
                ["episode.summary"],
            )
        ]
    return ExpectationStatus.RECORDED, [
        _item(
            ReflectionSurface.EXPECTED,
            "expected-recorded",
            str(recorded),
            "EPISODE",
            ["episode.summary"],
        )
    ]


def build_experience_reflection(episode: ExperienceEpisode) -> ExperienceReflection:
    present = [item.kind for item in episode.evidence_index if item.present]
    missing = [item.kind for item in episode.evidence_index if not item.present]
    alignments = episode.alignments
    confirmed = [
        item
        for item in alignments
        if item.relation in {AlignmentRelation.CONFIRMED, AlignmentRelation.RELATED}
    ]
    missed = [item for item in alignments if item.relation is AlignmentRelation.NEW_EDA_SIGNAL]
    incomplete = [
        item for item in alignments if item.relation is AlignmentRelation.PRECHECK_ONLY
    ]
    expected_status, expected_items = _persisted_expectation(episode)

    known = [
        _item(
            ReflectionSurface.KNOWN_AT_DECISION_TIME,
            "known-domain-view",
            (
                f"DOMAIN_VIEW {episode.domain_view_version} "
                f"(fingerprint {episode.domain_view_fingerprint}) was the authorized view."
            ),
            "DOMAIN_VIEW",
            ["episode.domain_view_version", "episode.domain_view_fingerprint"],
        )
    ]
    observed = [
        _item(
            ReflectionSurface.OBSERVED,
            f"observed-{kind}",
            f"Evidence kind present: {kind}.",
            "PREM3",
            [kind],
        )
        for kind in present
    ]
    if episode.organization_id:
        observed.append(
            _item(
                ReflectionSurface.OBSERVED,
                "observed-org-scoped",
                "Organization-scoped run context was present and remains non-global.",
                "RUN",
                ["episode.organization_id"],
            )
        )
    determined = [
        _item(
            ReflectionSurface.DETERMINED,
            "determined-terminal",
            f"Assignment closed as {episode.terminal_outcome.value}.",
            "PREM3",
            ["episode.terminal_outcome"],
        )
    ]
    believed = [
        _item(
            ReflectionSurface.BELIEVED,
            f"believed-{item.relation.value}-{idx}",
            item.reason,
            "DETERMINISTIC_ALIGNMENT",
            [item.prem3_finding_id or item.meridian_finding_id or "alignment"],
        )
        for idx, item in enumerate(alignments)
    ]
    allowed = [
        _item(
            ReflectionSurface.ALLOWED,
            "allowed-routing-cap",
            "First-cycle learned authority is capped at ROUTING_HINT / ADVISORY.",
            "PREM3_POLICY",
            ["app/rules/mel_promotion_policy.yaml"],
        ),
        _item(
            ReflectionSurface.ALLOWED,
            "allowed-meridian-severity",
            "Official Meridian remains authoritative for official EDA severity.",
            "MERIDIAN_NORMATIVE",
            ["official_eda"],
        ),
        _item(
            ReflectionSurface.ALLOWED,
            "allowed-model-ready-separation",
            "Reflection and MEL evaluation cannot change MODEL_READY.",
            "PREM3_POLICY",
            ["MODEL_READY"],
        ),
    ]
    unknown = [
        _item(
            ReflectionSurface.UNKNOWN,
            f"unknown-missing-{kind}",
            f"Evidence kind was not persisted: {kind}.",
            "PREM3",
            [kind],
        )
        for kind in missing
    ]
    if "semantic" in present:
        unknown.append(
            _item(
                ReflectionSurface.UNKNOWN,
                "unknown-semantic",
                "Semantic-readiness questions remained unresolved causal/context gaps.",
                "PREM3",
                ["semantic"],
            )
        )
    actual = [
        _item(
            ReflectionSurface.ACTUAL_OUTCOME,
            "actual-terminal",
            episode.terminal_outcome.value,
            "PREM3",
            ["episode.terminal_outcome"],
        )
    ]
    for item in alignments:
        if item.meridian_finding_id:
            actual.append(
                _item(
                    ReflectionSurface.ACTUAL_OUTCOME,
                    f"actual-meridian-{item.meridian_finding_id}",
                    (
                        f"Official Meridian finding {item.meridian_finding_id} "
                        f"({item.relation.value})."
                    ),
                    "OFFICIAL_MERIDIAN",
                    [item.meridian_finding_id],
                )
            )
    confirmed_items = [
        _item(
            ReflectionSurface.CONFIRMED,
            f"confirmed-{item.prem3_finding_id or idx}",
            (
                f"PreM3 {item.prem3_finding_id} is {item.relation.value} with "
                f"official {item.meridian_finding_id}."
            ),
            "OFFICIAL_MERIDIAN",
            [item.prem3_finding_id or "", item.meridian_finding_id or ""],
        )
        for idx, item in enumerate(confirmed)
    ]
    missed_items = [
        _item(
            ReflectionSurface.MISSED,
            f"missed-{item.meridian_finding_id or idx}",
            (
                f"Official Meridian finding {item.meridian_finding_id} had no mapped "
                "PreM3 pre-EDA counterpart."
            ),
            "OFFICIAL_MERIDIAN",
            [item.meridian_finding_id or "official_eda"],
        )
        for idx, item in enumerate(missed)
    ]
    incomplete_items = [
        _item(
            ReflectionSurface.INCOMPLETE,
            f"incomplete-{item.prem3_finding_id or idx}",
            f"PreM3 finding {item.prem3_finding_id} had no official Meridian counterpart.",
            "PREM3",
            [item.prem3_finding_id or "pre_eda"],
        )
        for idx, item in enumerate(incomplete)
    ]
    human_added: list[ReflectionItem] = []
    if "semantic" in present:
        human_added.append(
            _item(
                ReflectionSurface.HUMAN_ADDED,
                "human-semantic-channel",
                (
                    "Semantic interview persisted; human/modeler answers remain the "
                    "source of causal context."
                ),
                "HUMAN",
                ["semantic"],
            )
        )
    meridian_added = [
        _item(
            ReflectionSurface.MERIDIAN_ADDED,
            f"meridian-added-{item.meridian_finding_id or idx}",
            f"Official Meridian introduced {item.meridian_finding_id}.",
            "OFFICIAL_MERIDIAN",
            [item.meridian_finding_id or "official_eda"],
        )
        for idx, item in enumerate(missed)
    ]
    effective: list[ReflectionItem] = []
    if episode.terminal_outcome.value == "MODEL_READY":
        effective.append(
            _item(
                ReflectionSurface.EFFECTIVE_ACTIONS,
                "effective-ready",
                "The assignment reached MODEL_READY under deterministic gates.",
                "PREM3",
                ["episode.terminal_outcome"],
            )
        )
    surprises: list[ReflectionItem] = []
    if expected_status is ExpectationStatus.RECORDED:
        surprises.append(
            _item(
                ReflectionSurface.SURPRISES,
                "surprise-compare",
                "A persisted expectation existed; compare it to the recorded terminal outcome.",
                "EPISODE",
                ["episode.summary", "episode.terminal_outcome"],
            )
        )
    possible: list[ReflectionItem] = []
    if missed_items:
        possible.append(
            _item(
                ReflectionSurface.POSSIBLE_IMPROVEMENTS,
                "improve-handoff-official",
                (
                    "Possible future routing: prioritize official Meridian findings "
                    "PreM3 did not surface."
                ),
                "REFLECTION",
                ["alignments", "official_eda"],
            )
        )
    if "semantic" in present:
        possible.append(
            _item(
                ReflectionSurface.POSSIBLE_IMPROVEMENTS,
                "improve-semantic-first",
                (
                    "Possible future routing: surface unresolved semantic questions "
                    "before numeric commentary."
                ),
                "REFLECTION",
                ["semantic"],
            )
        )
    for item in possible:
        item.statement = (
            item.statement + " This is reflective evidence only and has no authority."
        )

    risk = (
        "Episode-specific evidence, organization-scoped facts, and a single assignment "
        "do not by themselves justify a reusable global lesson."
    )
    summary = (
        f"Closed {episode.terminal_outcome.value} episode {episode.episode_id}. "
        f"Confirmed alignments: {len(confirmed_items)}. "
        f"Missed official signals: {len(missed_items)}. "
        f"Unknown/unresolved: {len(unknown)}. "
        f"Expected: {expected_status.value}. "
        "Possible improvements are not lessons."
    )
    identity = {
        "episode_id": episode.episode_id,
        "episode_fingerprint": episode.content_fingerprint,
        "domain_view_version": episode.domain_view_version,
        "domain_view_fingerprint": episode.domain_view_fingerprint,
        "terminal_outcome": episode.terminal_outcome.value,
        "present": present,
        "alignment_relations": [item.relation.value for item in alignments],
        "expected_status": expected_status.value,
        "possible_improvement_ids": [item.item_id for item in possible],
    }
    return ExperienceReflection(
        reflection_id=reflection_id_for(episode.episode_id, episode.content_fingerprint),
        episode_id=episode.episode_id,
        run_id=episode.run_id,
        episode_fingerprint=episode.content_fingerprint,
        domain_view_version_used=episode.domain_view_version,
        domain_view_fingerprint_used=episode.domain_view_fingerprint,
        created_at=utc_now().isoformat(),
        reflection_version=REFLECTION_VERSION,
        known_at_decision_time=known,
        observed=observed,
        determined=determined,
        believed=believed,
        allowed=allowed,
        unknown=unknown,
        expected=expected_items,
        expected_status=expected_status,
        actual_outcome=actual,
        confirmed=confirmed_items,
        missed=missed_items,
        incomplete=incomplete_items,
        human_added=human_added,
        meridian_added=meridian_added,
        effective_actions=effective,
        ineffective_or_unnecessary_actions=[],
        surprises=surprises,
        possible_improvements=possible,
        generalization_risk=risk,
        reflection_summary=summary,
        content_fingerprint=fingerprint_payload(identity),
        operational_authority=False,
        reflection_role=(
            ReflectionRole.EVALUATION_ONLY
            if episode.holdout or episode.dataset_role is DatasetRole.SEALED_HOLDOUT
            else ReflectionRole.TRAINING
        ),
    )


def persist_reflection(repo: RunRepository, reflection: ExperienceReflection) -> str:
    root = Path(tempfile.mkdtemp(prefix="prem3-reflection-"))
    path = root / REFLECTION_RELATIVE
    payload = reflection.model_dump(mode="json")
    for key in FORBIDDEN_REFLECTION_KEYS:
        payload.pop(key, None)
    write_json_artifact(path, payload)
    return repo.upload_workspace_file(reflection.run_id, path, REFLECTION_RELATIVE)


def load_reflection(repo: RunRepository, run_id: str) -> ExperienceReflection | None:
    payload = repo.load_json(run_id, REFLECTION_RELATIVE)
    if payload is None:
        return None
    return ExperienceReflection.model_validate(payload)


def reflect_on_experience_episode(
    episode_id: str,
    *,
    repo: RunRepository,
    run_id: str,
) -> ExperienceReflection:
    episode = load_episode(repo, run_id)
    if episode is None or episode.episode_id != episode_id:
        raise MelError(f"closed episode not found: {episode_id}")
    existing = load_reflection(repo, run_id)
    if existing is not None and existing.episode_fingerprint == episode.content_fingerprint:
        return existing
    reflection = build_experience_reflection(episode)
    persist_reflection(repo, reflection)
    if not any(item.kind == "reflection" for item in episode.evidence_index):
        episode.evidence_index.append(
            EvidenceRef(
                kind="reflection",
                path=REFLECTION_RELATIVE,
                fingerprint=reflection.content_fingerprint,
                present=True,
            )
        )
    episode.reflection_id = reflection.reflection_id
    persist_episode(repo, episode)
    return reflection


def reflection_has_no_learning_receipt(reflection: ExperienceReflection) -> bool:
    dumped = reflection.model_dump(mode="json")
    text = str(dumped)
    return (
        reflection.operational_authority is False
        and LearningReceiptEnum.EXPERIENCE_LEARNED.value not in text
        and LearningReceiptEnum.EXPERIENCE_APPLIED.value not in text
    )


def fixture_reflection(
    episode: ExperienceEpisode, **overrides: Any
) -> ExperienceReflection:
    reflection = build_experience_reflection(episode)
    payload = reflection.model_dump(mode="json")
    payload.update(overrides)
    result = ExperienceReflection.model_validate(payload)
    result.operational_authority = False
    return result
