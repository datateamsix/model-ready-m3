"""Canonical locations for PreM3 full synthetic assignments.

Complete datasets live under `datasets/`. `tests/fixtures/` is reserved for
small isolated unit-test fixtures, not second copies of Dataset A/B/C.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS_ROOT = REPO_ROOT / "datasets"
MUSIC_CENTER_ROOT = DATASETS_ROOT / "music_center"
STRIDE_AND_FIELD_ROOT = DATASETS_ROOT / "stride_and_field"
SUMMIT_AND_PINE_ROOT = DATASETS_ROOT / "summit_and_pine"
DATASET_A_DIR = MUSIC_CENTER_ROOT / "dataset_a"
DATASET_B_DIR = STRIDE_AND_FIELD_ROOT / "dataset_b"
DATASET_C_DIR = SUMMIT_AND_PINE_ROOT / "dataset_c"
