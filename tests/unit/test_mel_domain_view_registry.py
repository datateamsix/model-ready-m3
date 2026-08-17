"""DOMAIN_VIEW registry seed, GCS load, and bootstrap isolation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.intelligence.builder import load_current_domain_view
from app.mel.models import MelError
from app.mel.promote import (
    REGISTRY_GS_ENV,
    active_domain_view_meta,
    load_active_view,
    seed_bootstrap_registry,
)


def test_seed_bootstrap_registry_is_v1_with_zero_lessons(tmp_path: Path) -> None:
    bootstrap = load_current_domain_view()
    assert bootstrap is not None
    seeded = seed_bootstrap_registry(tmp_path)
    loaded = load_active_view(tmp_path)
    assert seeded.domain_view_version == bootstrap.domain_view_version
    assert loaded.content_fingerprint == bootstrap.content_fingerprint
    assert loaded.promoted_lesson_count == 0


def test_default_load_active_view_ignores_local_experiment_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODELREADY_DOMAIN_VIEW_REGISTRY_DIR", raising=False)
    monkeypatch.delenv(REGISTRY_GS_ENV, raising=False)
    bootstrap = load_current_domain_view()
    assert bootstrap is not None
    loaded = load_active_view()
    assert loaded.content_fingerprint == bootstrap.content_fingerprint
    assert loaded.promoted_lesson_count == 0
    meta = active_domain_view_meta()
    assert meta["source"] == "bootstrap"
    assert meta["promoted_lesson_count"] == 0


def test_load_active_view_from_gs_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seeded = seed_bootstrap_registry(tmp_path)

    def fake_download(uri: str, dest: str | Path) -> Path:
        name = uri.rstrip("/").rsplit("/", 1)[-1]
        target = Path(dest)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((tmp_path / name).read_bytes())
        return target

    cache = tmp_path / "cache"
    monkeypatch.setenv(REGISTRY_GS_ENV, "gs://bucket/experiments/cloud/domain_view_registry/")
    monkeypatch.setenv("MODELREADY_DOMAIN_VIEW_REGISTRY_CACHE_DIR", str(cache))
    monkeypatch.setattr("app.mel.promote.download_file", fake_download)
    loaded = load_active_view()
    assert loaded.content_fingerprint == seeded.content_fingerprint
    assert loaded.promoted_lesson_count == 0
    meta = active_domain_view_meta()
    assert meta["source"] == "gcs_registry"
    assert meta["domain_view_version"] == seeded.domain_view_version


def test_gcs_pointer_failure_does_not_fall_back_to_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(uri: str, dest: str | Path) -> Path:
        raise OSError("missing pointer")

    monkeypatch.setenv(REGISTRY_GS_ENV, "gs://bucket/missing/domain_view_registry/")
    monkeypatch.setenv("MODELREADY_DOMAIN_VIEW_REGISTRY_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr("app.mel.promote.download_file", boom)
    with pytest.raises(MelError, match="failed to load DOMAIN_VIEW registry pointer"):
        load_active_view()
