"""Dataset C holdout is sealed before candidate extraction."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT / "tests/fixtures/summit_and_pine/dataset_c/learning/holdout_manifest.json"
)
GENERATION = ROOT / "tests/fixtures/summit_and_pine/dataset_c/generation_manifest.json"


def test_dataset_c_holdout_is_sealed_without_lessons() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    generation = json.loads(GENERATION.read_text(encoding="utf-8"))
    assert payload["sealed_before_candidate_extraction"] is True
    assert payload["lesson_ids_visible_at_seal"] == []
    assert payload["classification"] == "synthetic"
    assert payload["dataset_identity"] == "dataset_c_summit_and_pine"
    assert generation["business"] == "Summit & Pine"
    assert "TikTok Ads" in generation["providers"]
    assert "Google Ads" not in generation["providers"]
