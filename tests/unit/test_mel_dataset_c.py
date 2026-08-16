"""Dataset C is a sealed evaluation holdout, not MEL training evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.contracts import DurableRunState
from app.core.run_repository import LocalFilesystemRunRepository
from app.core.state import RunStage
from app.domain.intelligence.builder import load_current_domain_view
from app.domain.intelligence.models import ClaimScope, LearnedAuthority, ScopeLevel
from app.intelligence.orchestrator import run_pre_eda_diagnostics
from app.mel.candidates import (
    propose_candidates_from_episode,
    propose_cross_episode_candidates,
)
from app.mel.episode import close_experience_episode
from app.mel.evaluate import evaluate_candidate
from app.mel.holdout_compare import compare_holdout_runs
from app.mel.models import (
    CandidateLesson,
    DatasetRole,
    EvaluationDecision,
    LessonType,
    MelError,
    ReflectionRole,
)
from app.mel.orchestrator import evaluate_experience_episode
from app.mel.reflect import reflect_on_experience_episode
from app.response.builder import ResponseBuilder
from app.synthetic.paths import DATASET_C_DIR
from app.tools.artifacts import write_json_artifact
from tests.unit.intelligence_support import dataset_c_snapshot

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = DATASET_C_DIR / "learning" / "holdout_manifest.json"
GENERATION = DATASET_C_DIR / "generation_manifest.json"
DOMAIN_VIEW_FINGERPRINT = (
    "b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf"
)
DATASET_C_PACKAGE_FP = "8b5eed78f0059bff4608f1822490f72b25cfe22c2210287bdd5fee80c26bbae4"


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


def _routing_candidate(episode_id: str) -> CandidateLesson:
    return CandidateLesson(
        candidate_lesson_id="cand-test-holdout",
        source_episode_ids=[episode_id],
        lesson_type=LessonType.SEMANTIC_QUESTION_ROUTING,
        statement="When retargeting is present, ask the remarketing question first.",
        problem_pattern="retargeting selection",
        applicability_conditions=["paid_social_retargeting present"],
        scope=ClaimScope(level=ScopeLevel.GLOBAL, value=None),
        requested_authority=LearnedAuthority.ROUTING_HINT,
        expected_behavior_change="Prioritize REMARKETING_TARGETING questions.",
        supporting_evidence_refs=["reflection"],
    )


def test_dataset_c_holdout_is_sealed_without_lessons() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    generation = json.loads(GENERATION.read_text(encoding="utf-8"))
    view = load_current_domain_view()
    assert view is not None
    assert view.promoted_lesson_count == 0
    assert view.content_fingerprint == DOMAIN_VIEW_FINGERPRINT
    assert payload["sealed_before_candidate_extraction"] is True
    assert payload["lesson_ids_visible_at_seal"] == []
    assert payload["classification"] == "synthetic"
    assert payload["dataset_identity"] == "dataset_c_summit_and_pine"
    assert payload["holdout_role"] == DatasetRole.SEALED_HOLDOUT.value
    assert payload["input_package_fingerprint"] == DATASET_C_PACKAGE_FP
    assert generation["business"] == "Summit & Pine"
    assert "Google Ads" in generation["providers"]
    assert "Pinterest Ads" in generation["providers"]
    assert generation["dataset_role"] == DatasetRole.SEALED_HOLDOUT.value
    assert "generate_dataset_c" not in (
        ROOT / "scripts" / "generate_dataset_b.py"
    ).read_text(encoding="utf-8")


def test_dataset_c_episode_is_evaluation_only_and_rejected_from_training(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    _seed_run(
        repo,
        "dataset-c-holdout",
        organization_id="summit-and-pine",
        package_uri="gs://raw/summit-and-pine/packages/dataset-c-v1/",
    )
    episode = close_experience_episode(
        "dataset-c-holdout",
        repo=repo,
        holdout=True,
        dataset_role=DatasetRole.SEALED_HOLDOUT,
    )
    assert episode.dataset_role is DatasetRole.SEALED_HOLDOUT
    assert episode.holdout is True
    assert episode.learning_eligible is False
    reflection = reflect_on_experience_episode(
        episode.episode_id, repo=repo, run_id="dataset-c-holdout"
    )
    assert reflection.reflection_role is ReflectionRole.EVALUATION_ONLY
    assert reflection.operational_authority is False
    with pytest.raises(MelError, match="REJECTED_HOLDOUT_INPUT"):
        propose_candidates_from_episode(episode, reflection=reflection)
    evaluation = evaluate_candidate(_routing_candidate(episode.episode_id), episodes=[episode])
    assert evaluation.decision is EvaluationDecision.REJECT
    assert evaluation.reason == "REJECTED_HOLDOUT_INPUT"
    with pytest.raises(MelError, match="REJECTED_HOLDOUT_INPUT"):
        evaluate_experience_episode(
            episode.episode_id,
            repo=repo,
            run_id="dataset-c-holdout",
            ledger_dir=tmp_path / "ledger",
            registry_dir=tmp_path / "registry",
        )
    after = load_current_domain_view()
    assert after is not None
    assert after.content_fingerprint == DOMAIN_VIEW_FINGERPRINT
    assert after.promoted_lesson_count == 0


def test_dataset_c_cannot_join_a_plus_b_evidence(tmp_path: Path) -> None:
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
    _seed_run(
        repo,
        "dataset-c-holdout",
        organization_id="summit-and-pine",
        package_uri="gs://raw/summit-and-pine/packages/dataset-c-v1/",
    )
    episode_a = close_experience_episode("dataset-a-episode", repo=repo)
    episode_b = close_experience_episode("dataset-b-stride-field", repo=repo)
    episode_c = close_experience_episode(
        "dataset-c-holdout", repo=repo, holdout=True
    )
    reflection_a = reflect_on_experience_episode(
        episode_a.episode_id, repo=repo, run_id="dataset-a-episode"
    )
    reflection_b = reflect_on_experience_episode(
        episode_b.episode_id, repo=repo, run_id="dataset-b-stride-field"
    )
    reflection_c = reflect_on_experience_episode(
        episode_c.episode_id, repo=repo, run_id="dataset-c-holdout"
    )
    with pytest.raises(MelError, match="REJECTED_HOLDOUT_INPUT"):
        propose_cross_episode_candidates(
            [episode_a, episode_b, episode_c],
            [reflection_a, reflection_b, reflection_c],
        )
    mixed = evaluate_candidate(
        _routing_candidate(episode_a.episode_id),
        episodes=[episode_a, episode_b, episode_c],
    )
    assert mixed.decision is EvaluationDecision.REJECT
    assert mixed.reason == "REJECTED_HOLDOUT_INPUT"


def test_dataset_c_v1_baseline_does_not_claim_causal_roles_or_ready() -> None:
    baseline = json.loads(
        (DATASET_C_DIR / "baseline" / "domain_view_v1" / "baseline_result.json").read_text(
            encoding="utf-8"
        )
    )
    bundle = run_pre_eda_diagnostics(dataset_c_snapshot())
    interview = ResponseBuilder().semantic_interview(bundle)
    assessment = ResponseBuilder().assessment(bundle)
    assert baseline["causal_roles_assigned"] is False
    assert interview.questions
    assert "cannot establish causal roles" in interview.summary.lower()
    assert assessment.status.value in {
        "REVIEW_RECOMMENDED",
        "MODELER_REVIEW_REQUIRED",
        "USER_ACTION_REQUIRED",
        "READY",
    }
    assert baseline["model_ready_state"] != "MODEL_READY"
    assert baseline["official_eda_status"] == "NOT_RUN_IN_GENERATOR"


def test_future_v2_comparison_contract_does_not_certify_experience_applied() -> None:
    baseline = json.loads(
        (DATASET_C_DIR / "baseline" / "domain_view_v1" / "baseline_result.json").read_text(
            encoding="utf-8"
        )
    )
    later = {
        **baseline,
        "question_routing": ["REMARKETING_TARGETING"],
        "model_input_fingerprint": baseline["parameter"]["lenient_ratio"],
        "parameter_calculations": baseline["parameter"],
    }
    comparison = compare_holdout_runs(
        {
            "model_input_fingerprint": "same",
            "parameter_calculations": baseline["parameter"],
            "question_routing": [],
        },
        {
            "model_input_fingerprint": "same",
            "parameter_calculations": baseline["parameter"],
            "question_routing": ["REMARKETING_TARGETING"],
        },
    )
    assert comparison["invariants_ok"] is True
    assert "question_routing" in comparison["allowed_changes_observed"]
    assert comparison["experience_applied"] is False
    broken = compare_holdout_runs(
        {"model_ready_logic": "unchanged"},
        {"model_ready_logic": "advisory_lesson_blocked_ready"},
    )
    assert broken["invariants_ok"] is False
    assert "model_ready_logic" in broken["invariant_failures"]
    assert later["training_access"] == "DENIED"
