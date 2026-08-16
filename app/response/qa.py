"""Output QA hooks. The full Agent Output Evaluation Harness is deferred."""

from __future__ import annotations

from app.intelligence.contracts import KnowledgeClass
from app.response.contracts import (
    UI_COMPONENT_MAP,
    AccuracyHook,
    FormatHook,
    OutputQaHooks,
    PresentationStatus,
    ResponseAction,
    ResponseFinding,
    ResponseMetric,
    ResponseType,
    SectionType,
    SemanticsHook,
)


def attach_qa_hooks(
    *,
    response_type: ResponseType,
    status: PresentationStatus,
    findings: list[ResponseFinding],
    actions: list[ResponseAction],
    metrics: list[ResponseMetric],
    consistency_group: str | None,
) -> OutputQaHooks:
    evidence_ids = [metric.evidence_id for metric in metrics]
    for finding in findings:
        evidence_ids.extend(item.evidence_id for item in finding.evidence)
    return OutputQaHooks(
        accuracy=AccuracyHook(
            evidence_ids=sorted(set(evidence_ids)),
            numeric_paths=[item.path for finding in findings for item in finding.evidence],
            artifact_refs=sorted(
                {
                    item.artifact
                    for finding in findings
                    for item in finding.evidence
                    if item.artifact
                }
            ),
        ),
        semantics=SemanticsHook(
            response_type=response_type,
            status=status,
            knowledge_classes=sorted(
                {finding.knowledge_class for finding in findings},
                key=lambda item: item.value,
            ),
            decision_classes=sorted(
                {finding.decision_class for finding in findings},
                key=lambda item: item.value,
            ),
            owners=sorted({action.owner for action in actions}, key=lambda item: item.value),
            causal_restraint_required=any(
                finding.knowledge_class is KnowledgeClass.MMM_JUDGMENT for finding in findings
            ),
        ),
        format=FormatHook(
            has_title=True,
            has_summary=True,
            section_types=_section_types(response_type),
            technical_details_separated=True,
            ui_components=sorted(UI_COMPONENT_MAP.values()),
        ),
        consistency_group=consistency_group,
        harness_status="deferred",
    )


def _section_types(response_type: ResponseType) -> list[SectionType]:
    mapping = {
        ResponseType.ASSESSMENT: [SectionType.SUMMARY, SectionType.METRICS, SectionType.FINDINGS],
        ResponseType.MODELING_FEASIBILITY: [SectionType.FEASIBILITY],
        ResponseType.SEMANTIC_INTERVIEW: [SectionType.QUESTIONS],
        ResponseType.GUIDED_REMEDIATION: [SectionType.GUIDANCE, SectionType.ACTIONS],
        ResponseType.OFFICIAL_MERIDIAN_EDA: [SectionType.OFFICIAL_MERIDIAN],
        ResponseType.SCOPE_SCENARIO: [SectionType.SCENARIOS],
    }
    return mapping.get(response_type, [SectionType.SUMMARY])
