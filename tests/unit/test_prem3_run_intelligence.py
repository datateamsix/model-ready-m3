"""Unit tests for PreM3 parameter budget, history, and MODEL_READY boundary."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.meridian_eda_contracts import MeridianEDAFinding
from app.intelligence.analyzers import analyze_history_sufficiency
from app.intelligence.contracts import Prem3PreEdaFinding
from app.intelligence.fingerprint import content_fingerprint_payload
from app.intelligence.orchestrator import run_pre_eda_diagnostics
from app.intelligence.parameter import _ratio, compute_parameter_budget
from app.intelligence.source import FixtureAdapter, fingerprint_frame, load_verified_snapshot
from tests.unit.intelligence_support import dataset_a_snapshot, snapshot_from_frame, weekly_frame


def test_lenient_strict_shadow_formulas_national() -> None:
    frame, contract = weekly_frame(geos=["US"], periods=52, treatments=2, controls=1)
    snap = snapshot_from_frame("nat", frame, contract, modeler_n_knots=12)
    result = compute_parameter_budget(snap)
    assert result["n_geos"] == 1
    assert result["n_times"] == 52
    assert result["n_knots"] == 12
    assert result["n_knots_source"] == "MODELER_PROVIDED"
    assert result["n_treatments"] == 3
    assert result["n_controls"] == 1
    assert result["lenient"]["n_parameters"] == 12 + 1 + 3
    assert result["strict"]["n_parameters"] == (3 * 1) + (1 * 1) + 12
    assert result["shadow"]["factor"] == 3.0
    assert result["shadow"]["label"] == "PREM3_SHADOW_COMPLEXITY_DIAGNOSTIC"
    assert result["lenient"]["official_meridian_parameter_count"] is False
    assert result["interpretation"]["knowledge_class"] == "MMM_EVIDENCE_HEURISTIC"
    assert result["interpretation"]["blocks_model_ready"] is False


def test_geo_parameter_budget_and_zero_denominator() -> None:
    frame, contract = weekly_frame(geos=["CA", "TX"], periods=10, treatments=1, controls=0)
    snap = snapshot_from_frame("geo", frame, contract, modeler_n_knots=4)
    result = compute_parameter_budget(snap)
    assert result["n_data_points"] == 20
    assert result["lenient"]["ratio"] == round(20 / result["lenient"]["n_parameters"], 6)
    assert _ratio(10, 0) is None


def test_dataset_a_parameter_budget_is_computed_not_hardcoded() -> None:
    snap = dataset_a_snapshot()
    result = compute_parameter_budget(snap)
    assert result["n_geos"] == 4
    assert result["n_times"] == 131
    assert result["n_data_points"] == 524
    assert result["n_treatments"] == 4
    assert result["n_controls"] == 3
    assert result["n_knots_source"] == "PRE_EDA_DIAGNOSTIC_ASSUMPTION"
    expected_lenient = (4 - 1) + result["n_knots"] + 3 + 4
    assert result["lenient"]["n_parameters"] == expected_lenient
    assert result["lenient"]["ratio"] == round(524 / expected_lenient, 6)
    assert result["interpretation"]["review_recommended"] is True
    assert result["interpretation"]["blocks_model_ready"] is False
    assert result["finding"]["finding_origin"] == "PREM3_PRE_EDA"


def test_knot_provenance_eda_only_not_final_modelspec() -> None:
    frame, contract = weekly_frame(geos=["CA", "TX"], periods=8, treatments=1, controls=1)
    eda = {
        "model_spec": {
            "knots": 7,
            "source": "EDA_ONLY_OFFICIAL_GEO_TIME_CONTROL_INVARIANT",
            "approved_for_final_modeling": False,
        }
    }
    snap = snapshot_from_frame("knots", frame, contract, eda_receipt=eda)
    result = compute_parameter_budget(snap)
    assert result["n_knots"] == 7
    assert result["n_knots_source"] == "EDA_ONLY_COMPATIBILITY"
    assert result["approved_for_final_modeling"] is False


def test_history_geo_weekly_is_advisory() -> None:
    frame, contract = weekly_frame(geos=["CA", "TX"], periods=40, treatments=1, controls=0)
    snap = snapshot_from_frame("hist", frame, contract)
    result = analyze_history_sufficiency(snap)
    assert result["observed_fact"]["n_periods"] == 40
    assert result["guidance"]["blocks_model_ready"] is False
    assert result["disposition"] == "REVIEW_RECOMMENDED"


def test_history_national_preferred_range() -> None:
    frame, contract = weekly_frame(geos=["US"], periods=160, treatments=1, controls=0)
    snap = snapshot_from_frame("hist-n", frame, contract)
    result = analyze_history_sufficiency(snap)
    assert result["observed_fact"]["national"] is True
    assert result["disposition"] == "PASS"


def test_prem3_finding_cannot_be_official_meridian_finding() -> None:
    finding = Prem3PreEdaFinding(
        finding_id="x",
        dimension="PARAMETER_PRESSURE",
        disposition="REVIEW_RECOMMENDED",
        knowledge_class="MMM_EVIDENCE_HEURISTIC",
        decision_class="ADVISORY",
        title="t",
        what_was_calculated="c",
        why_it_matters="w",
        best_practice="b",
        recommended_action="a",
        responsible_actor="MODELER",
    )
    payload = finding.model_dump()
    with pytest.raises(ValidationError):
        MeridianEDAFinding.model_validate(payload)
    with pytest.raises(ValidationError):
        Prem3PreEdaFinding.model_validate({**payload, "finding_origin": "OFFICIAL_MERIDIAN_EDA"})


def test_content_fingerprint_ignores_timestamps() -> None:
    payload = {"ratio": 3.7, "generated_at": "2026-01-01T00:00:00Z", "calculated_at": "t1"}
    other = {"ratio": 3.7, "generated_at": "2026-08-16T00:00:00Z", "calculated_at": "t2"}
    assert content_fingerprint_payload(payload) == content_fingerprint_payload(other)


def test_high_parameter_pressure_does_not_block_model_ready() -> None:
    snap = dataset_a_snapshot()
    budget = compute_parameter_budget(snap)
    assert budget["interpretation"]["review_recommended"] is True
    assert budget["interpretation"]["blocks_model_ready"] is False


def test_dataset_a_orchestrator_local_proof() -> None:
    snap = dataset_a_snapshot()
    bundle = run_pre_eda_diagnostics(snap)
    receipt = bundle["receipt"]
    assert receipt["finding_origin"] == "PREM3_PRE_EDA"
    assert receipt["official_meridian_findings_included"] is False
    assert receipt["domain_view_version"] == "1.0.0"
    assert receipt["domain_view_fingerprint"].startswith("b3ad518e")
    assert receipt["diagnostics"]["parameter_budget"]["n_geos"] == 4
    assert receipt["diagnostics"]["parameter_budget"]["n_times"] == 131
    assert bundle["semantic_interview"]["generic_questionnaire"] is False
    assert bundle["modeling_feasibility"]["score"] is None
    assert bundle["modeling_feasibility"]["model_ready_is_distinct"] is True
    assert "ASSESS" in bundle["report_markdown"]
    assert (
        "WHAT I FOUND" in bundle["report_markdown"]
        or "parameter" in bundle["report_markdown"].lower()
    )
    first = content_fingerprint_payload(receipt)
    second = content_fingerprint_payload(run_pre_eda_diagnostics(snap)["receipt"])
    assert first == second


def test_fixture_fingerprint_mismatch_fails_closed() -> None:
    frame, contract = weekly_frame(geos=["CA"], periods=4, treatments=1, controls=0)
    fp = fingerprint_frame(frame, contract)
    adapter = FixtureAdapter(
        run_id="bad",
        frame=frame,
        contract=contract,
        expected_fingerprint="deadbeef",
        schema_fingerprint=fp,
    )
    with pytest.raises(Exception, match="fingerprint mismatch"):
        load_verified_snapshot("bad", adapter=adapter)
