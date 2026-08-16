"""Product, learning, definition, and judge/demo presentation builders."""

from __future__ import annotations

from app.domain.intelligence.builder import load_current_domain_view
from app.intelligence.contracts import DecisionClass, KnowledgeClass, ResponsibleActor
from app.response.contracts import (
    KNOWLEDGE_AUTHORITY_LABELS,
    AuthorityPresentation,
    DisclosurePlan,
    EvidenceRef,
    PresentationStatus,
    ProductBehavior,
    ResponseAction,
    ResponseFinding,
    ResponseInsight,
    ResponseMetric,
    ResponseOrigin,
    ResponseType,
    StructuredResponse,
    TechnicalDetails,
)
from app.response.qa import attach_qa_hooks


def build_product_response(topic: str) -> StructuredResponse:
    key = _normalize_topic(topic)
    catalog = {
        "what_is_prem3": (
            "What is PreM3?",
            "PreM3 is a self-learning, autonomous pre-modeling agent for Google Meridian. "
            "It maps and mends source data, verifies the BigQuery model input, runs official "
            "Meridian pre-modeling EDA, and hands a trustworthy package to the modeler.",
        ),
        "why_prem3": (
            "Why PreM3?",
            "MMM often becomes expensive before fitting begins. PreM3 systematizes mapping, "
            "safe repair, verification, official EDA, and guided remediation so the modeler "
            "starts from a proven consumption endpoint.",
        ),
        "architecture": (
            "What makes the architecture distinctive?",
            "Gemini decides. Deterministic code proves. Meridian calculates. Gemini interprets. "
            "Experience teaches. Evaluation decides what survives. Truth, presentation, UI, and "
            "QA are separate layers.",
        ),
        "how_model_ready": (
            "How do you determine MODEL_READY?",
            "MODEL_READY is a deterministic terminal state. Agent prose cannot set it. It requires "
            "verified BigQuery input, fingerprint parity, official Meridian EDA with zero ERROR "
            "findings, and a persisted modeler handoff.",
        ),
        "how_answers_reliable": (
            "How do you ensure your answers are reliable?",
            "PreM3 separates truth generation from presentation and evaluates output across "
            "accuracy, semantics, formatting, and consistency. The structured response "
            "architecture is implemented. The full automated evaluation harness is not live.",
        ),
        "how_you_learn": (
            "How do you learn?",
            "PreM3 does not treat memory as learning. MEL evaluates completed work and may "
            "promote lessons into DOMAIN_VIEW only after evidence, scope, safety, and regression "
            "checks. Automatic MEL promotion is not yet proven.",
        ),
        "what_is_domain_view": (
            "What is DOMAIN_VIEW?",
            "DOMAIN_VIEW is the versioned operational knowledge PreM3 is currently authorized "
            "to use. It is generated, not raw memory, and currently contains no promoted "
            "experiential lessons.",
        ),
    }
    title, summary = catalog.get(key, catalog["what_is_prem3"])
    return _product_finish(
        response_type=ResponseType.PRODUCT_INTELLIGENCE,
        title=title,
        summary=summary,
        status=PresentationStatus.COMPLETE,
        consistency_group=f"product.{key}",
        behaviors=[ProductBehavior.ADVISE],
    )


