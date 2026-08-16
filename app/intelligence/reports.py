"""Human-readable ASSESS / ADVISE / INSIGHT / GUIDE reports and guidance items."""

from __future__ import annotations

from typing import Any

from app.core.product import USER_RESOLUTION_TITLE
from app.intelligence.contracts import (
    DecisionClass,
    GuidedRemediationItem,
    IssueFamily,
    KnowledgeClass,
    Prem3DiagnosticDisposition,
    ResponsibleActor,
)


def build_pre_eda_report(summary: dict[str, Any]) -> str:
    assess = summary.get("assess") or {}
    advise = summary.get("advise") or {}
    insight = summary.get("insight") or {}
    guide = summary.get("guide") or {}
    lines = [
        "# PreM3 pre-EDA diagnostic report",
        "",
        "Finding origin: `PREM3_PRE_EDA`. These results are not official Meridian EDA findings.",
        "",
        "## ASSESS",
        "",
        str(assess.get("narrative") or "Verified input was assessed."),
        "",
        "## ADVISE",
        "",
        str(advise.get("narrative") or "Source-backed guidance is attached to each finding."),
        "",
        "## INSIGHT",
        "",
        str(insight.get("narrative") or "Run-specific calculations are in the receipt."),
        "",
        "## GUIDE",
        "",
        str(guide.get("narrative") or "See guided remediation items."),
        "",
    ]
    for item in summary.get("guided_remediation") or []:
        lines.extend(_render_item(item))
    return "\n".join(lines).rstrip() + "\n"


