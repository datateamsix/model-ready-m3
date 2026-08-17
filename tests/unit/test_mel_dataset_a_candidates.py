"""Dataset A episode candidate extraction records rejects; it does not force a lesson."""

from __future__ import annotations

from pathlib import Path

from app.core.contracts import DurableRunState
from app.core.run_repository import LocalFilesystemRunRepository
from app.core.state import RunStage
from app.mel.candidates import propose_candidates_from_episode
from app.mel.episode import close_experience_episode
from app.mel.evaluate import evaluate_candidate
from app.mel.models import EvaluationDecision
from app.mel.reflect import reflect_on_experience_episode
from app.tools.artifacts import write_json_artifact
from tests.unit.authority_support import bind_run_authority


def test_dataset_a_like_episode_records_candidates_without_forcing_promotion(
    tmp_path: Path,
) -> None:
    repo = LocalFilesystemRunRepository(
        root=tmp_path, raw_bucket="raw", artifact_bucket="artifacts"
    )
    state = DurableRunState(
        run_id="dataset-a-episode",
        organization_id="music-center",
        workspace_id="mmm-demo",
        package_uri="gs://raw/music-center/mmm-demo/packages/dataset-a-v1/",
        package_fingerprint="pkg-a",
        stage=RunStage.MODEL_READY,
        artifact_prefix="gs://artifacts/music-center/mmm-demo/runs/dataset-a-episode",
        status="MODEL_READY",
        physical_schema_fingerprint="model-a",
    )
    with bind_run_authority(
        tenant_id="music-center",
        run_id=state.run_id,
        package_uri=state.package_uri,
    ):
        repo.save_run(state)
        write_json_artifact(
            repo._artifact_path(state.run_id, "intelligence/pre_eda_diagnostic_receipt.json"),
            {"findings": [{"finding_id": "PRE-PARAM", "dimension": "PARAMETER_PRESSURE"}]},
        )
        write_json_artifact(
            repo._artifact_path(
                state.run_id, "intelligence/semantic_readiness_interview.json"
            ),
            {"questions": [{"question_id": "SEM-1", "status": "OPEN"}]},
        )
        write_json_artifact(
            repo._artifact_path(state.run_id, "eda/meridian_eda_receipt.json"),
            {
                "findings": [
                    {
                        "finding_id": "EDA-DA",
                        "check_type": "DATA_ADEQUACY",
                        "severity": "ATTENTION",
                    },
                    {
                        "finding_id": "EDA-PRIOR",
                        "check_type": "PRIOR_PROBABILITY",
                        "severity": "INFO",
                    },
                ]
            },
        )
        episode = close_experience_episode(state.run_id, repo=repo)
        reflection = reflect_on_experience_episode(
            episode.episode_id, repo=repo, run_id=state.run_id
        )
    candidates = propose_candidates_from_episode(episode, reflection=reflection)
    assert candidates
    assert all(item.source_reflection_id == reflection.reflection_id for item in candidates)
    evaluations = [
        evaluate_candidate(candidate, episodes=[episode]) for candidate in candidates
    ]
    assert evaluations
    assert all(item.decision in EvaluationDecision for item in evaluations)
    assert EvaluationDecision.PROMOTE not in {item.decision for item in evaluations}
    assert reflection.operational_authority is False
    assert all(candidate.synthetic_fixture is False for candidate in candidates)
    assert {candidate.candidate_creator for candidate in candidates} == {
        "MEL_DETERMINISTIC_EXTRACTOR"
    }
