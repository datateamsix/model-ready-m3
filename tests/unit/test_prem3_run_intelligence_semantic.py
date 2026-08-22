"""Semantic, scenario, source-of-truth, and guidance tests."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from app.core.errors import SafetyViolationError, ValidationBlockedError
from app.core.model_intent import DATASET_A_MODEL_INTENT, MODEL_READY_COLUMNS
from app.core.state import RunStage
from app.domain.intelligence.builder import load_current_domain_view
from app.intelligence.orchestrator import run_pre_eda_diagnostics, run_scope_scenarios
from app.intelligence.recording import build_semantic_answer
from app.intelligence.reports import build_guided_remediation
from app.intelligence.scenarios import simulate_model_scope_scenarios
from app.intelligence.semantic import (
    detect_semantic_question_triggers,
    generate_semantic_readiness_interview,
)
from app.intelligence.source import load_verified_snapshot
from app.tools.fingerprints import content_fingerprint
from app.tools.meridian_contract import generate_meridian_input_contract
from app.tools.model_frame import coerce_model_frame_types
from tests.unit.intelligence_support import (
    DATASET_A_TRUTH,
    dataset_a_snapshot,
    snapshot_from_frame,
    weekly_frame,
)


def test_semantic_triggers_do_not_assign_causal_roles() -> None:
    frame, contract = weekly_frame(
        geos=["CA"],
        periods=20,
        treatments=1,
        controls=0,
        include_promo=True,
        include_price=True,
        gqv=True,
        remarketing=True,
    )
    snap = snapshot_from_frame("sem", frame, contract)
    triggers = detect_semantic_question_triggers(snap)
    families = {item["question_family"] for item in triggers}
    assert "PROMOTION_TIMING" in families
    assert "PRICE_DISCOUNT_TIMING" in families
    assert "ORGANIC_MEDIA_TIMING" in families
    assert "REMARKETING_TARGETING" in families
    assert all(item["causal_role_assigned"] is False for item in triggers)
    interview = generate_semantic_readiness_interview(snap, triggers=triggers)
    for question in interview["questions"]:
        assert question["trigger_evidence"]
        assert question["why_pre_m3_is_asking"]
        assert question["affected_variables"] or question["affected_channels"]
        assert question["possible_causal_issue"]
        assert question["required_human_role"]
        assert question["decision_class"]
        assert question["what_changes_based_on_answer"]


def test_no_generic_interview_without_triggers() -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=12, treatments=1, controls=0)
    contract.organic_media = []
    frame = frame.drop(columns=["organic_sessions"])
    snap = snapshot_from_frame("none", frame, contract)
    interview = generate_semantic_readiness_interview(snap, triggers=[])
    assert interview["question_count"] == 0
    assert interview["semantic_status"] == "CLEAR"
    assert interview["generic_questionnaire"] is False


def test_dataset_a_semantic_interview_is_run_specific() -> None:
    snap = dataset_a_snapshot()
    interview = generate_semantic_readiness_interview(snap)
    assert interview["generic_questionnaire"] is False
    families = {item["question_family"] for item in interview["questions"]}
    assert "PROMOTION_TIMING" in families
    assert "PRICE_DISCOUNT_TIMING" in families
    assert interview["causal_roles_assigned"] is False


def test_scope_scenarios_are_read_only_and_protect_confounders() -> None:
    frame, contract = weekly_frame(geos=["CA", "TX"], periods=20, treatments=2, controls=1)
    snap = snapshot_from_frame(
        "scn",
        frame,
        contract,
        confirmed_confounders=["control_0"],
        optional_predictors=[],
        modeler_n_knots=8,
    )
    baseline_fp = snap.endpoint.input_fingerprint
    result = simulate_model_scope_scenarios(
        snap,
        [
            {"scenario_type": "CANDIDATE_CHANNEL_CONSOLIDATION", "channels": ["ch0", "ch1"]},
            {"scenario_type": "MODELER_REVIEWED_TIME_COMPLEXITY", "n_knots": 4},
            {"scenario_type": "ADDITIONAL_HISTORY", "additional_periods": 52},
        ],
    )
    assert result["read_only"] is True
    assert result["mutated_production_input"] is False
    assert result["input_fingerprint_unchanged"] == baseline_fp
    assert all(item["drop_confounder"] is False for item in result["scenarios"])
    knots = next(
        item
        for item in result["scenarios"]
        if item["scenario_type"] == "MODELER_REVIEWED_TIME_COMPLEXITY"
    )
    assert knots["required_authority"] == "MODELER_REVIEW_REQUIRED"
    with pytest.raises(ValidationBlockedError, match="confirmed confounder"):
        simulate_model_scope_scenarios(
            snap,
            [
                {
                    "scenario_type": "OPTIONAL_NON_CONFOUNDING_VARIABLE_SCOPE",
                    "drop_controls": ["control_0"],
                }
            ],
        )


def test_guided_remediation_has_canonical_sections() -> None:
    snap = dataset_a_snapshot()
    bundle = run_pre_eda_diagnostics(snap)
    items = bundle["guided_remediation"] or build_guided_remediation(
        bundle["receipt"]["diagnostics"]
    )
    assert items
    required = {
        "what_i_found",
        "why_it_matters",
        "best_practice",
        "insight_from_your_data",
        "what_prem3_can_do",
        "what_you_should_do",
        "modeler_review",
        "next_step",
        "responsible_actor",
    }
    assert required <= set(items[0])


def test_domain_view_recorded_and_not_mutated() -> None:
    before = load_current_domain_view()
    assert before is not None
    fingerprint = before.content_fingerprint
    version = before.domain_view_version
    count = before.promoted_lesson_count
    snap = dataset_a_snapshot()
    bundle = run_pre_eda_diagnostics(snap)
    assert bundle["receipt"]["domain_view_version"] == version
    assert bundle["receipt"]["domain_view_fingerprint"] == fingerprint
    after = load_current_domain_view()
    assert after is not None
    assert after.content_fingerprint == fingerprint
    assert after.promoted_lesson_count == count == 0


def test_record_semantic_context_keeps_explicit_answer() -> None:
    answer = build_semantic_answer(
        run_id="r1",
        question_id="SEM-PROMOTION-r1",
        answer="Promotions were planned in a separate retail calendar.",
        actor_role="ANALYST",
    )
    assert answer.provenance == "EXPLICIT_HUMAN_ANSWER"
    assert answer.scope == "RUN"
    with pytest.raises(SafetyViolationError):
        build_semantic_answer(
            run_id="r1",
            question_id="q",
            answer="therefore it is a confounder",
            actor_role="ANALYST",
        )


def test_bigquery_source_fails_closed_without_receipt() -> None:
    class FakeRepo:
        def load_run(self, run_id: str):
            return SimpleNamespace(
                run_id=run_id, stage=RunStage.EXPLORING, model_consumption_view=None
            )

        def load_json(self, run_id: str, relative: str):
            return None

        def load_issues(self, run_id: str):
            return []

    with pytest.raises(ValidationBlockedError, match="missing BigQuery publish receipt"):
        load_verified_snapshot("run-x", repo=FakeRepo())


def test_bigquery_fingerprint_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=2, treatments=1, controls=0)
    contract.run_id = "run-y"

    class FakeRepo:
        def load_run(self, run_id: str):
            return SimpleNamespace(
                run_id=run_id,
                stage=RunStage.EXPLORING,
                model_consumption_view="view_x",
            )

        def load_json(self, run_id: str, relative: str):
            if relative == "publish_receipt.json":
                return {
                    "status": "PUBLISHED",
                    "parity_status": "PASS",
                    "project_id": "p",
                    "dataset_id": "d",
                    "table_id": "t",
                    "published_fingerprint": "expected",
                    "schema_fingerprint": "s",
                    "row_count": 2,
                    "consumption_view": "p.d.t",
                }
            if relative == "meridian_input_contract.json":
                return contract.model_dump(mode="json")
            return None

        def load_issues(self, run_id: str):
            return []

    monkeypatch.setattr(
        "app.intelligence.source._read_consumption_table",
        lambda client, table_ref, queried_at: frame,
    )

    class DummyClient:
        pass

    with pytest.raises(ValidationBlockedError, match="fingerprint mismatch"):
        load_verified_snapshot("run-y", repo=FakeRepo(), bq_client=DummyClient())


def test_bigquery_snapshot_matches_publish_parity_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = pd.read_csv(DATASET_A_TRUTH)
    published = coerce_model_frame_types(frame)
    expected_fp = content_fingerprint(
        published, columns=list(MODEL_READY_COLUMNS), key_columns=["time", "geo"]
    )
    contract = generate_meridian_input_contract(
        run_id="run-parity",
        intent=DATASET_A_MODEL_INTENT,
        frame=frame,
        project_id="p",
        dataset_id="d",
        table_id="t",
    )
    bq_like = frame.copy()
    bq_like["time"] = pd.to_datetime(bq_like["time"])
    bq_like["kpi_orders"] = bq_like["kpi_orders"].astype("float64")
    bq_like["population"] = bq_like["population"].astype("float64")

    class FakeRepo:
        def load_run(self, run_id: str):
            return SimpleNamespace(
                run_id=run_id,
                stage=RunStage.PUBLISHING,
                model_consumption_view=None,
            )

        def load_json(self, run_id: str, relative: str):
            if relative == "publish_receipt.json":
                return {
                    "status": "PUBLISHED",
                    "parity_status": "PASS",
                    "project_id": "p",
                    "dataset_id": "d",
                    "table_id": "t",
                    "published_fingerprint": expected_fp,
                    "schema_fingerprint": "s",
                    "row_count": int(len(frame)),
                }
            if relative == "meridian_input_contract.json":
                return contract.model_dump(mode="json")
            return None

        def load_issues(self, run_id: str):
            return []

    monkeypatch.setattr(
        "app.intelligence.source._read_consumption_table",
        lambda client, table_ref, queried_at: bq_like,
    )

    class DummyClient:
        pass

    snapshot = load_verified_snapshot("run-parity", repo=FakeRepo(), bq_client=DummyClient())
    assert snapshot.endpoint.input_fingerprint == expected_fp
    assert snapshot.endpoint.expected_fingerprint == expected_fp


def test_dataset_a_scope_scenario_proof() -> None:
    snap = dataset_a_snapshot()
    bundle = run_pre_eda_diagnostics(snap)
    result = run_scope_scenarios(
        snap,
        diagnostics=bundle,
        scenarios=[{"scenario_type": "ADDITIONAL_HISTORY", "additional_periods": 52}],
    )
    assert result["read_only"] is True
    assert result["mutated_production_input"] is False
    scenario = result["scenarios"][0]
    assert scenario["change"]["lenient_ratio"] is not None
    assert scenario["required_authority"] == "USER_REQUIRED"
