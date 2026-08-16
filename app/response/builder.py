"""Deterministic construction of structured PreM3 responses.

Consumes existing intelligence artifacts. Does not recalculate diagnostics,
override action authority, change MODEL_READY, or reinterpret official
Meridian severity.
"""

from __future__ import annotations

from typing import Any

from app.intelligence.contracts import DecisionClass, KnowledgeClass, ResponsibleActor
from app.mel.routing_apply import reorder_actions
from app.response.contracts import (
    KNOWLEDGE_AUTHORITY_LABELS,
    TOP_FINDINGS_MAX,
    TOP_FINDINGS_MIN,
    AuthorityPresentation,
    DisclosurePlan,
    EvidenceRef,
    FeasibilityRow,
    ModelReadyGateEvidence,
    OfficialMeridianView,
    PresentationStatus,
    ProductBehavior,
    ProofBundle,
    ResponseAction,
    ResponseFinding,
    ResponseInsight,
    ResponseIntent,
    ResponseMetric,
    ResponseOrigin,
    ResponseSection,
    ResponseType,
    ScenarioView,
    SectionType,
    SemanticQuestionCard,
    StructuredResponse,
    TechnicalDetails,
)
from app.response.product import (
    build_definition_response,
    build_domain_view_response,
    build_judge_response,
    build_learning_response,
    build_product_response,
)
from app.response.qa import attach_qa_hooks
from app.response.routing import select_response_type
from app.response.validate import ResponseContractError

DISPOSITION_STATUS = {
    "PASS": PresentationStatus.PASS,
    "READY": PresentationStatus.READY,
    "REVIEW_RECOMMENDED": PresentationStatus.REVIEW_RECOMMENDED,
    "USER_CONTEXT_REQUIRED": PresentationStatus.USER_ACTION_REQUIRED,
    "USER_ACTION_REQUIRED": PresentationStatus.USER_ACTION_REQUIRED,
    "CONTRACT_FAILURE": PresentationStatus.BLOCKED,
    "NOT_APPLICABLE": PresentationStatus.NOT_APPLICABLE,
    "MODELER_REVIEW_REQUIRED": PresentationStatus.MODELER_REVIEW_REQUIRED,
    "CLEAR": PresentationStatus.READY,
    "QUESTIONS_OPEN": PresentationStatus.REVIEW_RECOMMENDED,
    "PENDING": PresentationStatus.PENDING,
    "COMPLETE": PresentationStatus.COMPLETE,
    "BLOCKED": PresentationStatus.BLOCKED,
}


