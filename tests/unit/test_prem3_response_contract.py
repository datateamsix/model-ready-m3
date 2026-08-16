"""Unit tests for the PreM3 structured response contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.meridian_eda_contracts import MeridianEDAFinding
from app.domain.intelligence.builder import load_current_domain_view
from app.intelligence.contracts import DecisionClass, KnowledgeClass, ResponsibleActor
from app.intelligence.orchestrator import run_pre_eda_diagnostics, run_scope_scenarios
from app.response.builder import ResponseBuilder
from app.response.contracts import (
    DisclosureLevel,
    DisclosurePlan,
    EvidenceRef,
    ModelReadyGateEvidence,
    PresentationStatus,
    ResponseAction,
    ResponseFinding,
    ResponseIntent,
    ResponseMetric,
    ResponseOrigin,
    ResponseType,
    SemanticQuestionCard,
    StructuredResponse,
)
from app.response.render import render_markdown
from app.response.routing import select_response_type
from app.response.validate import ResponseContractError
from tests.unit.intelligence_support import dataset_a_snapshot

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "tests" / "fixtures" / "response"
DOMAIN_VIEW_FINGERPRINT = (
    "b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf"
)


def _bundle():
    return run_pre_eda_diagnostics(dataset_a_snapshot())


def _gate(**overrides: object) -> ModelReadyGateEvidence:
    payload = {
        "gate_status": "MODEL_READY",
        "bigquery_verified": True,
        "content_fingerprint_matched": True,
        "official_meridian_eda_complete": True,
        "official_error_count": 0,
        "handoff_persisted": True,
    }
    payload.update(overrides)
    return ModelReadyGateEvidence(**payload)


def test_style_guide_is_canonical_and_routed() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs/context/RESPONSE_STYLE_GUIDE.md").read_text(encoding="utf-8")
    assert "docs/context/RESPONSE_STYLE_GUIDE.md" in agents
    assert "typed contract in `app/response/`" in agents
    assert "RESPONSE_STYLE_GUIDE prose" in agents
    assert "Lead with the conclusion" in guide
    assert (ROOT / "docs/architecture/prem3_agent_output_qa_framework.png").exists()


def test_response_type_routing_uses_explicit_intent() -> None:
    assert (
        select_response_type(ResponseIntent(kind="parameter_pressure"))
        is ResponseType.DEFINITION
    )
    assert (
        select_response_type(ResponseIntent(kind="enough_data", has_run_context=True))
        is ResponseType.MODELING_FEASIBILITY
    )
    assert (
        select_response_type(ResponseIntent(kind="what_to_fix", has_run_context=True))
        is ResponseType.GUIDED_REMEDIATION
    )
    assert select_response_type(ResponseIntent(kind="what_learned")) is ResponseType.LEARNING
    assert (
        select_response_type(ResponseIntent(kind="model_ready", audience="judge"))
        is ResponseType.JUDGE_DEMO
    )
    assert (
        select_response_type(ResponseIntent(kind="model_ready", audience="user"))
        is ResponseType.PRODUCT_INTELLIGENCE
    )


def test_dataset_a_assessment_numbers_are_grounded() -> None:
    bundle = _bundle()
    response = ResponseBuilder().assessment(bundle)
    rows = next(item for item in response.metrics if item.metric_id == "rows")
    assert rows.value == 524
    evidence = {item.evidence_id: item for item in response.proof.receipts}
    assert evidence["rows"].value == 524
    assert evidence["rows"].path == "snapshot_meta.row_count"
    markdown = render_markdown(response)
    assert "524" in markdown
    assert str(rows.value) in markdown


def test_parameter_pressure_authority_is_not_official_meridian() -> None:
    response = ResponseBuilder().parameter_advisory(_bundle())
    finding = next(
        item for item in response.findings if item.finding_id == "PREM3-PREEDA-PARAMETER-BUDGET"
    )
    assert finding.knowledge_class is KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
    assert any(
        item.knowledge_class is KnowledgeClass.MMM_EVIDENCE_HEURISTIC
        for item in response.authority
    )
    assert finding.disposition is PresentationStatus.REVIEW_RECOMMENDED
    assert finding.decision_class is DecisionClass.ADVISORY
    markdown = render_markdown(response)
    assert "official Meridian failure" in markdown.lower() or "heuristic" in markdown.lower()
    assert "ERROR" not in markdown.split("Status")[0]


def test_model_ready_requires_gate_evidence() -> None:
    with pytest.raises((ResponseContractError, ValidationError)):
        StructuredResponse(
            response_type=ResponseType.MODEL_READY,
            title="MODEL_READY",
            summary="The pre-modeling contract has been verified.",
            status=PresentationStatus.READY,
        )
    with pytest.raises((ResponseContractError, ValidationError)):
        ResponseBuilder().model_ready(_gate(gate_status="NOT_READY"))
    ready = ResponseBuilder().model_ready(_gate())
    assert ready.response_type is ResponseType.MODEL_READY
    assert ready.gate_evidence is not None
    assert ready.gate_evidence.official_error_count == 0


def test_official_meridian_stays_separate_from_prem3_interpretation() -> None:
    official = MeridianEDAFinding(
        finding_id="EDA-1",
        check_type="MULTICOLLINEARITY",
        report_category="variable_relationships",
        severity="ATTENTION",
        finding_cause="MULTICOLLINEARITY",
        explanation="VIF exceeds the official attention threshold.",
    )
    response = ResponseBuilder().official_meridian_eda(
        [official.model_dump(mode="json")],
        interpretations={
            "EDA-1": {
                "why_it_matters": "High collinearity can make channel effects hard to separate.",
                "guidance": "Keep the official severity. Do not rewrite it as a PreM3 ERROR.",
            }
        },
    )
    markdown = render_markdown(response)
    assert "### Official Meridian finding" in markdown
    assert "### PreM3 interpretation" in markdown
    assert response.official_meridian[0].severity == "ATTENTION"
    assert response.official_meridian[0].finding_text != (
        response.official_meridian[0].prem3_why_it_matters
    )


def test_semantic_question_requires_trigger_evidence() -> None:
    with pytest.raises((ResponseContractError, ValidationError)):
        StructuredResponse(
            response_type=ResponseType.SEMANTIC_QUESTION,
            title="One business-context question",
            summary="Were promotions scheduled independently of media?",
            status=PresentationStatus.MODELER_REVIEW_REQUIRED,
            questions=[
                SemanticQuestionCard(
                    question_id="SEM-MISSING",
                    question="Were promotions scheduled independently of media?",
                    why_asking="Timing may matter.",
                    triggered_by="overlap",
                    trigger_evidence=[],
                    what_changes="Causal role remains open.",
                    owner=ResponsibleActor.MODELER,
                    decision_authority=DecisionClass.MODELER_REVIEW_REQUIRED,
                    affected_scope=["promo"],
                )
            ],
        )
    card = ResponseBuilder().semantic_question(_bundle()).questions[0]
    assert card.trigger_evidence
    assert card.owner
    assert card.decision_authority
    assert card.affected_scope


def test_external_action_requires_owner() -> None:
    with pytest.raises(ValidationError):
        ResponseAction(
            action_id="missing-owner",
            action="Export another 52 weeks.",
            reason="History is limited.",
            decision_class=DecisionClass.USER_REQUIRED,
            can_prem3_execute=False,
        )
    action = ResponseAction(
        action_id="prem3-run",
        action="Re-run PreM3.",
        owner=ResponsibleActor.PREM3,
        reason="Diagnostics can be recomputed.",
        decision_class=DecisionClass.AUTO_SAFE,
        can_prem3_execute=True,
    )
    assert action.owner is ResponsibleActor.PREM3


def test_blocked_response_keeps_stack_trace_in_technical_details() -> None:
    response = ResponseBuilder().blocked(
        reason="Verified BigQuery model input was not available.",
        next_action="Reconnect the published table and re-run PreM3.",
        owner=ResponsibleActor.DATA_ENGINEER,
        retry_condition="A verified model-consumption endpoint exists.",
        raw_error='Traceback (most recent call last):\n  File "gate.py", line 1',
    )
    markdown = render_markdown(response)
    assert "What failed" in markdown
    assert "Reconnect the published table" in markdown
    assert "DATA_ENGINEER" in markdown
    assert "verified model-consumption endpoint exists" in markdown.lower()
    assert "Traceback" not in markdown
    assert response.technical_details.raw_error is not None
    assert "Traceback" in response.technical_details.raw_error


def test_learning_response_does_not_invent_lessons() -> None:
    view = load_current_domain_view()
    assert view is not None
    assert view.domain_view_version == "1.0.0"
    assert view.content_fingerprint == DOMAIN_VIEW_FINGERPRINT
    assert view.promoted_lesson_count == 0
    response = ResponseBuilder().from_intent(ResponseIntent(kind="what_learned"))
    markdown = render_markdown(response)
    assert "no promoted experiential lessons" in markdown.lower()
    assert "EXPERIENCE_LEARNED" not in markdown
    assert "EXPERIENCE_APPLIED" not in markdown


def test_causal_restraint_on_promotion_question() -> None:
    response = ResponseBuilder().semantic_interview(_bundle())
    markdown = render_markdown(response)
    assert "creates a causal question" in markdown.lower() or "causal question" in markdown.lower()
    assert "promotion is a confounder" not in markdown.lower()


def test_progressive_disclosure_hides_technical_proof() -> None:
    response = ResponseBuilder().assessment(_bundle())
    primary = render_markdown(response, level=DisclosureLevel.SUMMARY)
    assert "input_fingerprint" not in primary
    assert "PREM3-PB-001" not in primary
    assert "intelligence/pre_eda_diagnostic_receipt.json" not in primary
    proof = render_markdown(response, level=DisclosureLevel.PROOF)
    assert "Technical details" in proof
    assert "PREM3-PB-001" in proof


def test_top_findings_limit_retains_all_evidence() -> None:
    evidence = EvidenceRef(
        evidence_id="base",
        origin=ResponseOrigin.RUN_EVIDENCE,
        path="fixture",
        label="fixture",
        value=12,
    )
    findings = []
    for index in range(12):
        findings.append(
            ResponseFinding(
                finding_id=f"F-{index:02d}",
                title=f"Finding {index}",
                observed_fact=f"Observed fact {index}.",
                evidence=[evidence],
                interpretation=f"Interpretation {index}.",
                why_it_matters="Material enough to retain.",
                knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
                decision_class=DecisionClass.ADVISORY,
                knowledge_authority_label="PreM3 deterministic diagnostic",
                decision_authority_label="Advisory",
                disposition=PresentationStatus.REVIEW_RECOMMENDED,
                origin=ResponseOrigin.RUN_EVIDENCE,
            )
        )
    response = StructuredResponse(
        response_type=ResponseType.ASSESSMENT,
        title="Many findings",
        summary="Twelve material findings exist; the summary shows a short list.",
        status=PresentationStatus.REVIEW_RECOMMENDED,
        findings=findings,
        metrics=[
            ResponseMetric(
                metric_id="count",
                label="Finding count",
                value=12,
                evidence_id="base",
            )
        ],
        disclosure=DisclosurePlan(
            summary_finding_ids=[item.finding_id for item in findings[:5]],
            additional_finding_count=7,
            view_all_available=True,
        ),
    )
    assert len(response.disclosure.summary_finding_ids) == 5
    assert len(response.findings) == 12
    assert response.disclosure.view_all_available is True


def test_serialization_is_deterministic() -> None:
    bundle = _bundle()
    first = ResponseBuilder().assessment(bundle).model_dump(mode="json")
    second = ResponseBuilder().assessment(bundle).model_dump(mode="json")
    assert first == second
    assert [item["finding_id"] for item in first["findings"]] == [
        item["finding_id"] for item in second["findings"]
    ]


def test_dataset_a_presentation_suite() -> None:
    bundle = _bundle()
    builder = ResponseBuilder()
    assessment = builder.assessment(bundle)
    advisory = builder.parameter_advisory(bundle)
    interview = builder.semantic_interview(bundle)
    feasibility = builder.modeling_feasibility(bundle)
    scenario_payload = run_scope_scenarios(dataset_a_snapshot(), diagnostics=bundle)
    scenarios = builder.scope_scenario(scenario_payload)
    assert assessment.status in {
        PresentationStatus.READY,
        PresentationStatus.REVIEW_RECOMMENDED,
    }
    assert next(item.value for item in assessment.metrics if item.metric_id == "geos") == 4
    assert next(item.value for item in assessment.metrics if item.metric_id == "times") == 131
    assert "3.74" in str(advisory.metrics[0].value) or advisory.metrics[0].value == (
        bundle["receipt"]["diagnostics"]["parameter_budget"]["lenient"]["ratio"]
    )
    assert len(interview.questions) == 4
    assert "PENDING" in feasibility.summary
    assert scenarios.scenarios
    assert scenarios.scenarios[0].read_only is True
    assert scenarios.scenarios[0].production_data_changed is False
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    payloads = {
        "dataset_a_assessment.json": assessment,
        "dataset_a_parameter_advisory.json": advisory,
        "dataset_a_semantic_interview.json": interview,
        "dataset_a_feasibility.json": feasibility,
        "dataset_a_scope_scenario.json": scenarios,
        "learning.json": builder.from_intent(ResponseIntent(kind="what_learned")),
        "domain_view.json": builder.from_intent(ResponseIntent(kind="domain_view")),
        "judge_model_ready.json": builder.from_intent(
            ResponseIntent(kind="model_ready", audience="judge")
        ),
        "official_meridian.json": builder.official_meridian_eda(
            [
                {
                    "finding_id": "EDA-1",
                    "check_type": "MULTICOLLINEARITY",
                    "severity": "ATTENTION",
                    "finding_cause": "MULTICOLLINEARITY",
                    "explanation": "Official collinearity attention.",
                }
            ],
            interpretations={
                "EDA-1": {"why_it_matters": "Channel effects may be hard to separate."}
            },
        ),
        "model_ready.json": builder.model_ready(_gate()),
        "blocked.json": builder.blocked(
            reason="Source export is incomplete.",
            next_action="Export the missing weeks.",
            owner=ResponsibleActor.DATA_ENGINEER,
            retry_condition="Re-run PreM3 after the exports are added.",
        ),
        "guided_remediation.json": builder.guided_remediation(bundle),
    }
    for name, response in payloads.items():
        dumped = response.model_dump(mode="json")
        path = GOLDEN_DIR / name
        if path.exists():
            expected = json.loads(path.read_text(encoding="utf-8"))
            assert dumped == expected
        else:
            path.write_text(json.dumps(dumped, indent=2) + "\n", encoding="utf-8")
