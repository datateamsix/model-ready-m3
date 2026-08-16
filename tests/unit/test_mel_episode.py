"""MEL ExperienceEpisode closure tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.contracts import DurableRunState
from app.core.run_repository import LocalFilesystemRunRepository
from app.core.state import RunStage
from app.mel.episode import close_experience_episode, episode_id_for, maybe_close_experience_episode
from app.mel.models import EpisodeTerminalOutcome, MelError
from app.tools.artifacts import write_json_artifact


def _repo(tmp_path: Path) -> LocalFilesystemRunRepository:
    return LocalFilesystemRunRepository(
        root=tmp_path,
        raw_bucket="raw",
        artifact_bucket="artifacts",
    )


def _state(run_id: str, stage: RunStage, status: str) -> DurableRunState:
    return DurableRunState(
        run_id=run_id,
        organization_id="music-center",
        workspace_id="mmm-demo",
        package_uri="gs://raw/music-center/mmm-demo/packages/dataset-a-v1/",
        package_fingerprint="pkg-fp",
        stage=stage,
        artifact_prefix="gs://artifacts/music-center/mmm-demo/runs/" + run_id,
        physical_schema_fingerprint="model-fp",
        status=status,
        detected_issue_ids=["i1"],
        resolved_issue_ids=["i1"],
        open_issue_ids=[],
    )


def _seed_run(repo: LocalFilesystemRunRepository, state: DurableRunState) -> None:
    repo.save_run(state)
    write_json_artifact(
        repo._artifact_path(state.run_id, "intelligence/pre_eda_diagnostic_receipt.json"),
        {
            "findings": [
                {
                    "finding_id": "PRE-PARAM-1",
                    "dimension": "PARAMETER_PRESSURE",
                    "title": "parameter pressure",
                }
            ]
        },
    )
    write_json_artifact(
        repo._artifact_path(state.run_id, "eda/meridian_eda_receipt.json"),
        {
            "findings": [
                {
                    "finding_id": "EDA-DA-1",
                    "check_type": "DATA_ADEQUACY",
                    "severity": "ATTENTION",
                },
                {
                    "finding_id": "EDA-VIF-1",
                    "check_type": "MULTICOLLINEARITY",
                    "severity": "INFO",
                },
            ]
        },
    )


def test_model_ready_run_closes_episode(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _state("run-ready", RunStage.MODEL_READY, "MODEL_READY")
    _seed_run(repo, state)
    episode = close_experience_episode("run-ready", repo=repo)
    assert episode.terminal_outcome is EpisodeTerminalOutcome.MODEL_READY
    assert episode.episode_id == episode_id_for("run-ready")
    assert episode.learning_eligible is True
    assert episode.content_fingerprint
    closed = close_experience_episode("run-ready", repo=repo)
    assert closed.content_fingerprint == episode.content_fingerprint
    assert any(item.kind == "pre_eda" and item.present for item in episode.evidence_index)
    assert any(item.relation.value in {"RELATED", "CONFIRMED"} for item in episode.alignments)


def test_user_required_and_failed_runs_close(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    blocked = _state("run-user", RunStage.WAITING_FOR_APPROVAL, "USER_REQUIRED")
    failed = _state("run-fail", RunStage.FAILED, "EDA_BLOCKED")
    _seed_run(repo, blocked)
    _seed_run(repo, failed)
    user_ep = close_experience_episode("run-user", repo=repo)
    fail_ep = close_experience_episode("run-fail", repo=repo)
    assert user_ep.terminal_outcome is EpisodeTerminalOutcome.USER_REQUIRED
    assert fail_ep.terminal_outcome is EpisodeTerminalOutcome.EDA_BLOCKED


def test_non_terminal_run_cannot_close(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _state("run-open", RunStage.PUBLISHING, "RUNNING")
    repo.save_run(state)
    with pytest.raises(MelError, match="non-terminal"):
        close_experience_episode("run-open", repo=repo)


def test_maybe_close_skips_non_terminal_and_survives_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    open_state = _state("run-open", RunStage.PUBLISHING, "RUNNING")
    repo.save_run(open_state)
    skipped = maybe_close_experience_episode("run-open", repo=repo)
    assert skipped["status"] == "SKIPPED"

    ready = _state("run-ready", RunStage.MODEL_READY, "MODEL_READY")
    _seed_run(repo, ready)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("mel crash")

    monkeypatch.setattr("app.mel.episode.close_experience_episode", _boom)
    failed = maybe_close_experience_episode("run-ready", repo=repo)
    assert failed["status"] == "MEL_EVALUATION_FAILED"
    assert "mel crash" in str(failed.get("error"))