def build_definition_response(topic: str) -> StructuredResponse:
    key = _normalize_topic(topic)
    catalog = {
        "parameter_pressure": (
            "What is parameter pressure?",
            "Parameter pressure compares available observations to the number of diagnostic "
            "parameters implied by geos, time, treatments, controls, and knots.",
            "Higher pressure can make estimates less stable. Interpreting the ratio is an "
            "MMM heuristic, not an official Meridian failure, and cannot independently "
            "block MODEL_READY.",
        ),
        "pre_period_media": (
            "What is pre-period media?",
            "Pre-period media is media activity before the KPI modeling window that may still "
            "affect early modeled periods through carryover.",
            "Unknown absence is not treated as zero. Coverage should be checked by channel.",
        ),
        "confounder": (
            "What is a confounder?",
            "A confounder is a variable that influences both treatment and outcome, creating "
            "a causal question the numeric table cannot settle by correlation alone.",
            "PreM3 may flag timing overlap as a question. It does not assign causal roles.",
        ),
    }
    title, definition, why = catalog.get(key, catalog["parameter_pressure"])
    evidence = EvidenceRef(
        evidence_id="definition-source",
        origin=ResponseOrigin.PRODUCT_CONTEXT,
        path="docs/context/PREM3_MMM_BOOT_CONTEXT.md",
        label="MMM boot context",
        value=title,
    )
    finding = ResponseFinding(
        finding_id=f"def-{key}",
        title=title,
        observed_fact=definition,
        evidence=[evidence],
        interpretation=why,
        why_it_matters=why,
        knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC
        if key == "parameter_pressure"
        else KnowledgeClass.MMM_JUDGMENT,
        decision_class=DecisionClass.ADVISORY,
        knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
            KnowledgeClass.MMM_EVIDENCE_HEURISTIC
            if key == "parameter_pressure"
            else KnowledgeClass.MMM_JUDGMENT
        ],
        decision_authority_label="Definition",
        disposition=PresentationStatus.COMPLETE,
        origin=ResponseOrigin.PRODUCT_CONTEXT,
    )
    return _product_finish(
        response_type=ResponseType.DEFINITION,
        title=title,
        summary=definition,
        status=PresentationStatus.COMPLETE,
        findings=[finding],
        consistency_group=f"definition.{key}",
        behaviors=[ProductBehavior.ADVISE],
    )


def build_learning_response() -> StructuredResponse:
    view = load_current_domain_view()
    count = 0 if view is None else int(view.promoted_lesson_count)
    version = "missing" if view is None else view.domain_view_version
    fingerprint = "missing" if view is None else view.content_fingerprint
    evidence = [
        EvidenceRef(
            evidence_id="lesson-count",
            origin=ResponseOrigin.DOMAIN_VIEW,
            path="domain_view.promoted_lesson_count",
            label="Promoted experiential lessons",
            value=count,
            artifact="app/domain/intelligence/data/current/domain_view.json",
        ),
        EvidenceRef(
            evidence_id="dv-version",
            origin=ResponseOrigin.DOMAIN_VIEW,
            path="domain_view.domain_view_version",
            label="DOMAIN_VIEW version",
            value=version,
        ),
    ]
    summary = (
        "I currently have no promoted experiential lessons. DOMAIN_VIEW is implemented as "
        "authorized operational knowledge. MEL promotion is not yet proven."
        if count == 0
        else f"DOMAIN_VIEW currently contains {count} promoted experiential lessons."
    )
    finding = ResponseFinding(
        finding_id="learning-status",
        title="Current learning status",
        observed_fact=f"Promoted experiential lesson count is {count}.",
        evidence=evidence,
        interpretation=(
            "No experiential lesson was created by presentation. "
            "Memory is not learning."
        ),
        why_it_matters="Users should not infer learning that has not been proven.",
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        decision_class=DecisionClass.AUTO_SAFE,
        knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
            KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
        ],
        decision_authority_label="Current state",
        disposition=PresentationStatus.COMPLETE,
        origin=ResponseOrigin.DOMAIN_VIEW,
    )
    return _product_finish(
        response_type=ResponseType.LEARNING,
        title="What PreM3 has learned",
        summary=summary,
        status=PresentationStatus.COMPLETE,
        metrics=[
            ResponseMetric(
                metric_id="promoted-lessons",
                label="Promoted experiential lessons",
                value=count,
                evidence_id="lesson-count",
            ),
            ResponseMetric(
                metric_id="domain-view-version",
                label="DOMAIN_VIEW version",
                value=version,
                evidence_id="dv-version",
            ),
        ],
        findings=[finding],
        insights=[
            ResponseInsight(
                insight_id="mel-not-proven",
                statement="MEL promotion is not yet proven.",
                evidence_ids=["lesson-count"],
                implication="Automatic lesson promotion has not been demonstrated.",
                do_not_claim="That PreM3 has already learned from production runs.",
            )
        ],
        technical_details=TechnicalDetails(
            fingerprints={"domain_view_fingerprint": fingerprint},
            storage_paths=["app/domain/intelligence/data/current/domain_view.json"],
        ),
        consistency_group="product.learning",
        behaviors=[ProductBehavior.ASSESS],
    )


