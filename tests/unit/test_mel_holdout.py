"""Holdout seal isolation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.mel.holdout import (
    assert_sealed_before_extraction,
    isolation_fingerprint,
    seal_holdout,
)
from app.mel.models import MelError


def test_holdout_seal_has_no_lesson_ids(tmp_path: Path) -> None:
    path = tmp_path / "learning" / "holdout_manifest.json"
    manifest = seal_holdout(
        dest=path,
        dataset_identity="dataset_c_summit_and_pine",
        classification="synthetic",
        input_package_fingerprint="pkg",
        schema_fingerprint="schema",
        seed=20260816,
        generator_version="1.0.0",
    )
    assert manifest.sealed_before_candidate_extraction is True
    assert manifest.lesson_ids_visible_at_seal == []
    assert_sealed_before_extraction(manifest)


def test_holdout_cannot_be_training_episode() -> None:
    with pytest.raises(MelError, match="holdout episode"):
        isolation_fingerprint(["ep-train", "ep-hold"], "ep-hold")
    digest = isolation_fingerprint(["ep-train"], "ep-hold")
    assert digest