class ResponseBuilder:
    """Build typed responses from structured intelligence."""

    def from_intent(
        self,
        intent: ResponseIntent,
        *,
        bundle: dict[str, Any] | None = None,
        scenarios: dict[str, Any] | None = None,
        gate: ModelReadyGateEvidence | None = None,
        official_findings: list[dict[str, Any]] | None = None,
        blocked: dict[str, Any] | None = None,
        topic: str | None = None,
    ) -> StructuredResponse:
        response_type = select_response_type(intent)
        if response_type is ResponseType.ASSESSMENT:
            return self.assessment(bundle or {})
        if response_type is ResponseType.ADVISORY:
            return self.parameter_advisory(bundle or {})
        if response_type is ResponseType.INSIGHT:
            return self.insight(bundle or {})
        if response_type is ResponseType.GUIDED_REMEDIATION:
            return self.guided_remediation(bundle or {})
        if response_type is ResponseType.SEMANTIC_INTERVIEW:
            return self.semantic_interview(bundle or {})
        if response_type is ResponseType.SEMANTIC_QUESTION:
            return self.semantic_question(bundle or {})
        if response_type is ResponseType.MODELING_FEASIBILITY:
            return self.modeling_feasibility(bundle or {})
        if response_type is ResponseType.SCOPE_SCENARIO:
            return self.scope_scenario(scenarios or bundle or {})
        if response_type is ResponseType.DATA_SUMMARY:
            return self.data_summary(bundle or {})
        if response_type is ResponseType.DATA_ACQUISITION:
            return self.data_acquisition(bundle or {})
        if response_type is ResponseType.OFFICIAL_MERIDIAN_EDA:
            return self.official_meridian_eda(official_findings or [])
        if response_type is ResponseType.MODEL_READY:
            if gate is None:
                raise ResponseContractError(
                    "MODEL_READY responses require deterministic gate evidence."
                )
            return self.model_ready(gate)
        if response_type is ResponseType.BLOCKED:
            return self.blocked(**(blocked or {}))
        if response_type is ResponseType.LEARNING:
            return build_learning_response()
        if response_type is ResponseType.DOMAIN_VIEW:
            return build_domain_view_response()
        if response_type is ResponseType.JUDGE_DEMO:
            return build_judge_response(topic or intent.kind)
        if response_type is ResponseType.DEFINITION:
            return build_definition_response(topic or intent.kind)
        if response_type is ResponseType.PRODUCT_INTELLIGENCE:
            return build_product_response(topic or intent.kind)
        raise ResponseContractError(f"Unsupported response type {response_type}.")

    def assessment(self, bundle: dict[str, Any]) -> StructuredResponse:
        ctx = _RunContext(bundle)
        blockers = ctx.structural_blocker_count()
        pressure = ctx.pressure_band()
        questions = ctx.question_count()
        pre_period = ctx.pre_period_status()
        status = (
            PresentationStatus.READY if blockers == 0 else PresentationStatus.BLOCKED
        )
        if blockers == 0 and (
            pressure != "LOW" or questions > 0 or pre_period == "UNKNOWN"
        ):
            status = PresentationStatus.REVIEW_RECOMMENDED
        summary = (
            f"Your verified model input passes structural readiness. "
            f"The main concern is {pressure.lower()} parameter pressure, and "
            f"{questions} causal/business questions remain for modeler review."
            if blockers == 0
            else "Structural blockers remain on the verified model input."
        )
        findings = [
            ctx.parameter_finding(),
            ctx.pre_period_finding(),
            ctx.semantic_gap_finding(),
        ]
        findings.extend(ctx.extra_diagnostic_findings())
        return _finish(
            response_type=ResponseType.ASSESSMENT,
            title="Your input passes structural readiness"
            if blockers == 0
            else "Structural readiness is blocked",
            summary=summary,
            status=status,
            metrics=ctx.coverage_metrics(),
            findings=findings,
            insights=[ctx.parameter_insight()],
            actions=ctx.assessment_actions(),
            authority=[ctx.heuristic_authority(), ctx.diagnostic_authority()],
            product_behaviors=[
                ProductBehavior.ASSESS,
                ProductBehavior.INSIGHT,
                ProductBehavior.ADVISE,
                ProductBehavior.GUIDE,
            ],
            technical_details=ctx.technical_details(),
            proof=ctx.proof(),
            consistency_group="run.assessment",
        )

    def parameter_advisory(self, bundle: dict[str, Any]) -> StructuredResponse:
        ctx = _RunContext(bundle)
        finding = ctx.parameter_finding()
        return _finish(
            response_type=ResponseType.ADVISORY,
            title="Review model scope before fitting",
            summary=(
                f"The current lenient diagnostic ratio is {ctx.lenient_ratio()} "
                "observations per parameter. This is a PreM3/MMM heuristic, not "
                "an official Meridian failure."
            ),
            status=PresentationStatus.REVIEW_RECOMMENDED,
            metrics=ctx.parameter_metrics(),
            findings=[finding],
            insights=[ctx.parameter_insight()],
            actions=ctx.parameter_actions(),
            authority=[ctx.diagnostic_authority(), ctx.heuristic_authority()],
            product_behaviors=[ProductBehavior.ADVISE, ProductBehavior.GUIDE],
            technical_details=ctx.technical_details(),
            proof=ctx.proof(),
            consistency_group="run.parameter_pressure",
        )

    def insight(self, bundle: dict[str, Any]) -> StructuredResponse:
        ctx = _RunContext(bundle)
        insight = ctx.parameter_insight()
        return _finish(
            response_type=ResponseType.INSIGHT,
            title="Parameter pressure is severe on this run",
            summary=insight.statement,
            status=PresentationStatus.REVIEW_RECOMMENDED,
            metrics=ctx.parameter_metrics(),
            findings=[ctx.parameter_finding()],
            insights=[insight],
            actions=ctx.parameter_actions(),
            authority=[ctx.heuristic_authority()],
            product_behaviors=[ProductBehavior.INSIGHT],
            technical_details=ctx.technical_details(),
            proof=ctx.proof(),
            consistency_group="run.parameter_pressure",
        )

    def guided_remediation(self, bundle: dict[str, Any]) -> StructuredResponse:
        ctx = _RunContext(bundle)
        items = ctx.guidance_items()
        if not items:
            raise ResponseContractError("No guided remediation items are available.")
        item = items[0]
        sections = _remediation_sections(item)
        owner = ResponsibleActor(item.get("responsible_actor") or "MODELER")
        action = ResponseAction(
            action_id="remediation-next",
            action=_imperative(item.get("next_step") or "Re-run PreM3."),
            owner=owner,
            reason=str(item.get("why_it_matters") or "Resolution is required."),
            knowledge_class=KnowledgeClass(
                item.get("knowledge_class") or KnowledgeClass.MMM_EVIDENCE_HEURISTIC
            ),
            decision_class=DecisionClass(
                item.get("decision_class") or DecisionClass.ADVISORY
            ),
            can_prem3_execute=owner is ResponsibleActor.PREM3,
            related_finding_ids=[str(item.get("finding_id") or "")],
        )
        return _finish(
            response_type=ResponseType.GUIDED_REMEDIATION,
            title="Severe parameter pressure",
            summary=str(item.get("why_it_matters") or item.get("what_i_found")),
            status=PresentationStatus.REVIEW_RECOMMENDED,
            sections=sections,
            findings=[ctx.parameter_finding()],
            actions=[
                ResponseAction(
                    action_id="prem3-can",
                    action=_imperative(item.get("what_prem3_can_do") or "Re-run diagnostics."),
                    owner=ResponsibleActor.PREM3,
                    reason="PreM3-owned diagnostic follow-up.",
                    decision_class=DecisionClass.AUTO_SAFE,
                    can_prem3_execute=True,
                ),
                action,
            ],
            authority=[ctx.heuristic_authority()],
            product_behaviors=[ProductBehavior.GUIDE, ProductBehavior.ADVISE],
            technical_details=ctx.technical_details(),
            proof=ctx.proof(),
            consistency_group="run.guided_remediation",
        )

    def semantic_interview(self, bundle: dict[str, Any]) -> StructuredResponse:
        ctx = _RunContext(bundle)
        cards = ctx.question_cards()
        count = len(cards)
        return _finish(
            response_type=ResponseType.SEMANTIC_INTERVIEW,
            title="Business-context answers are still needed",
            summary=(
                f"I need {count} business-context answers. "
                "These questions create a causal question for modeler review. "
                "The table cannot establish causal roles."
            ),
            status=PresentationStatus.MODELER_REVIEW_REQUIRED,
            metrics=ctx.coverage_metrics()[:3],
            questions=cards,
            actions=[
                ResponseAction(
                    action_id="answer-semantic",
                    action=(
                        "Answer the open semantic questions, then continue to "
                        "official Meridian EDA."
                    ),
                    owner=ResponsibleActor.MODELER,
                    reason="Causal roles cannot be assigned from the table.",
                    knowledge_class=KnowledgeClass.MMM_JUDGMENT,
                    decision_class=DecisionClass.MODELER_REVIEW_REQUIRED,
                    can_prem3_execute=False,
                )
            ],
            authority=[
                _authority(KnowledgeClass.MMM_JUDGMENT, DecisionClass.MODELER_REVIEW_REQUIRED)
            ],
            product_behaviors=[ProductBehavior.ASSESS, ProductBehavior.GUIDE],
            technical_details=ctx.technical_details(),
            proof=ctx.proof(),
            consistency_group="run.semantic_interview",
        )

    def semantic_question(self, bundle: dict[str, Any]) -> StructuredResponse:
        ctx = _RunContext(bundle)
        cards = ctx.question_cards()
        if not cards:
            raise ResponseContractError("No semantic question is available.")
        card = cards[0]
        return _finish(
            response_type=ResponseType.SEMANTIC_QUESTION,
            title="One business-context question",
            summary=card.question,
            status=PresentationStatus.MODELER_REVIEW_REQUIRED,
            questions=[card],
            actions=[
                ResponseAction(
                    action_id="answer-one",
                    action="Provide the business-context answer for this question.",
                    owner=card.owner,
                    reason=card.why_asking,
                    knowledge_class=KnowledgeClass.MMM_JUDGMENT,
                    decision_class=card.decision_authority,
                    can_prem3_execute=False,
                )
            ],
            product_behaviors=[ProductBehavior.GUIDE],
            technical_details=ctx.technical_details(),
            proof=ctx.proof(),
            consistency_group="run.semantic_question",
        )

    def modeling_feasibility(self, bundle: dict[str, Any]) -> StructuredResponse:
        ctx = _RunContext(bundle)
        rows = ctx.feasibility_rows()
        return _finish(
            response_type=ResponseType.MODELING_FEASIBILITY,
            title="Modeling feasibility",
            summary=(
                f"Feasibility is dimensional, not a score. Parameter pressure is "
                f"{ctx.pressure_band().lower()}, pre-period media is "
                f"{ctx.pre_period_status()}, and official Meridian EDA is "
                f"{ctx.official_eda_status()}."
            ),
            status=PresentationStatus.REVIEW_RECOMMENDED,
            metrics=ctx.coverage_metrics(),
            feasibility_rows=rows,
            findings=[ctx.parameter_finding(), ctx.semantic_gap_finding()],
            actions=ctx.assessment_actions(),
            authority=[ctx.heuristic_authority()],
            product_behaviors=[ProductBehavior.ASSESS, ProductBehavior.ADVISE],
            technical_details=ctx.technical_details(),
            proof=ctx.proof(),
            consistency_group="run.feasibility",
        )

    def scope_scenario(self, payload: dict[str, Any]) -> StructuredResponse:
        scenarios = _scenario_views(payload)
        if not scenarios:
            raise ResponseContractError("No scope scenarios are available.")
        first = scenarios[0]
        return _finish(
            response_type=ResponseType.SCOPE_SCENARIO,
            title=first.title,
            summary=(
                "These scenarios are read-only diagnostics. Production data is unchanged."
            ),
            status=PresentationStatus.REVIEW_RECOMMENDED,
            scenarios=scenarios,
            actions=[
                ResponseAction(
                    action_id="review-scenario",
                    action=(
                        "Review eligible scope changes with the modeler before "
                        "changing production input."
                    ),
                    owner=ResponsibleActor.MODELER,
                    reason=first.required_review,
                    knowledge_class=KnowledgeClass.MMM_JUDGMENT,
                    decision_class=DecisionClass.MODELER_REVIEW_REQUIRED,
                    can_prem3_execute=False,
                    requires_approval=True,
                )
            ],
            product_behaviors=[ProductBehavior.INSIGHT, ProductBehavior.GUIDE],
            technical_details=TechnicalDetails(
                fingerprints={"input_fingerprint": str(payload.get("input_fingerprint") or "")}
                if payload.get("input_fingerprint")
                else {},
                raw_enums={"read_only": "true"},
            ),
            proof=ProofBundle(
                fingerprints={
                    "input_fingerprint": str(payload.get("input_fingerprint") or "")
                }
                if payload.get("input_fingerprint")
                else {}
            ),
            consistency_group="run.scope_scenario",
        )

    def data_summary(self, bundle: dict[str, Any]) -> StructuredResponse:
        ctx = _RunContext(bundle)
        return _finish(
            response_type=ResponseType.DATA_SUMMARY,
            title="Data inventory",
            summary=(
                f"The verified input covers {ctx.row_count()} rows across "
                f"{ctx.n_geos()} geos and {ctx.n_times()} periods."
            ),
            status=PresentationStatus.READY,
            metrics=ctx.coverage_metrics(),
            findings=ctx.data_summary_findings(),
            product_behaviors=[ProductBehavior.ASSESS],
            technical_details=ctx.technical_details(),
            proof=ctx.proof(),
            consistency_group="run.data_summary",
        )

    def data_acquisition(self, bundle: dict[str, Any]) -> StructuredResponse:
        ctx = _RunContext(bundle)
        findings = ctx.acquisition_findings()
        actions = [
            ResponseAction(
                action_id="reexport",
                action="Export the missing source periods and re-run PreM3.",
                owner=ResponsibleActor.DATA_ENGINEER,
                reason="Source coverage is incomplete.",
                knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
                decision_class=DecisionClass.USER_REQUIRED,
                can_prem3_execute=False,
                retry_condition="Re-run PreM3 after the exports are added.",
            )
        ]
        return _finish(
            response_type=ResponseType.DATA_ACQUISITION,
            title="Additional source data is required",
            summary="PreM3 needs source exports before it can continue safely.",
            status=PresentationStatus.USER_ACTION_REQUIRED,
            findings=findings,
            actions=actions,
            product_behaviors=[ProductBehavior.GUIDE],
            technical_details=ctx.technical_details(),
            proof=ctx.proof(),
            consistency_group="run.data_acquisition",
        )

    def official_meridian_eda(
        self,
        findings: list[dict[str, Any]],
        *,
        interpretations: dict[str, dict[str, str]] | None = None,
    ) -> StructuredResponse:
        views: list[OfficialMeridianView] = []
        response_findings: list[ResponseFinding] = []
        interpretations = interpretations or {}
        for raw in findings:
            finding_id = str(raw.get("finding_id") or raw.get("id") or "meridian-finding")
            interp = interpretations.get(finding_id) or {}
            official_text = str(raw.get("explanation") or raw.get("finding_text") or "")
            view = OfficialMeridianView(
                finding_id=finding_id,
                severity=str(raw.get("severity") or "INFO"),
                finding_text=official_text,
                metadata={
                    "check_type": raw.get("check_type"),
                    "finding_cause": raw.get("finding_cause"),
                },
                prem3_why_it_matters=interp.get("why_it_matters")
                or "This is official Meridian evidence, not a PreM3 diagnostic.",
                prem3_guidance=interp.get("guidance"),
            )
            views.append(view)
            evidence = EvidenceRef(
                evidence_id=f"official-{finding_id}",
                origin=ResponseOrigin.OFFICIAL_MERIDIAN,
                path="official_meridian.findings",
                label="Official Meridian finding",
                value=official_text,
                artifact="meridian_eda_receipt.json",
            )
            response_findings.append(
                ResponseFinding(
                    finding_id=finding_id,
                    title="Official Meridian finding",
                    observed_fact=official_text,
                    evidence=[evidence],
                    interpretation=view.prem3_why_it_matters,
                    why_it_matters=view.prem3_why_it_matters or "",
                    knowledge_class=KnowledgeClass.MERIDIAN_NORMATIVE,
                    decision_class=DecisionClass.AUTO_BLOCK
                    if view.severity == "ERROR"
                    else DecisionClass.ADVISORY,
                    knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                        KnowledgeClass.MERIDIAN_NORMATIVE
                    ],
                    decision_authority_label="Official Meridian severity preserved",
                    disposition=(
                        PresentationStatus.BLOCKED
                        if view.severity == "ERROR"
                        else PresentationStatus.REVIEW_RECOMMENDED
                    ),
                    origin=ResponseOrigin.OFFICIAL_MERIDIAN,
                    official_severity=view.severity,
                    official_finding_text=official_text,
                    prem3_interpretation=view.prem3_why_it_matters,
                )
            )
        errors = sum(1 for item in views if item.severity == "ERROR")
        status = (
            PresentationStatus.BLOCKED if errors else PresentationStatus.REVIEW_RECOMMENDED
        )
        return _finish(
            response_type=ResponseType.OFFICIAL_MERIDIAN_EDA,
            title="Meridian EDA result",
            summary=(
                f"Official Meridian EDA reported {errors} ERROR findings. "
                "PreM3 interpretation is separate from the official finding text."
            ),
            status=status,
            findings=response_findings,
            official_meridian=views,
            actions=[
                ResponseAction(
                    action_id="next-meridian",
                    action=(
                        "Resolve official ERROR findings before completion."
                        if errors
                        else "Interpret ATTENTION findings, then continue the handoff."
                    ),
                    owner=ResponsibleActor.MODELER if errors else ResponsibleActor.PREM3,
                    reason="Official Meridian owns ERROR/ATTENTION/INFO.",
                    knowledge_class=KnowledgeClass.MERIDIAN_NORMATIVE,
                    decision_class=DecisionClass.AUTO_BLOCK if errors else DecisionClass.ADVISORY,
                    can_prem3_execute=not errors,
                )
            ],
            authority=[
                _authority(KnowledgeClass.MERIDIAN_NORMATIVE, DecisionClass.AUTO_BLOCK)
            ],
            product_behaviors=[ProductBehavior.ASSESS, ProductBehavior.INSIGHT],
            proof=ProofBundle(official_meridian_raw=list(findings)),
            consistency_group="run.official_meridian_eda",
        )

    def model_ready(self, gate: ModelReadyGateEvidence) -> StructuredResponse:
        evidence = [
            EvidenceRef(
                evidence_id="gate-bq",
                origin=ResponseOrigin.RUN_EVIDENCE,
                path="gate.bigquery_verified",
                label="BigQuery verified",
                value=gate.bigquery_verified,
            ),
            EvidenceRef(
                evidence_id="gate-fp",
                origin=ResponseOrigin.RUN_EVIDENCE,
                path="gate.content_fingerprint_matched",
                label="Content fingerprint matched",
                value=gate.content_fingerprint_matched,
            ),
            EvidenceRef(
                evidence_id="gate-eda",
                origin=ResponseOrigin.OFFICIAL_MERIDIAN,
                path="gate.official_meridian_eda_complete",
                label="Official Meridian EDA complete",
                value=gate.official_meridian_eda_complete,
            ),
            EvidenceRef(
                evidence_id="gate-errors",
                origin=ResponseOrigin.OFFICIAL_MERIDIAN,
                path="gate.official_error_count",
                label="Official ERROR count",
                value=gate.official_error_count,
            ),
            EvidenceRef(
                evidence_id="gate-handoff",
                origin=ResponseOrigin.RUN_EVIDENCE,
                path="gate.handoff_persisted",
                label="Handoff persisted",
                value=gate.handoff_persisted,
            ),
        ]
        finding = ResponseFinding(
            finding_id="model-ready-gate",
            title="MODEL_READY gate passed",
            observed_fact="The deterministic pre-modeling gate returned MODEL_READY.",
            evidence=evidence,
            interpretation="Agent prose did not set this state.",
            why_it_matters="MODEL_READY is the verified pre-modeling terminal state.",
            knowledge_class=KnowledgeClass.MERIDIAN_NORMATIVE,
            decision_class=DecisionClass.AUTO_SAFE,
            knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                KnowledgeClass.MERIDIAN_NORMATIVE
            ],
            decision_authority_label="Deterministic gate",
            disposition=PresentationStatus.READY,
            origin=ResponseOrigin.RUN_EVIDENCE,
        )
        return _finish(
            response_type=ResponseType.MODEL_READY,
            title="MODEL_READY",
            summary="The pre-modeling contract has been verified.",
            status=PresentationStatus.READY,
            metrics=[
                ResponseMetric(
                    metric_id="official-errors",
                    label="Official ERROR count",
                    value=gate.official_error_count,
                    evidence_id="gate-errors",
                )
            ],
            findings=[finding],
            actions=[
                ResponseAction(
                    action_id="handoff",
                    action="Proceed to modeler-owned specification and fitting.",
                    owner=ResponsibleActor.MODELER,
                    reason="Posterior sampling remains outside autonomous PreM3 authority.",
                    knowledge_class=KnowledgeClass.MERIDIAN_NORMATIVE,
                    decision_class=DecisionClass.MODELER_REVIEW_REQUIRED,
                    can_prem3_execute=False,
                )
            ],
            gate_evidence=gate,
            product_behaviors=[ProductBehavior.ASSESS, ProductBehavior.GUIDE],
            proof=ProofBundle(receipts=evidence, rule_ids=["MR-020"]),
            technical_details=TechnicalDetails(registry_ids=["MR-020"]),
            consistency_group="run.model_ready",
        )

    def blocked(
        self,
        *,
        reason: str,
        next_action: str,
        owner: ResponsibleActor | str,
        retry_condition: str,
        raw_error: str | None = None,
        run_id: str | None = None,
    ) -> StructuredResponse:
        actor = owner if isinstance(owner, ResponsibleActor) else ResponsibleActor(owner)
        evidence = EvidenceRef(
            evidence_id="blocked-reason",
            origin=ResponseOrigin.RUN_EVIDENCE,
            path="blocked.reason",
            label="Failure reason",
            value=reason,
        )
        finding = ResponseFinding(
            finding_id="blocked",
            title="Execution stopped",
            observed_fact=reason,
            evidence=[evidence],
            interpretation="PreM3 failed closed instead of guessing.",
            why_it_matters="Continuing would invent evidence or skip a required gate.",
            knowledge_class=KnowledgeClass.PREM3_POLICY_BLOCKER,
            decision_class=DecisionClass.AUTO_BLOCK,
            knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                KnowledgeClass.PREM3_POLICY_BLOCKER
            ],
            decision_authority_label="Fail closed",
            disposition=PresentationStatus.BLOCKED,
            origin=ResponseOrigin.RUN_EVIDENCE,
        )
        return _finish(
            response_type=ResponseType.BLOCKED,
            title="Unable to continue",
            summary=reason,
            status=PresentationStatus.BLOCKED,
            findings=[finding],
            actions=[
                ResponseAction(
                    action_id="blocked-next",
                    action=_imperative(next_action),
                    owner=actor,
                    reason=reason,
                    decision_class=DecisionClass.USER_REQUIRED,
                    can_prem3_execute=actor is ResponsibleActor.PREM3,
                    retry_condition=retry_condition,
                )
            ],
            blocked_reason=reason,
            retry_condition=retry_condition,
            product_behaviors=[ProductBehavior.GUIDE],
            technical_details=TechnicalDetails(run_id=run_id, raw_error=raw_error),
            consistency_group="run.blocked",
        )