def build_domain_view_response() -> StructuredResponse:
    view = load_current_domain_view()
    count = 0 if view is None else int(view.promoted_lesson_count)
    version = "missing" if view is None else view.domain_view_version
    fingerprint = "missing" if view is None else view.content_fingerprint
    evidence = EvidenceRef(
        evidence_id="dv-version",
        origin=ResponseOrigin.DOMAIN_VIEW,
        path="domain_view.domain_view_version",
        label="DOMAIN_VIEW version",
        value=version,
    )
    count_ref = EvidenceRef(
        evidence_id="lesson-count",
        origin=ResponseOrigin.DOMAIN_VIEW,
        path="domain_view.promoted_lesson_count",
        label="Promoted experiential lessons",
        value=count,
    )
    finding = ResponseFinding(
        finding_id="domain-view-state",
        title=f"DOMAIN_VIEW {version}",
        observed_fact=(
            f"DOMAIN_VIEW {version} is the current authorized knowledge set, "
            f"with {count} promoted experiential lessons."
        ),
        evidence=[evidence, count_ref],
        interpretation="DOMAIN_VIEW is consumed, not mutated, by presentation.",
        why_it_matters="Operational knowledge is versioned and auditable.",
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        decision_class=DecisionClass.AUTO_SAFE,
        knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
            KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
        ],
        decision_authority_label="Current state",
        disposition=PresentationStatus.COMPLETE,
        origin=ResponseOrigin.DOMAIN_VIEW,
    )
    return _product_finish(
        response_type=ResponseType.DOMAIN_VIEW,
        title=f"DOMAIN_VIEW {version}",
        summary=(
            f"DOMAIN_VIEW {version} is active. Promoted experiential lessons: {count}. "
            "Recent experiential changes: none."
        ),
        status=PresentationStatus.COMPLETE,
        metrics=[
            ResponseMetric(
                metric_id="domain-view-version",
                label="DOMAIN_VIEW version",
                value=version,
                evidence_id="dv-version",
            ),
            ResponseMetric(
                metric_id="promoted-lessons",
                label="Promoted experiential lessons",
                value=count,
                evidence_id="lesson-count",
            ),
        ],
        findings=[finding],
        technical_details=TechnicalDetails(
            fingerprints={"domain_view_fingerprint": fingerprint},
        ),
        consistency_group="product.domain_view",
        behaviors=[ProductBehavior.ASSESS],
    )


