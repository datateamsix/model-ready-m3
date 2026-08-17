"""First-cycle A+B experiment: promote at most one lesson without Dataset C."""

from __future__ import annotations

from pathlib import Path

from app.core.run_repository import LocalFilesystemRunRepository
from app.domain.intelligence.builder import load_current_domain_view
from app.mel.assignment import run_intelligence_assignment
from app.mel.candidates import propose_cross_episode_candidates
from app.mel.experiment import (
    CANDIDATE_SELECTION_POLICY,
    evaluate_ab_candidates,
    promote_selected,
    routing_regression_for,
)
from app.mel.models import DatasetRole, EvaluationDecision, MelError
from app.mel.promote import REGISTRY_GS_ENV


def _repo(tmp_path: Path) -> LocalFilesystemRunRepository:
    return LocalFilesystemRunRepository(
        root=tmp_path, raw_bucket="raw", artifact_bucket="artifacts"
    )


def test_dataset_c_cannot_enter_candidate_generation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MODELREADY_DOMAIN_VIEW_REGISTRY_DIR", raising=False)
    monkeypatch.delenv(REGISTRY_GS_ENV, raising=False)
    repo = _repo(tmp_path)
    result_a = run_intelligence_assignment("A", repo=repo, run_id="exp-a")
    result_c = run_intelligence_assignment("C", repo=repo, run_id="exp-c")
    assert result_c["episode"].dataset_role is DatasetRole.SEALED_HOLDOUT
    try:
        propose_cross_episode_candidates(
            [result_a["episode"], result_c["episode"]],
            [result_a["reflection"]],
        )
        raise AssertionError("Dataset C must not enter candidate generation")
    except MelError as exc:
        assert "holdout" in str(exc).lower() or "HOLDOUT" in str(exc)


def test_ab_first_cycle_promotes_at_most_one_lesson(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MODELREADY_DOMAIN_VIEW_REGISTRY_DIR", raising=False)
    monkeypatch.delenv(REGISTRY_GS_ENV, raising=False)
    repo = _repo(tmp_path)
    result_c_v1 = run_intelligence_assignment("C", repo=repo, run_id="exp-c-v1")
    result_a = run_intelligence_assignment("A", repo=repo, run_id="exp-a")
    result_b = run_intelligence_assignment("B", repo=repo, run_id="exp-b")
    assert result_a["reflection"] is not None
    assert result_b["reflection"] is not None
    view = load_current_domain_view()
    assert view is not None
    assert view.promoted_lesson_count == 0
    ledger = tmp_path / "ledger"
    outcome = evaluate_ab_candidates(
        episode_a=result_a["episode"],
        reflection_a=result_a["reflection"],
        episode_b=result_b["episode"],
        reflection_b=result_b["reflection"],
        view=view,
        ledger_dir=ledger,
    )
    assert outcome["ranking_rule"] == CANDIDATE_SELECTION_POLICY["ranking"]
    assert all(
        "dataset_c" not in str(item.get("supporting_episode_ids"))
        for item in outcome["candidates"]
    )
    selected = outcome["selected"]
    if selected is None:
        assert outcome["eligible_count"] == 0
        after = load_current_domain_view()
        assert after is not None
        assert after.promoted_lesson_count == 0
        return
    candidate = selected["candidate"]
    evaluation = selected["evaluation"]
    assert evaluation.decision is EvaluationDecision.PROMOTE
    assert (candidate.independent_context_count or 0) >= 2
    assert candidate.expected_behavior_effect
    regression = routing_regression_for(candidate, view)
    assert regression.passed
    registry = tmp_path / "registry"
    promoted = promote_selected(
        candidate=candidate,
        evaluation=evaluation,
        view=view,
        registry_dir=registry,
        ledger_dir=ledger,
        regression=regression,
    )
    assert promoted["claim_count_after"] == promoted["claim_count_before"] + 1
    assert promoted["new_fingerprint"] != promoted["old_fingerprint"]
    monkeypatch.setenv("MODELREADY_DOMAIN_VIEW_REGISTRY_DIR", str(registry))
    result_c_v2 = run_intelligence_assignment("C", repo=repo, run_id="exp-c-v2")
    assert result_c_v1["behavior"]["action_ids"][0] == "prem3-scenarios"
    assert result_c_v2["behavior"]["action_ids"][0] == "modeler-questions"
    assert result_c_v1["model_input_fingerprint"] == result_c_v2["model_input_fingerprint"]