class _RunContext:
    def __init__(self, bundle: dict[str, Any]) -> None:
        self.bundle = bundle
        self.receipt = bundle.get("receipt") or {}
        self.diagnostics = (self.receipt.get("diagnostics") or {}) or {}
        if not self.diagnostics and bundle.get("diagnostics"):
            self.diagnostics = bundle["diagnostics"]
        self.budget = self.diagnostics.get("parameter_budget") or {}
        self.interview = bundle.get("semantic_interview") or {}
        self.feasibility = bundle.get("modeling_feasibility") or {}
        self.meta = bundle.get("snapshot_meta") or {}
        self.endpoint = self.receipt.get("source_endpoint") or {}

    def row_count(self) -> int:
        return int(self.meta.get("row_count") or self.endpoint.get("row_count") or 0)

    def n_geos(self) -> int:
        return int(self.meta.get("n_geos") or self.budget.get("n_geos") or 0)

    def n_times(self) -> int:
        return int(self.meta.get("n_times") or self.budget.get("n_times") or 0)

    def lenient_ratio(self) -> float | str:
        return (self.budget.get("lenient") or {}).get("ratio") or "unavailable"

    def pressure_band(self) -> str:
        return str((self.budget.get("interpretation") or {}).get("pressure_band") or "UNKNOWN")

    def question_count(self) -> int:
        return int(self.interview.get("question_count") or 0)

    def pre_period_status(self) -> str:
        return str((self.diagnostics.get("pre_period_media") or {}).get("overall") or "UNKNOWN")

    def official_eda_status(self) -> str:
        return str(self.feasibility.get("official_meridian_eda_status") or "PENDING")

    def structural_blocker_count(self) -> int:
        count = 0
        for payload in self.diagnostics.values():
            if not isinstance(payload, dict):
                continue
            finding = payload.get("finding") or payload
            if finding.get("disposition") == "CONTRACT_FAILURE":
                count += 1
        return count

    def ev(
        self, evidence_id: str, path: str, label: str, value: object, artifact: str | None = None
    ) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=evidence_id,
            origin=ResponseOrigin.RUN_EVIDENCE,
            path=path,
            label=label,
            value=(
                value
                if isinstance(value, str | int | float | bool) or value is None
                else str(value)
            ),
            artifact=artifact or "pre_eda_diagnostic_receipt.json",
        )

    def coverage_metrics(self) -> list[ResponseMetric]:
        refs = {
            "rows": self.ev("rows", "snapshot_meta.row_count", "Verified rows", self.row_count()),
            "geos": self.ev("geos", "snapshot_meta.n_geos", "Geographies", self.n_geos()),
            "times": self.ev(
                "times", "snapshot_meta.n_times", "Weekly periods", self.n_times()
            ),
            "blockers": self.ev(
                "blockers",
                "diagnostics.contract_failures",
                "Structural blockers",
                self.structural_blocker_count(),
            ),
            "preperiod": self.ev(
                "preperiod",
                "diagnostics.pre_period_media.overall",
                "Pre-period media",
                self.pre_period_status(),
            ),
        }
        self._coverage_evidence = list(refs.values())
        return [
            ResponseMetric(
                metric_id=key,
                label=ref.label,
                value=ref.value,
                evidence_id=ref.evidence_id,
            )
            for key, ref in refs.items()
        ]

    def parameter_metrics(self) -> list[ResponseMetric]:
        ratio = self.lenient_ratio()
        ref = self.ev(
            "lenient-ratio",
            "diagnostics.parameter_budget.lenient.ratio",
            "Lenient observations per parameter",
            ratio,
        )
        self._parameter_evidence = [ref]
        return [
            ResponseMetric(
                metric_id="lenient-ratio",
                label=ref.label,
                value=ref.value,
                evidence_id=ref.evidence_id,
            )
        ]

    def parameter_finding(self) -> ResponseFinding:
        ratio = self.lenient_ratio()
        evidence = self.ev(
            "lenient-ratio",
            "diagnostics.parameter_budget.lenient.ratio",
            "Lenient observations per parameter",
            ratio,
        )
        return ResponseFinding(
            finding_id="PREM3-PREEDA-PARAMETER-BUDGET",
            title="Parameter pressure is high",
            observed_fact=(
                f"Lenient observations-per-parameter ratio is {ratio} "
                f"({self.pressure_band()} parameter pressure)."
            ),
            evidence=[evidence],
            interpretation=(
                "This is a PreM3/MMM heuristic, not an official Meridian failure. "
                "It may indicate unstable estimates and deserves modeler review."
            ),
            why_it_matters="Higher parameter pressure can make estimates less stable.",
            knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
            decision_class=DecisionClass.ADVISORY,
            knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
            ],
            decision_authority_label="Review recommended",
            disposition=PresentationStatus.REVIEW_RECOMMENDED,
            origin=ResponseOrigin.RUN_EVIDENCE,
            related_action_ids=["review-scope"],
        )

    def pre_period_finding(self) -> ResponseFinding:
        status = self.pre_period_status()
        evidence = self.ev(
            "preperiod",
            "diagnostics.pre_period_media.overall",
            "Pre-period media",
            status,
        )
        return ResponseFinding(
            finding_id="PREM3-PREEDA-PRE-PERIOD",
            title="Pre-period media coverage",
            observed_fact=f"Pre-period media status is {status}.",
            evidence=[evidence],
            interpretation=(
                "Unknown media absence is not treated as zero. "
                "The data cannot establish activity before the modeled window."
            ),
            why_it_matters="Carryover can affect early modeled periods.",
            knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
            decision_class=DecisionClass.ADVISORY,
            knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
            ],
            decision_authority_label="Review recommended",
            disposition=(
                PresentationStatus.REVIEW_RECOMMENDED
                if status == "UNKNOWN"
                else PresentationStatus.PASS
            ),
            origin=ResponseOrigin.RUN_EVIDENCE,
        )

    def semantic_gap_finding(self) -> ResponseFinding:
        count = self.question_count()
        evidence = self.ev(
            "semantic-count",
            "semantic_interview.question_count",
            "Semantic questions",
            count,
            "semantic_readiness_interview.json",
        )
        return ResponseFinding(
            finding_id="PREM3-SEMANTIC-OPEN",
            title="Open semantic questions",
            observed_fact=f"{count} targeted semantic questions were triggered.",
            evidence=[evidence],
            interpretation=(
                "These create a causal question for modeler review. "
                "The table cannot establish confounder, mediator, or treatment roles."
            ),
            why_it_matters="Business-process facts are required before causal roles are assigned.",
            knowledge_class=KnowledgeClass.MMM_JUDGMENT,
            decision_class=DecisionClass.MODELER_REVIEW_REQUIRED,
            knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[KnowledgeClass.MMM_JUDGMENT],
            decision_authority_label="Modeler review required",
            disposition=PresentationStatus.MODELER_REVIEW_REQUIRED,
            origin=ResponseOrigin.RUN_EVIDENCE,
        )

    def extra_diagnostic_findings(self) -> list[ResponseFinding]:
        extras: list[ResponseFinding] = []
        for name in (
            "history",
            "geo_coverage",
            "media_variation",
            "spend_range",
            "collinearity",
            "spend_distribution",
            "missingness_evidence",
            "media_spend_consistency",
            "population_relationships",
            "reach_frequency",
        ):
            payload = self.diagnostics.get(name) or {}
            finding = payload.get("finding") or {}
            if not finding:
                continue
            finding_id = str(finding.get("finding_id") or f"PREM3-{name}")
            evidence_payload = finding.get("observed_evidence") or {}
            evidence = self.ev(
                finding_id,
                f"diagnostics.{name}.finding.observed_evidence",
                str(finding.get("title") or name),
                next(iter(evidence_payload.values()), finding.get("disposition")),
            )
            extras.append(
                ResponseFinding(
                    finding_id=finding_id,
                    title=str(finding.get("title") or name.replace("_", " ")),
                    observed_fact=str(finding.get("what_was_calculated") or finding.get("title")),
                    evidence=[evidence],
                    interpretation=str(finding.get("why_it_matters") or ""),
                    why_it_matters=str(finding.get("why_it_matters") or ""),
                    knowledge_class=KnowledgeClass(
                        finding.get("knowledge_class")
                        or KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
                    ),
                    decision_class=DecisionClass(
                        finding.get("decision_class") or DecisionClass.ADVISORY
                    ),
                    knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                        KnowledgeClass(
                            finding.get("knowledge_class")
                            or KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
                        )
                    ],
                    decision_authority_label=str(
                        finding.get("decision_class") or DecisionClass.ADVISORY.value
                    ),
                    disposition=DISPOSITION_STATUS.get(
                        str(finding.get("disposition") or "PASS"),
                        PresentationStatus.PASS,
                    ),
                    origin=ResponseOrigin.RUN_EVIDENCE,
                    affected_entities=list(finding.get("affected_channels") or []),
                )
            )
        return extras

    def data_summary_findings(self) -> list[ResponseFinding]:
        spend = self.diagnostics.get("spend_distribution") or {}
        channels = spend.get("channels") or []
        names = ", ".join(str(item.get("channel")) for item in channels[:6] if item.get("channel"))
        evidence = self.ev(
            "paid-media",
            "diagnostics.spend_distribution.channels",
            "Paid media channels",
            names or "none",
        )
        missing = self.diagnostics.get("missingness_evidence") or {}
        missing_title = (missing.get("finding") or {}).get("title")
        missing_fact = str(missing_title or "No material missingness flagged.")
        return [
            ResponseFinding(
                finding_id="coverage",
                title="Coverage",
                observed_fact=(
                    f"{self.row_count()} rows, {self.n_geos()} geos, {self.n_times()} periods."
                ),
                evidence=[
                    self.ev("rows", "snapshot_meta.row_count", "Verified rows", self.row_count())
                ],
                why_it_matters="Coverage is the inventory baseline.",
                knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
                decision_class=DecisionClass.AUTO_SAFE,
                knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                    KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
                ],
                decision_authority_label="Informational",
                disposition=PresentationStatus.READY,
                origin=ResponseOrigin.RUN_EVIDENCE,
            ),
            ResponseFinding(
                finding_id="paid-media",
                title="Paid media summary",
                observed_fact=names or "No paid-media channels listed.",
                evidence=[evidence],
                why_it_matters=(
                    "Channel inventory should stay compact unless every column is requested."
                ),
                knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
                decision_class=DecisionClass.AUTO_SAFE,
                knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                    KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
                ],
                decision_authority_label="Informational",
                disposition=PresentationStatus.READY,
                origin=ResponseOrigin.RUN_EVIDENCE,
            ),
            ResponseFinding(
                finding_id="missing",
                title="Missing / unresolved",
                observed_fact=missing_fact,
                evidence=[
                    self.ev(
                        "missing",
                        "diagnostics.missingness_evidence",
                        "Missingness",
                        missing_fact,
                    )
                ],
                why_it_matters="Only material gaps are listed.",
                knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
                decision_class=DecisionClass.ADVISORY,
                knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                    KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
                ],
                decision_authority_label="Informational",
                disposition=PresentationStatus.PASS,
                origin=ResponseOrigin.RUN_EVIDENCE,
            ),
        ]

    def acquisition_findings(self) -> list[ResponseFinding]:
        history = self.diagnostics.get("history") or {}
        finding = history.get("finding") or {}
        evidence = self.ev(
            "history",
            "diagnostics.history",
            "History",
            finding.get("what_was_calculated") or "History diagnostic",
        )
        return [
            ResponseFinding(
                finding_id="history-gap",
                title="Additional history",
                observed_fact=str(finding.get("what_was_calculated") or "History may be limited."),
                evidence=[evidence],
                why_it_matters="More valid history can reduce parameter pressure.",
                knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
                decision_class=DecisionClass.USER_REQUIRED,
                knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
                    KnowledgeClass.MMM_EVIDENCE_HEURISTIC
                ],
                decision_authority_label="User action required",
                disposition=PresentationStatus.USER_ACTION_REQUIRED,
                origin=ResponseOrigin.RUN_EVIDENCE,
            )
        ]

    def parameter_insight(self) -> ResponseInsight:
        ratio = self.lenient_ratio()
        return ResponseInsight(
            insight_id="parameter-ratio",
            statement=(
                f"The current lenient parameter ratio is {ratio} observations "
                "per diagnostic parameter."
            ),
            evidence_ids=["lenient-ratio"],
            implication="This may indicate unstable estimates under the current scope.",
            do_not_claim=(
                "That official Meridian has failed, or that a confounder should be dropped."
            ),
        )

    def question_cards(self) -> list[SemanticQuestionCard]:
        cards: list[SemanticQuestionCard] = []
        for question in self.interview.get("questions") or []:
            trigger = question.get("trigger_evidence") or {}
            evidence = EvidenceRef(
                evidence_id=f"trigger-{question.get('question_id')}",
                origin=ResponseOrigin.RUN_EVIDENCE,
                path="semantic_interview.questions.trigger_evidence",
                label="Trigger evidence",
                value=str(trigger.get("evidence") or trigger),
                artifact="semantic_readiness_interview.json",
            )
            scope = list(question.get("affected_variables") or []) + list(
                question.get("affected_channels") or []
            )
            cards.append(
                SemanticQuestionCard(
                    question_id=str(question.get("question_id")),
                    question=str(question.get("question")),
                    why_asking=str(question.get("why_pre_m3_is_asking")),
                    triggered_by=str(trigger.get("evidence") or "Run-specific trigger."),
                    trigger_evidence=[evidence],
                    what_changes=str(question.get("what_changes_based_on_answer")),
                    owner=ResponsibleActor(
                        question.get("required_human_role") or ResponsibleActor.MODELER
                    ),
                    decision_authority=DecisionClass(
                        question.get("decision_class") or DecisionClass.MODELER_REVIEW_REQUIRED
                    ),
                    affected_scope=scope,
                )
            )
        return cards

    def feasibility_rows(self) -> list[FeasibilityRow]:
        rows: list[FeasibilityRow] = []
        for item in self.feasibility.get("dimensions") or []:
            evidence_blob = item.get("observed_evidence") or {}
            compact = ", ".join(
                f"{key}={evidence_blob[key]}"
                for key in list(evidence_blob)[:3]
                if key not in {"input_fingerprint", "schema_fingerprint"}
            ) or str(item.get("why_it_matters") or "")
            rows.append(
                FeasibilityRow(
                    dimension=str(item.get("dimension")),
                    status=DISPOSITION_STATUS.get(
                        str(item.get("disposition") or "NOT_APPLICABLE"),
                        PresentationStatus.NOT_APPLICABLE,
                    ),
                    evidence=compact,
                    evidence_ids=[str(item.get("dimension"))],
                )
            )
        return rows

    def guidance_items(self) -> list[dict[str, Any]]:
        return list(self.bundle.get("guided_remediation") or [])

    def assessment_actions(self) -> list[ResponseAction]:
        actions = [
            ResponseAction(
                action_id="prem3-scenarios",
                action="Run read-only scope scenarios.",
                owner=ResponsibleActor.PREM3,
                reason="Scope experiments must not mutate production input.",
                knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
                decision_class=DecisionClass.AUTO_SAFE,
                can_prem3_execute=True,
            ),
            ResponseAction(
                action_id="modeler-questions",
                action="Review the open semantic questions.",
                owner=ResponsibleActor.MODELER,
                reason="Causal roles require business context.",
                knowledge_class=KnowledgeClass.MMM_JUDGMENT,
                decision_class=DecisionClass.MODELER_REVIEW_REQUIRED,
                can_prem3_execute=False,
            ),
            ResponseAction(
                action_id="continue-eda",
                action="Continue to official Meridian EDA.",
                owner=ResponsibleActor.PREM3,
                reason="Official EDA remains pending on this local evidence path.",
                knowledge_class=KnowledgeClass.MERIDIAN_NORMATIVE,
                decision_class=DecisionClass.AUTO_SAFE,
                can_prem3_execute=True,
                retry_condition="Official Meridian EDA completes with zero ERROR findings.",
            ),
        ]
        routing = self.bundle.get("learned_routing") or {}
        order = list(routing.get("handoff_action_order") or [])
        if order:
            return reorder_actions(actions, order)
        return actions

    def parameter_actions(self) -> list[ResponseAction]:
        return [
            ResponseAction(
                action_id="review-scope",
                action="Review channel consolidation.",
                owner=ResponsibleActor.ANALYST,
                reason="Parameter pressure is advisory and cannot drop a confirmed confounder.",
                knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
                decision_class=DecisionClass.ADVISORY,
                can_prem3_execute=False,
                requires_approval=True,
                related_finding_ids=["PREM3-PREEDA-PARAMETER-BUDGET"],
            ),
            ResponseAction(
                action_id="export-history",
                action="Export another 52 weeks.",
                owner=ResponsibleActor.DATA_ENGINEER,
                reason="Additional valid history can improve the diagnostic ratio.",
                knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
                decision_class=DecisionClass.ADVISORY,
                can_prem3_execute=False,
                related_finding_ids=["PREM3-PREEDA-PARAMETER-BUDGET"],
            ),
        ]

    def diagnostic_authority(self) -> AuthorityPresentation:
        return _authority(
            KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC, DecisionClass.ADVISORY
        )

    def heuristic_authority(self) -> AuthorityPresentation:
        return _authority(
            KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
            DecisionClass.ADVISORY,
            rule_id="PREM3-PB-001",
        )

    def technical_details(self) -> TechnicalDetails:
        fingerprints = {}
        if self.receipt.get("input_fingerprint"):
            fingerprints["input_fingerprint"] = str(self.receipt["input_fingerprint"])
        elif self.endpoint.get("input_fingerprint"):
            fingerprints["input_fingerprint"] = str(self.endpoint["input_fingerprint"])
        if self.receipt.get("artifact_fingerprint"):
            fingerprints["artifact_fingerprint"] = str(self.receipt["artifact_fingerprint"])
        return TechnicalDetails(
            run_id=str(self.receipt.get("run_id") or self.endpoint.get("run_id") or "") or None,
            fingerprints=fingerprints,
            registry_ids=["PREM3-PB-001", "PREM3-SEM-001"],
            storage_paths=["intelligence/pre_eda_diagnostic_receipt.json"],
            tool_names=["run_pre_eda_diagnostics"],
            raw_enums={
                "finding_origin": "PREM3_PRE_EDA",
                "official_meridian_eda_status": self.official_eda_status(),
            },
        )

    def proof(self) -> ProofBundle:
        details = self.technical_details()
        receipts = [
            self.ev("rows", "snapshot_meta.row_count", "Verified rows", self.row_count()),
            self.ev("geos", "snapshot_meta.n_geos", "Geographies", self.n_geos()),
            self.ev("times", "snapshot_meta.n_times", "Weekly periods", self.n_times()),
            self.ev(
                "blockers",
                "diagnostics.contract_failures",
                "Structural blockers",
                self.structural_blocker_count(),
            ),
            self.ev(
                "preperiod",
                "diagnostics.pre_period_media.overall",
                "Pre-period media",
                self.pre_period_status(),
            ),
            self.ev(
                "lenient-ratio",
                "diagnostics.parameter_budget.lenient.ratio",
                "Lenient observations per parameter",
                self.lenient_ratio(),
            ),
            self.ev(
                "semantic-count",
                "semantic_interview.question_count",
                "Semantic questions",
                self.question_count(),
                "semantic_readiness_interview.json",
            ),
        ]
        return ProofBundle(
            receipts=receipts,
            fingerprints=details.fingerprints,
            bigquery_endpoint=str(self.endpoint.get("resolved_source") or "") or None,
            rule_ids=details.registry_ids,
            artifact_uris=details.storage_paths,
        )


