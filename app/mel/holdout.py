"""Holdout seal and isolation.

Candidate extraction must not read holdout outcomes. The holdout is sealed
before promotion, with no lesson IDs visible at seal time.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.contracts import utc_now
from app.mel.fingerprint import fingerprint_payload
from app.mel.models import HoldoutManifest, MelError

SEAL_NAME = "learning/holdout_manifest.json"


def seal_holdout(
    *,
    dest: Path,
    dataset_identity: str,
    classification: str,
    input_package_fingerprint: str,
    schema_fingerprint: str,
    seed: int | None = None,
    generator_version: str | None = None,
) -> HoldoutManifest:
    dest.parent.mkdir(parents=True, exist_ok=True)
    manifest = HoldoutManifest(
        dataset_identity=dataset_identity,
        classification=classification,
        seed=seed,
        created_at=utc_now().isoformat(),
        input_package_fingerprint=input_package_fingerprint,
        schema_fingerprint=schema_fingerprint,
        sealed_before_candidate_extraction=True,
        lesson_ids_visible_at_seal=[],
        generator_version=generator_version,
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
