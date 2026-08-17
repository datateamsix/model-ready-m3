"""Dataset B episode/reflection proof. Generation is not EXPERIENCE_LEARNED."""

from __future__ import annotations

from pathlib import Path

from app.core.contracts import DurableRunState
from app.core.run_repository import LocalFilesystemRunRepository
from app.core.state import RunStage
from app.domain.intelligence.builder import load_current_domain_view
from app.mel.candidates import (
    propose_candidates_from_episode,
    propose_cross_episode_candidates,
)
from app.mel.episode import close_experience_episode
from app.mel.evaluate import evaluate_candidate
from app.mel.models import EvaluationDecision, MelError
from app.mel.reflect import reflect_on_experience_episode
from app.tools.artifacts import write_json_artifact
from tests.unit.authority_support import bind_run_authority

DOMAIN_VIEW_FINGERPRINT = (
    "b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf"
)


def _repo(tmp_path: Path) -> LocalFilesystemRunRepository:
    return LocalFilesystemRunRepository(
        root=tmp_path, raw_bucket="raw", artifact_bucket="artifacts"
    )


def _seed_run(
    repo: LocalFilesystemRunRepository,
    run_id: str,
    *,
    organization_id: str,
    package_uri: str,
) -> None:
    state = DurableRunState(
        run_id=run_id,
        organization_id=organization_id,
        workspace_id="mmm-demo",
        package_uri=package_uri,
        package_fingerprint=f"pkg-{run_id}",
        stage=RunStage.MODEL_READY,
        artifact_prefix=f"gs://artifacts/{organization_id}/mmm-demo/runs/{run_id}",
        status="MODEL_READY",
        physical_schema_fingerprint=f"model-{run_id}",
    )
    with bind_run_authority(
        tenant_id=organization_id, run_id=run_id, package_uri=package_uri
    ):
        repo.save_run(state)
        write_json_artifact(
            repo._artifact_path(run_id, "intelligence/pre_eda_diagnostic_receipt.json"),
            {"findings": [{"finding_id": "PRE-PARAM", "dimension": "PARAMETER_PRESSURE"}]},
        )
        write_json_artifact(
            repo._artifact_path(run_id, "intelligence/semantic_readiness_interview.json"),
            {"questions": [{"question_id": "SEM-1", "status": "OPEN"}]},
        )
        write_json_artifact(
            repo._artifact_path(run_id, "eda/meridian_eda_receipt.json"),
            {
                "findings": [
                    {
                        "finding_id": "EDA-DA",
                        "check_type": "DATA_ADEQUACY",
                        "severity": "ATTENTION",
                    }
                ]
            },
        )


def test_dataset_b_episode_and_reflection_do_not_change_domain_view(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed_run(
        repo,
        "dataset-b-stride-field",
        organization_id="stride-and-field",
        package_uri="gs://raw/stride-and-field/packages/dataset-b-v1/",
    )
    before = load_current_domain_view()
    assert before is not None
    assert before.domain_view_version == "1.0.0"
    assert before.content_fingerprint == DOMAIN_VIEW_FINGERPRINT
    assert before.promoted_lesson_count == 0

    episode = None
    reflection = None
    with bind_run_authority(
        tenant_id="stride-and-field",
        run_id="dataset-b-stride-field",
        package_uri="gs://raw/stride-and-field/packages/dataset-b-v1/",
    ):
        episode = close_experience_episode("dataset-b-stride-field", repo=repo)
        reflection = reflect_on_experience_episode(
            episode.episode_id, repo=repo, run_id="dataset-b-stride-field"
        )
    candidates = propose_candidates_from_episode(episode, reflection=reflection)
    evaluations = [evaluate_candidate(candidate, episodes=[episode]) for candidate in candidates]

    after = load_current_domain_view()
    assert after is not None
    assert after.content_fingerprint == before.content_fingerprint
    assert after.domain_view_version == "1.0.0"
    assert reflection.operational_authority is False
    assert EvaluationDecision.PROMOTE not in {item.decision for item in evaluations}
    assert all(candidate.synthetic_fixture is False for candidate in candidates)


def test_dataset_a_plus_b_candidates_are_reported_without_forced_promotion(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed_run(
        repo,
        "dataset-a-episode",
        organization_id="music-center",
        package_uri="gs://raw/music-center/packages/dataset-a-v1/",
    )
    _seed_run(
        repo,
        "dataset-b-stride-field",
        organization_id="stride-and-field",
        package_uri="gs://raw/stride-and-field/packages/dataset-b-v1/",
    )
    with bind_run_authority(
        tenant_id="music-center",
        run_id="dataset-a-episode",
        package_uri="gs://raw/music-center/packages/dataset-a-v1/",
    ):
        episode_a = close_experience_episode("dataset-a-episode", repo=repo)
        reflection_a = reflect_on_experience_episode(
            episode_a.episode_id, repo=repo, run_id="dataset-a-episode"
        )
    with bind_run_authority(
        tenant_id="stride-and-field",
        run_id="dataset-b-stride-field",
        package_uri="gs://raw/stride-and-field/packages/dataset-b-v1/",
    ):
        episode_b = close_experience_episode("dataset-b-stride-field", repo=repo)
        reflection_b = reflect_on_experience_episode(
            episode_b.episode_id, repo=repo, run_id="dataset-b-stride-field"
        )
    candidates = propose_cross_episode_candidates(
        [episode_a, episode_b],
        [reflection_a, reflection_b],
    )
    assert candidates
    cross = [item for item in candidates if item.independent_context_count == 2]
    assert cross
    assert all(item.source_episode_ids == sorted(item.source_episode_ids) for item in cross)
    assert all(len(item.source_reflection_ids) == 2 for item in cross)
    evaluations = [
        evaluate_candidate(candidate, episodes=[episode_a, episode_b]) for candidate in candidates
    ]
    assert evaluations
    assert EvaluationDecision.PROMOTE not in {item.decision for item in evaluations}
    view = load_current_domain_view()
    assert view is not None
    assert view.content_fingerprint == DOMAIN_VIEW_FINGERPRINT
    assert view.promoted_lesson_count == 0


def test_cross_episode_candidates_reject_holdout_episodes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed_run(
        repo,
        "dataset-a-episode",
        organization_id="music-center",
        package_uri="gs://raw/music-center/packages/dataset-a-v1/",
    )
    _seed_run(
        repo,
        "dataset-c-holdout",
        organization_id="summit-and-pine",
        package_uri="gs://raw/summit-and-pine/packages/dataset-c-v1/",
    )
    with bind_run_authority(
        tenant_id="music-center",
        run_id="dataset-a-episode",
        package_uri="gs://raw/music-center/packages/dataset-a-v1/",
    ):
        episode_a = close_experience_episode("dataset-a-episode", repo=repo)
        reflection_a = reflect_on_experience_episode(
            episode_a.episode_id, repo=repo, run_id="dataset-a-episode"
        )
    with bind_run_authority(
        tenant_id="summit-and-pine",
        run_id="dataset-c-holdout",
        package_uri="gs://raw/summit-and-pine/packages/dataset-c-v1/",
    ):
        episode_c = close_experience_episode("dataset-c-holdout", repo=repo)
        episode_c.holdout = True
        reflection_c = reflect_on_experience_episode(
            episode_c.episode_id, repo=repo, run_id="dataset-c-holdout"
        )
    try:
        propose_cross_episode_candidates([episode_a, episode_c], [reflection_a, reflection_c])
        raise AssertionError("holdout episodes must not enter cross-episode extraction")
    except MelError as exc:
        assert "holdout" in str(exc)