def _authority(
    knowledge: KnowledgeClass,
    decision: DecisionClass,
    rule_id: str | None = None,
) -> AuthorityPresentation:
    return AuthorityPresentation(
        knowledge_class=knowledge,
        decision_class=decision,
        knowledge_label=KNOWLEDGE_AUTHORITY_LABELS[knowledge],
        decision_label=decision.value.replace("_", " ").title(),
        rule_id=rule_id,
        blocks_model_ready=False,
    )


def _finding_rank(finding: ResponseFinding) -> tuple[int, str]:
    if finding.disposition is PresentationStatus.BLOCKED:
        return (0, finding.finding_id)
    if finding.disposition is PresentationStatus.USER_ACTION_REQUIRED:
        return (1, finding.finding_id)
    if finding.disposition is PresentationStatus.MODELER_REVIEW_REQUIRED:
        return (2, finding.finding_id)
    if finding.disposition is PresentationStatus.REVIEW_RECOMMENDED:
        return (3, finding.finding_id)
    return (4, finding.finding_id)


def _prioritize(findings: list[ResponseFinding]) -> tuple[list[ResponseFinding], list[str], int]:
    ordered = sorted(findings, key=_finding_rank)
    if len(ordered) <= TOP_FINDINGS_MAX:
        summary_ids = [item.finding_id for item in ordered]
        extra = 0
    else:
        keep = max(TOP_FINDINGS_MIN, min(TOP_FINDINGS_MAX, 5))
        summary_ids = [item.finding_id for item in ordered[:keep]]
        extra = len(ordered) - keep
    return ordered, summary_ids, extra


