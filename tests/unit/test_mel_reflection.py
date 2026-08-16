"""ExperienceReflection tests. Reflection has no operational authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.contracts import DurableRunState
from app.core.run_repository import LocalFilesystemRunRepository
from app.core.state import RunStage
from app.domain.intelligence.builder import load_current_domain_view
from app.mel.candidates import propose_candidates_from_episode
from app.mel.episode import close_experience_episode
from app.mel.evaluate import evaluate_candidate
from app.mel.models import (
    EvaluationDecision,
    ExpectationStatus,
    LearningReceiptEnum,
    MelError,
)
from app.mel.reflect import (
    FORBIDDEN_REFLECTION_KEYS,
    REFLECTION_RELATIVE,
    build_experience_reflection,
    reflect_on_experience_episode,
    reflection_has_no_learning_receipt,
)
from app.tools.artifacts import write_json_artifact


def _repo(tmp_path: Path) -> LocalFilesystemRunRepository:
    return LocalFilesystemRunRepository(
        root=tmp_path,
        raw_bucket="raw",
        artifact_bucket="artifacts",
    )


def _seed(
    repo: LocalFilesystemRunRepository,
    run_id: str,
    *,
    stage: RunStage = RunStage.MODEL_READY,
    status: str = "MODEL_READY",
) -> None:
    state = DurableRunState(
        run_id=run_id,
        organization_id="music-center",
        workspace_id="mmm-demo",
        package_uri=f"gs://raw/packages/{run_id}/",
        package_fingerprint="pkg-fp",
        stage=stage,
        artifact_prefix=f"gs://artifacts/runs/{run_id}",
        status=status,
        physical_schema_fingerprint="model-fp",
    )
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
                },
                {
                    "finding_id": "EDA-PRIOR",
                    "check_type": "PRIOR_PROBABILITY",
                    "severity": "INFO",
                },
            ]
        },
    )


def test_only_closed_episodes_can_be_reflected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(MelError, match="closed episode not found"):
        reflect_on_experience_episode("ep-missing", repo=repo, run_id="missing")


def test_reflection_references_episode_and_is_deterministic(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed(repo, "run-ref")
    episode = close_experience_episode("run-ref", repo=repo)
    first = reflect_on_experience_episode(episode.episode_id, repo=repo, run_id="run-ref")
    second = build_experience_reflection(episode)
    assert first.episode_id == episode.episode_id
    assert first.run_id == episode.run_id
    assert first.episode_fingerprint == episode.content_fingerprint
    assert first.content_fingerprint == second.content_fingerprint
    assert first.operational_authority is False
    loaded = repo.load_json("run-ref", REFLECTION_RELATIVE)
    assert loaded is not None
    assert loaded["reflection_id"] == first.reflection_id


def test_official_meridian_origin_and_no_hidden_reasoning(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed(repo, "run-ref")
    episode = close_experience_episode("run-ref", repo=repo)
    reflection = reflect_on_experience_episode(
        episode.episode_id, repo=repo, run_id="run-ref"
    )
    dumped = reflection.model_dump(mode="json")
    for key in FORBIDDEN_REFLECTION_KEYS:
        assert key not in dumped
    meridian_items = [
        item for item in reflection.actual_outcome if item.origin == "OFFICIAL_MERIDIAN"
    ]
    assert meridian_items
    assert all(item.origin == "OFFICIAL_MERIDIAN" for item in reflection.meridian_added)


def test_absent_expectation_is_not_invented(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed(repo, "run-ref")
    episode = close_experience_episode("run-ref", repo=repo)
    reflection = build_experience_reflection(episode)
    assert reflection.expected_status is ExpectationStatus.NOT_RECORDED
    assert reflection.surprises == []
    assert "No persisted expectation" in reflection.expected[0].statement


def test_reflection_cannot_learn_or_change_domain_view(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed(repo, "run-ref")
    episode = close_experience_episode("run-ref", repo=repo)
    before = load_current_domain_view()
    assert before is not None
    reflection = reflect_on_experience_episode(
        episode.episode_id, repo=repo, run_id="run-ref"
    )
    after = load_current_domain_view()
    assert after is not None
    assert after.content_fingerprint == before.content_fingerprint
    assert after.promoted_lesson_count == 0
    assert reflection_has_no_learning_receipt(reflection)
    assert LearningReceiptEnum.EXPERIENCE_LEARNED.value not in reflection.reflection_summary
    assert LearningReceiptEnum.EXPERIENCE_APPLIED.value not in reflection.reflection_summary


def test_candidate_extraction_requires_reflection(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed(repo, "run-ref")
    episode = close_experience_episode("run-ref", repo=repo)
    with pytest.raises(MelError, match="requires ExperienceReflection"):
        propose_candidates_from_episode(episode)
    reflection = reflect_on_experience_episode(
        episode.episode_id, repo=repo, run_id="run-ref"
    )
    candidates = propose_candidates_from_episode(episode, reflection=reflection)
    assert candidates
    assert all(item.source_reflection_id == reflection.reflection_id for item in candidates)
    assert reflection.possible_improvements
    assert all(
        "no authority" in item.statement.lower() for item in reflection.possible_improvements
    )


def test_dataset_a_like_reflection_does_not_force_a_lesson(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed(repo, "dataset-a-episode")
    episode = close_experience_episode("dataset-a-episode", repo=repo)
    reflection = reflect_on_experience_episode(
        episode.episode_id, repo=repo, run_id="dataset-a-episode"
    )
    candidates = propose_candidates_from_episode(episode, reflection=reflection)
    evaluations = [
        evaluate_candidate(candidate, episodes=[episode]) for candidate in candidates
    ]
    assert reflection.operational_authority is False
    assert EvaluationDecision.PROMOTE not in {item.decision for item in evaluations}
    view = load_current_domain_view()
    assert view is not None
    assert view.promoted_lesson_count == 0
    assert view.domain_view_version == "1.0.0"


def test_org_facts_stay_scoped_and_model_ready_is_unchanged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed(repo, "run-org")
    episode = close_experience_episode("run-org", repo=repo)
    reflection = build_experience_reflection(episode)
    org_items = [
        item for item in reflection.observed if item.item_id == "observed-org-scoped"
    ]
    assert org_items
    assert "music-center" not in org_items[0].statement
    assert all(
        "music-center" not in item.statement for item in reflection.possible_improvements
    )
    assert any("MODEL_READY" in item.statement for item in reflection.allowed)
    assert episode.terminal_outcome.value == "MODEL_READY"