def build_semantic_interview_markdown(interview: dict[str, Any]) -> str:
    lines = [
        "# PreM3 semantic readiness interview",
        "",
        f"Status: `{interview.get('semantic_status')}`",
        f"Question count: `{interview.get('question_count')}`",
        "",
        "Causal roles are not assigned from correlation.",
        "",
    ]
    questions = interview.get("questions") or []
    if not questions:
        lines.append("No run-specific semantic questions were triggered.")
        return "\n".join(lines).rstrip() + "\n"
    for question in questions:
        lines.extend(
            [
                f"## {question.get('question_id')}",
                "",
                f"- Family: `{question.get('question_family')}`",
                f"- Question: {question.get('question')}",
                f"- Why PreM3 is asking: {question.get('why_pre_m3_is_asking')}",
                f"- Possible causal issue: {question.get('possible_causal_issue')}",
                f"- Required role: `{question.get('required_human_role')}`",
                f"- Decision class: `{question.get('decision_class')}`",
                f"- Blocks current input if unresolved: "
                f"`{question.get('blocks_current_input_if_unresolved')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def build_guided_remediation(diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[GuidedRemediationItem] = []
    budget = diagnostics.get("parameter_budget") or {}
    interpretation = budget.get("interpretation") or {}
    if interpretation.get("review_recommended"):
        observed = budget.get("lenient") or {}
        items.append(
            GuidedRemediationItem(
                issue_family=IssueFamily.PARAMETER_PRESSURE,
                finding_id="PREM3-PREEDA-PARAMETER-BUDGET",
                what_i_found=(
                    f"Lenient observations-per-parameter ratio is {observed.get('ratio')} "
                    f"({interpretation.get('pressure_band')} parameter pressure)."
                ),
                why_it_matters=(
                    "High parameter pressure is a modeling-feasibility signal, not an "
                    "official Meridian failure."
                ),
                best_practice=(
                    "Roughly 7–10 observations per parameter is MMM_EVIDENCE_HEURISTIC "
                    "guidance. It cannot independently block MODEL_READY."
                ),
                insight_from_your_data=(
                    f"n_geos={budget.get('n_geos')}, n_times={budget.get('n_times')}, "
                    f"n_treatments={budget.get('n_treatments')}, "
                    f"n_controls={budget.get('n_controls')}, "
                    f"n_knots={budget.get('n_knots')} ({budget.get('n_knots_source')})."
                ),
                what_prem3_can_do=(
                    "Compute the three parameter views and simulate read-only scope scenarios. "
                    "It will not drop a confirmed confounder or merge channels."
                ),
                what_you_should_do=(
                    "Export more history if available, or review eligible channel consolidation "
                    "with the analyst. Owner: DATA_ENGINEER / ANALYST."
                ),
                modeler_review=(
                    "Review time complexity and optional non-confounding predictors. "
                    "Do not treat EDA-only knots as final ModelSpec."
                ),
                next_step="Inspect modeling feasibility, then run official Meridian EDA.",
                responsible_actor=ResponsibleActor.MODELER,
                knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
                decision_class=DecisionClass.ADVISORY,
                source_acquisition=(
                    "Export additional historical KPI and media periods if they exist."
                ),
            )
        )
    missing = diagnostics.get("pre_period_media") or {}
    if missing.get("overall") in {"UNKNOWN", "ABSENT", "PARTIAL"}:
        items.append(
            GuidedRemediationItem(
                issue_family=IssueFamily.SOURCE_ACQUISITION_GAP,
                finding_id="PREM3-PREEDA-PRE-PERIOD-MEDIA",
                what_i_found=f"Pre-period media coverage is {missing.get('overall')}.",
                why_it_matters="Carryover is harder to identify without pre-period media evidence.",
                best_practice="Unknown absence is not confirmed inactivity and is not zero.",
                insight_from_your_data="See channel-level coverage in the diagnostic receipt.",
                what_prem3_can_do="Classify coverage. It will not invent pre-period zeros.",
                what_you_should_do="Request earlier media exports from the source systems.",
                modeler_review="Decide whether to proceed with incomplete pre-period coverage.",
                next_step="Data engineer obtains additional history if available.",
                responsible_actor=ResponsibleActor.DATA_ENGINEER,
                knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
                decision_class=DecisionClass.USER_REQUIRED,
                source_acquisition=(
                    "Export more historical media periods before the first KPI date."
                ),
            )
        )
    interview = diagnostics.get("semantic_interview") or {}
    if int(interview.get("question_count") or 0) > 0:
        items.append(
            GuidedRemediationItem(
                issue_family=IssueFamily.CAUSAL_CONTEXT_GAP,
                finding_id="PREM3-PREEDA-SEMANTIC",
                what_i_found=(
                    f"{interview.get('question_count')} run-specific semantic "
                    "questions were triggered."
                ),
                why_it_matters="The table cannot answer these causal/business process questions.",
                best_practice="Correlation triggers questions. It does not assign causal roles.",
                insight_from_your_data="See the semantic readiness interview artifact.",
                what_prem3_can_do="Ask the triggered questions and record explicit human answers.",
                what_you_should_do="Analyst/marketer answers the triggered questions only.",
                modeler_review=(
                    "Unresolved questions remain MODELER_REVIEW_REQUIRED unless they "
                    "affect current input semantics."
                ),
                next_step="Record semantic context, then continue to official Meridian EDA.",
                responsible_actor=ResponsibleActor.ANALYST,
                knowledge_class=KnowledgeClass.MMM_JUDGMENT,
                decision_class=DecisionClass.MODELER_REVIEW_REQUIRED,
            )
        )
    return [item.model_dump(mode="json") for item in items]


def resolution_pack_header() -> str:
    return USER_RESOLUTION_TITLE


def _render_item(item: dict[str, Any]) -> list[str]:
    sections = [
        ("WHAT I FOUND", item.get("what_i_found")),
        ("WHY IT MATTERS", item.get("why_it_matters")),
        ("BEST PRACTICE", item.get("best_practice")),
        ("INSIGHT FROM YOUR DATA", item.get("insight_from_your_data")),
        ("WHAT PREM3 CAN DO", item.get("what_prem3_can_do")),
        ("WHAT YOU SHOULD DO", item.get("what_you_should_do")),
        ("MODELER REVIEW", item.get("modeler_review")),
        ("NEXT STEP", item.get("next_step")),
    ]
    lines = [
        f"### {item.get('issue_family')} — {item.get('responsible_actor')}",
        "",
    ]
    for title, body in sections:
        if body:
            lines.extend([f"**{title}**", "", str(body), ""])
    return lines


def material_disposition(value: str | None) -> bool:
    return value in {
        Prem3DiagnosticDisposition.REVIEW_RECOMMENDED.value,
        Prem3DiagnosticDisposition.USER_CONTEXT_REQUIRED.value,
        Prem3DiagnosticDisposition.CONTRACT_FAILURE.value,
    }
