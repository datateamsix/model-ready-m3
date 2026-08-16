"""Holdout seal and isolation.

Candidate extraction must not read holdout outcomes. The holdout is sealed
before promotion, with no lesson IDs visible at seal time.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.contracts import utc_now
from app.mel.fingerprint import fingerprint_payload
from app.mel.models import DatasetRole, HoldoutManifest, MelError

SEAL_NAME = "learning/holdout_manifest.json"
REJECTED_HOLDOUT_INPUT = "REJECTED_HOLDOUT_INPUT"


def is_holdout_episode(episode: object) -> bool:
    holdout = bool(getattr(episode, "holdout", False))
    role = getattr(episode, "dataset_role", None)
    return holdout or role is DatasetRole.SEALED_HOLDOUT


def reject_holdout_training(episode: object, *, action: str) -> None:
    if is_holdout_episode(episode):
        raise MelError(f"{REJECTED_HOLDOUT_INPUT}: {action} cannot use a sealed holdout episode")


def seal_holdout(
    *,
    dest: Path,
    dataset_identity: str,
    classification: str,
    input_package_fingerprint: str,
    schema_fingerprint: str,
    seed: int | None = None,
    generator_version: str | None = None,
    business: str | None = None,
    expected_contract_fingerprint: str | None = None,
    sealed_at: str | None = None,
    domain_view_version_at_seal: str | None = None,
    domain_view_fingerprint_at_seal: str | None = None,
    promoted_lesson_count_at_seal: int = 0,
    created_at: str | None = None,
) -> HoldoutManifest:
    dest.parent.mkdir(parents=True, exist_ok=True)
    created = created_at or utc_now().isoformat()
    manifest = HoldoutManifest(
        dataset_identity=dataset_identity,
        classification=classification,
        seed=seed,
        created_at=created,
        input_package_fingerprint=input_package_fingerprint,
        schema_fingerprint=schema_fingerprint,
        sealed_before_candidate_extraction=True,
        lesson_ids_visible_at_seal=[],
        generator_version=generator_version,
        business=business,
        holdout_role=DatasetRole.SEALED_HOLDOUT,
        expected_contract_fingerprint=expected_contract_fingerprint,
        sealed_at=sealed_at or created,
        domain_view_version_at_seal=domain_view_version_at_seal,
        domain_view_fingerprint_at_seal=domain_view_fingerprint_at_seal,
        promoted_lesson_count_at_seal=promoted_lesson_count_at_seal,
        training_access="DENIED",
        candidate_generation_access="DENIED",
        reflection_training_access="DENIED",
        evaluation_only=True,
    )
    dest.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def load_holdout_manifest(path: Path) -> HoldoutManifest:
    if not path.is_file():
        raise MelError(f"holdout manifest missing: {path}")
    return HoldoutManifest.model_validate_json(path.read_text(encoding="utf-8"))


def assert_sealed_before_extraction(manifest: HoldoutManifest) -> None:
    if not manifest.sealed_before_candidate_extraction:
        raise MelError("holdout was not sealed before candidate extraction")
    if manifest.lesson_ids_visible_at_seal:
        raise MelError("holdout seal must not include lesson IDs")


def isolation_fingerprint(training_episode_ids: list[str], holdout_id: str) -> str:
    if holdout_id in training_episode_ids:
        raise MelError("holdout episode cannot be a training episode")
    return fingerprint_payload(
        {"training": sorted(training_episode_ids), "holdout_excluded": holdout_id}
    )