def _remediation_sections(item: dict[str, Any]) -> list[ResponseSection]:
    mapping = [
        ("What I found", item.get("what_i_found")),
        ("Why it matters", item.get("why_it_matters")),
        ("Best practice", item.get("best_practice")),
        ("Insight from your data", item.get("insight_from_your_data")),
        ("What PreM3 can do", item.get("what_prem3_can_do")),
        ("What you should do", item.get("what_you_should_do")),
        ("Modeler review", item.get("modeler_review")),
        ("Next step", item.get("next_step")),
    ]
    sections: list[ResponseSection] = []
    for title, body in mapping:
        text = str(body or "").strip()
        if not text:
            continue
        sections.append(
            ResponseSection(section_type=SectionType.GUIDANCE, title=title, body=text)
        )
    return sections


def _scenario_views(payload: dict[str, Any]) -> list[ScenarioView]:
    baseline = payload.get("baseline") or {}
    views: list[ScenarioView] = []
    for index, item in enumerate(payload.get("scenarios") or []):
        if item.get("status") == "REFUSED":
            continue
        current_ratio = baseline.get("lenient_ratio")
        if current_ratio is None:
            current_ratio = (baseline.get("lenient") or {}).get("ratio")
        metrics = item.get("scenario_metrics") or {}
        scenario_ratio = metrics.get("lenient_ratio")
        delta = (item.get("change") or {}).get("lenient_ratio")
        if delta is None:
            improves = "Parameter pressure may change under the assumption."
        elif float(delta) > 0:
            improves = f"Lenient diagnostic ratio improves by {delta}."
        else:
            improves = "The diagnostic ratio does not improve under this assumption."
        title = str(item.get("scenario_type") or f"Scenario {index + 1}").replace("_", " ").title()
        views.append(
            ScenarioView(
                scenario_id=str(item.get("scenario_id") or f"scenario-{index}"),
                title=title,
                assumption=str(
                    item.get("known_limitations")
                    or item.get("assumption")
                    or "Read-only diagnostic assumption."
                ),
                baseline_to_scenario=[
                    {
                        "metric": "Lenient ratio",
                        "current": str(current_ratio),
                        "scenario": str(scenario_ratio),
                    }
                ],
                what_improves=improves,
                what_does_not_change=(
                    "Production model input is unchanged. Semantic validity is not proven."
                ),
                authority=(
                    "Read-only diagnostic. Modeler review required before any production change."
                ),
                required_review=str(
                    item.get("required_authority") or "Modeler / analyst approval required."
                ),
                read_only=bool(item.get("read_only", payload.get("read_only", True))),
                production_data_changed=bool(
                    item.get(
                        "mutated_production_input",
                        payload.get("mutated_production_input", False),
                    )
                ),
            )
        )
    return views


def _imperative(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned.endswith("."):
        cleaned = f"{cleaned}."
    return cleaned


def _finish(**kwargs: Any) -> StructuredResponse:
    findings: list[ResponseFinding] = list(kwargs.get("findings") or [])
    ordered, summary_ids, extra = _prioritize(findings)
    kwargs["findings"] = ordered
    kwargs["disclosure"] = DisclosurePlan(
        summary_finding_ids=summary_ids,
        additional_finding_count=extra,
        view_all_available=extra > 0,
    )
    kwargs["qa_hooks"] = attach_qa_hooks(
        response_type=kwargs["response_type"],
        status=kwargs["status"],
        findings=ordered,
        actions=list(kwargs.get("actions") or []),
        metrics=list(kwargs.get("metrics") or []),
        consistency_group=kwargs.get("consistency_group"),
    )
    return StructuredResponse(**kwargs)