def build_judge_response(topic: str) -> StructuredResponse:
    key = _normalize_topic(topic)
    if key in {"how_you_learn", "learning"}:
        answer = (
            "PreM3 learns only through MEL: evaluated experience can become a candidate "
            "lesson, and only promoted lessons update DOMAIN_VIEW. That promotion path "
            "is implemented as architecture, not yet proven in production. Current "
            "DOMAIN_VIEW has zero promoted experiential lessons."
        )
        show = "Open DOMAIN_VIEW v1.0.0 and the empty promoted-lesson set."
        group = "judge.learning"
    elif key in {"architecture", "why_trust", "why_prem3"}:
        answer = (
            "PreM3 does not let one LLM generation own truth, authority, presentation, "
            "and quality. Deterministic tools calculate. Official Meridian owns official "
            "EDA. The response contract presents evidence. QA is designed across accuracy, "
            "semantics, format, and consistency."
        )
        show = "Show the response contract and the output QA architecture diagram."
        group = "judge.architecture"
    else:
        answer = (
            "MODEL_READY is not an LLM opinion or a score. It is a deterministic terminal "
            "state reached only after PreM3 verifies the model input, independently reads "
            "it back from BigQuery, runs official Meridian EDA, confirms zero official "
            "ERROR findings, and persists the handoff evidence."
        )
        show = "Open the run receipt and Meridian EDA artifact."
        group = "judge.model_ready"
    view = load_current_domain_view()
    count = 0 if view is None else int(view.promoted_lesson_count)
    evidence = EvidenceRef(
        evidence_id="lesson-count",
        origin=ResponseOrigin.DOMAIN_VIEW,
        path="domain_view.promoted_lesson_count",
        label="Promoted experiential lessons",
        value=count,
    )
    finding = ResponseFinding(
        finding_id="judge-proof",
        title="Current proof",
        observed_fact=answer,
        evidence=[evidence],
        interpretation="Demo clarity does not change facts.",
        why_it_matters="Judges need spoken-length answers with visible proof.",
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        decision_class=DecisionClass.AUTO_SAFE,
        knowledge_authority_label=KNOWLEDGE_AUTHORITY_LABELS[
            KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
        ],
        decision_authority_label="Current state",
        disposition=PresentationStatus.COMPLETE,
        origin=ResponseOrigin.PRODUCT_CONTEXT,
    )
    return _product_finish(
        response_type=ResponseType.JUDGE_DEMO,
        title="Judge / demo answer",
        summary=answer,
        status=PresentationStatus.COMPLETE,
        metrics=[
            ResponseMetric(
                metric_id="promoted-lessons",
                label="Promoted experiential lessons",
                value=count,
                evidence_id="lesson-count",
            )
        ],
        findings=[finding],
        actions=[
            ResponseAction(
                action_id="show",
                action=show,
                owner=ResponsibleActor.PREM3,
                reason="Demo surface for the spoken answer.",
                decision_class=DecisionClass.AUTO_SAFE,
                can_prem3_execute=True,
            )
        ],
        consistency_group=group,
        behaviors=[ProductBehavior.ASSESS],
    )


def _normalize_topic(topic: str) -> str:
    text = topic.lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "parameter_pressure": "parameter_pressure",
        "what_is_parameter_pressure": "parameter_pressure",
        "pre_period_media": "pre_period_media",
        "confounder": "confounder",
        "what_is_prem3": "what_is_prem3",
        "why_prem3": "why_prem3",
        "architecture": "architecture",
        "architecture_distinctive": "architecture",
        "how_model_ready": "how_model_ready",
        "model_ready": "how_model_ready",
        "how_answers_reliable": "how_answers_reliable",
        "reliability": "how_answers_reliable",
        "how_you_learn": "how_you_learn",
        "learning": "how_you_learn",
        "what_is_domain_view": "what_is_domain_view",
        "domain_view": "what_is_domain_view",
        "why_trust": "why_trust",
    }
    return aliases.get(text, text)


def _product_finish(
    *,
    response_type: ResponseType,
    title: str,
    summary: str,
    status: PresentationStatus,
    findings: list[ResponseFinding] | None = None,
    insights: list[ResponseInsight] | None = None,
    metrics: list[ResponseMetric] | None = None,
    actions: list[ResponseAction] | None = None,
    technical_details: TechnicalDetails | None = None,
    consistency_group: str,
    behaviors: list[ProductBehavior],
) -> StructuredResponse:
    findings = findings or []
    actions = actions or []
    metrics = metrics or []
    return StructuredResponse(
        response_type=response_type,
        title=title,
        summary=summary,
        status=status,
        findings=findings,
        insights=insights or [],
        metrics=metrics,
        actions=actions,
        authority=[
            AuthorityPresentation(
                knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
                decision_class=DecisionClass.AUTO_SAFE,
                knowledge_label=KNOWLEDGE_AUTHORITY_LABELS[
                    KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC
                ],
                decision_label="Current product state",
            )
        ],
        technical_details=technical_details or TechnicalDetails(),
        product_behaviors=behaviors,
        disclosure=DisclosurePlan(
            summary_finding_ids=[item.finding_id for item in findings],
            additional_finding_count=0,
            view_all_available=False,
        ),
        qa_hooks=attach_qa_hooks(
            response_type=response_type,
            status=status,
            findings=findings,
            actions=actions,
            metrics=metrics,
            consistency_group=consistency_group,
        ),
        consistency_group=consistency_group,
    )
