"""MEL orchestrator isolation and fail-closed promotion tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.contracts import DurableRunState
from app.core.execution_context import bind_service_execution
from app.core.run_repository import LocalFilesystemRunRepository
from app.core.state import RunStage
from app.mel.episode import close_experience_episode
from app.mel.models import EvaluationDecision, LearningReceiptEnum, MelError
from app.mel.orchestrator import evaluate_experience_episode
from app.tools.artifacts import write_json_artifact
from app.tools.run_tools import RUN_READY_TOOLS


def _repo(tmp_path: Path) -> LocalFilesystemRunRepository:
    return LocalFilesystemRunRepository(
        root=tmp_path,
        raw_bucket="raw",
        artifact_bucket="artifacts",
    )


def _seed_terminal(repo: LocalFilesystemRunRepository, run_id: str, *, holdout: bool) -> str:
    state = DurableRunState(
        run_id=run_id,
        organization_id="music-center",
        workspace_id="mmm-demo",
        package_uri=f"gs://raw/packages/{run_id}/",
        package_fingerprint="pkg-fp",
        stage=RunStage.MODEL_READY,
        artifact_prefix=f"gs://artifacts/runs/{run_id}",
        status="MODEL_READY",
        physical_schema_fingerprint="model-fp",
    )
    with bind_service_execution(
        tenant_id="music-center",
        workspace_id="mmm-demo",
        run_id=run_id,
        package_uri=state.package_uri,
    ):
        repo.save_run(state)
        write_json_artifact(
            repo._artifact_path(run_id, "intelligence/pre_eda_diagnostic_receipt.json"),
            {"findings": [{"finding_id": "PRE-1", "dimension": "PARAMETER_PRESSURE"}]},
        )
        write_json_artifact(
            repo._artifact_path(run_id, "eda/meridian_eda_receipt.json"),
            {
                "findings": [
                    {
                        "finding_id": "EDA-1",
                        "check_type": "DATA_ADEQUACY",
                        "severity": "ATTENTION",
                    }
                ]
            },
        )
        write_json_artifact(
            repo._artifact_path(run_id, "intelligence/semantic_readiness_interview.json"),
            {"questions": [{"question_id": "SEM-1", "status": "OPEN"}]},
        )
        episode = close_experience_episode(run_id, repo=repo, holdout=holdout)
        return episode.episode_id


def test_holdout_episode_is_inaccessible_to_candidate_generation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    episode_id = _seed_terminal(repo, "run-holdout", holdout=True)
    with bind_service_execution(
        tenant_id="music-center",
        workspace_id="mmm-demo",
        run_id="run-holdout",
        package_uri="gs://raw/packages/run-holdout/",
    ):
        with pytest.raises(MelError, match="holdout"):
            evaluate_experience_episode(
                episode_id,
                repo=repo,
                run_id="run-holdout",
                ledger_dir=tmp_path / "ledger",
                registry_dir=tmp_path / "registry",
            )


def test_evaluate_does_not_promote_without_regression(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    episode_id = _seed_terminal(repo, "run-train", holdout=False)
    with bind_service_execution(
        tenant_id="music-center",
        workspace_id="mmm-demo",
        run_id="run-train",
        package_uri="gs://raw/packages/run-train/",
    ):
        first = evaluate_experience_episode(
            episode_id,
            repo=repo,
            run_id="run-train",
            ledger_dir=tmp_path / "ledger",
            registry_dir=tmp_path / "registry",
        )
        second = evaluate_experience_episode(
            episode_id,
            repo=repo,
            run_id="run-train",
            ledger_dir=tmp_path / "ledger",
            registry_dir=tmp_path / "registry",
        )
    assert first["candidate_count"] >= 1
    assert first["experience_learned"] is False
    assert second["experience_learned"] is False
    assert first["status"] == LearningReceiptEnum.NO_SAFE_PROMOTABLE_LESSON.value
    assert EvaluationDecision.PROMOTE.value not in first["decision_summary"]
    assert first["promoted"] is None
    assert second["promoted"] is None


def test_gemini_cannot_call_promotion_tools() -> None:
    names = {fn.__name__ for fn in RUN_READY_TOOLS}
    assert "evaluate_experience_episode" not in names
    assert "set_domain_view" not in names
    assert "activate_promoted_view" not in names
    assert "complete_dataset_run" in names
