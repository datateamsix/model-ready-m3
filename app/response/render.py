"""Markdown fallback renderer for structured PreM3 responses.

Markdown is not the machine contract. Primary rendering omits Level 3 proof
unless explicitly requested.
"""

from __future__ import annotations

import re

from app.response.contracts import (
    DisclosureLevel,
    ResponseType,
    StructuredResponse,
)

_PROOF_TOKENS = (
    "artifact_fingerprint",
    "input_fingerprint",
    "schema_fingerprint",
    "content_fingerprint",
    "registry_id",
    "gs://",
    "/intelligence/",
    "pre_eda_diagnostic_receipt.json",
)
_HEX_HASH = re.compile(r"\b[a-f0-9]{64}\b")


def render_markdown(
    response: StructuredResponse,
    *,
    level: DisclosureLevel = DisclosureLevel.SUMMARY,
) -> str:
    lines: list[str] = [f"## {response.title}", "", response.summary, ""]
    if response.status:
        lines.extend([f"**Status:** `{response.status.value}`", ""])
    _render_metrics(response, lines)
    if response.response_type is ResponseType.MODELING_FEASIBILITY:
        _render_feasibility(response, lines)
    if response.response_type is ResponseType.SEMANTIC_INTERVIEW:
        _render_interview(response, lines, level)
    elif response.questions:
        _render_questions(response, lines, level)
    if response.response_type is ResponseType.GUIDED_REMEDIATION:
        _render_remediation(response, lines)
    if response.response_type is ResponseType.SCOPE_SCENARIO:
        _render_scenarios(response, lines)
    if response.response_type is ResponseType.OFFICIAL_MERIDIAN_EDA:
        _render_official_meridian(response, lines)
    if response.response_type is ResponseType.DATA_ACQUISITION:
        _render_acquisition(response, lines)
    if response.response_type is ResponseType.JUDGE_DEMO:
        _render_judge(response, lines)
    else:
        _render_insights(response, lines)
        _render_findings(response, lines, level)
        _render_authority(response, lines)
        _render_actions(response, lines)
    if response.response_type is ResponseType.BLOCKED:
        _render_blocked(response, lines)
    if response.response_type is ResponseType.MODEL_READY:
        _render_model_ready_proof(response, lines)
    if level is DisclosureLevel.DETAILS:
        for section in response.sections:
            if section.visible_at is DisclosureLevel.DETAILS and section.body:
                lines.extend([f"### {section.title}", "", section.body, ""])
    if level is DisclosureLevel.PROOF:
        lines.extend(_proof_lines(response))
    text = "\n".join(lines).rstrip() + "\n"
    if level is not DisclosureLevel.PROOF:
        _assert_no_proof_leak(text)
    return text


def _render_metrics(response: StructuredResponse, lines: list[str]) -> None:
    if not response.metrics:
        return
    lines.extend(["### Key evidence", ""])
    for metric in response.metrics:
        unit = f" {metric.unit}" if metric.unit else ""
        lines.append(f"- {metric.label}: {metric.value}{unit}")
    lines.append("")


def _render_feasibility(response: StructuredResponse, lines: list[str]) -> None:
    if not response.feasibility_rows:
        return
    lines.extend(
        [
            "### Modeling feasibility",
            "",
            "| Dimension | Status | Evidence |",
            "|---|---|---|",
        ]
    )
    for row in response.feasibility_rows:
        lines.append(f"| {row.dimension} | {row.status.value} | {row.evidence} |")
    lines.append("")


def _render_interview(
    response: StructuredResponse, lines: list[str], level: DisclosureLevel
) -> None:
    count = len(response.questions)
    lines.extend([f"I need {count} business-context answers.", ""])
    _render_questions(response, lines, level)


def _render_questions(
    response: StructuredResponse, lines: list[str], level: DisclosureLevel
) -> None:
    limit = response.disclosure.question_display_limit
    visible = response.questions
    if level is DisclosureLevel.SUMMARY:
        visible = response.questions[:limit]
    for index, question in enumerate(visible, start=1):
        lines.extend(
            [
                f"### {index}. {question.question}",
                "",
                "**Why I'm asking**",
                question.why_asking,
                "",
                "**Triggered by**",
                question.triggered_by,
                "",
                "**What changes based on the answer**",
                question.what_changes,
                "",
                f"**Who should answer:** {question.owner.value}",
                "",
                f"**Decision authority:** `{question.decision_authority.value}`",
                "",
            ]
        )


def _render_remediation(response: StructuredResponse, lines: list[str]) -> None:
    for section in response.sections:
        if not section.body:
            continue
        lines.extend([f"### {section.title}", "", section.body, ""])


def _render_scenarios(response: StructuredResponse, lines: list[str]) -> None:
    for scenario in response.scenarios:
        lines.extend(
            [
                f"### {scenario.title}",
                "",
                "**Assumption**",
                scenario.assumption,
                "",
                "**Baseline → Scenario**",
                "",
                "| Metric | Current | Scenario |",
                "|---|---:|---:|",
            ]
        )
        for row in scenario.baseline_to_scenario:
            lines.append(
                f"| {row.get('metric', '')} | {row.get('current', '')} | "
                f"{row.get('scenario', '')} |"
            )
        changed = "YES" if scenario.production_data_changed else "NO"
        lines.extend(
            [
                "",
                "**What improves**",
                scenario.what_improves,
                "",
                "**What does not change**",
                scenario.what_does_not_change,
                "",
                f"**Authority / required review:** {scenario.required_review}",
                "",
                "**READ_ONLY**",
                "",
                f"**PRODUCTION DATA CHANGED:** {changed}",
                "",
            ]
        )


def _render_official_meridian(response: StructuredResponse, lines: list[str]) -> None:
    for item in response.official_meridian:
        lines.extend(
            [
                "### Official Meridian finding",
                "",
                f"**Severity:** `{item.severity}`",
                "",
                item.finding_text,
                "",
                "### PreM3 interpretation",
                "",
                item.prem3_why_it_matters or "No additional PreM3 interpretation.",
                "",
            ]
        )
        if item.prem3_guidance:
            lines.extend([item.prem3_guidance, ""])


def _render_acquisition(response: StructuredResponse, lines: list[str]) -> None:
    if not response.findings:
        return
    lines.extend(
        [
            "| Data needed | Why | Source/owner |",
            "|---|---|---|",
        ]
    )
    for finding, action in zip(response.findings, response.actions, strict=False):
        lines.append(
            f"| {finding.title} | {finding.why_it_matters} | {action.owner.value} |"
        )
    lines.append("")


def _render_judge(response: StructuredResponse, lines: list[str]) -> None:
    lines.extend(["### Answer", "", response.summary, "", "### Proof", ""])
    for metric in response.metrics:
        lines.append(f"- {metric.label}: {metric.value}")
    if response.actions:
        lines.extend(["", "### Show", "", response.actions[0].action, ""])


def _render_insights(response: StructuredResponse, lines: list[str]) -> None:
    if not response.insights:
        return
    lines.extend(["### Insight", ""])
    for insight in response.insights:
        lines.append(insight.statement)
        if insight.implication:
            lines.extend(["", insight.implication])
        if insight.do_not_claim:
            lines.extend(["", f"**This does not prove:** {insight.do_not_claim}"])
        lines.append("")


def _render_findings(
    response: StructuredResponse, lines: list[str], level: DisclosureLevel
) -> None:
    if response.response_type in {
        ResponseType.ASSESSMENT,
        ResponseType.MODELING_FEASIBILITY,
        ResponseType.SEMANTIC_INTERVIEW,
        ResponseType.GUIDED_REMEDIATION,
        ResponseType.JUDGE_DEMO,
    }:
        if level is DisclosureLevel.SUMMARY:
            return
    ids = set(response.disclosure.summary_finding_ids)
    visible = [
        finding
        for finding in response.findings
        if level is not DisclosureLevel.SUMMARY or finding.finding_id in ids
    ]
    if not visible:
        return
    lines.extend(["### Findings", ""])
    for finding in visible:
        lines.append(f"- **{finding.title}.** {finding.observed_fact}")
    extra = response.disclosure.additional_finding_count
    if extra > 0 and level is DisclosureLevel.SUMMARY:
        lines.append(f"- VIEW ALL: {extra} additional findings retained.")
    lines.append("")


def _render_authority(response: StructuredResponse, lines: list[str]) -> None:
    if not response.authority:
        return
    item = response.authority[0]
    lines.extend(
        [
            "### Advice",
            "",
            f"**Authority:** {item.knowledge_label}. **Decision:** {item.decision_label}.",
            "",
        ]
    )


def _render_actions(response: StructuredResponse, lines: list[str]) -> None:
    if not response.actions:
        return
    lines.extend(["### Next", ""])
    for action in response.actions:
        lines.append(f"- **{action.owner.value}:** {action.action}")
        if action.retry_condition:
            lines.append(f"  Retry: {action.retry_condition}")
    lines.append("")


def _render_blocked(response: StructuredResponse, lines: list[str]) -> None:
    lines.extend(
        [
            "**What failed**",
            response.blocked_reason or response.summary,
            "",
            "**Why execution stopped**",
            response.summary,
            "",
            f"**Retry:** {response.retry_condition}",
            "",
        ]
    )


def _render_model_ready_proof(response: StructuredResponse, lines: list[str]) -> None:
    gate = response.gate_evidence
    if gate is None:
        return
    lines.extend(
        [
            "### Proof",
            "",
            f"- BigQuery verified: {gate.bigquery_verified}",
            f"- Content fingerprint matched: {gate.content_fingerprint_matched}",
            f"- Official Meridian EDA complete: {gate.official_meridian_eda_complete}",
            f"- Official ERROR count: {gate.official_error_count}",
            f"- Handoff persisted: {gate.handoff_persisted}",
            "",
        ]
    )
    if gate.review_recommended:
        lines.extend(["**Review recommended**", ""])


def _proof_lines(response: StructuredResponse) -> list[str]:
    details = response.technical_details
    lines = ["### Technical details", ""]
    if details.run_id:
        lines.append(f"- run_id: `{details.run_id}`")
    for key, value in sorted(details.fingerprints.items()):
        lines.append(f"- {key}: `{value}`")
    for rule_id in details.registry_ids:
        lines.append(f"- registry: `{rule_id}`")
    for path in details.storage_paths:
        lines.append(f"- path: `{path}`")
    if details.raw_error:
        lines.append(f"- raw_error: `{details.raw_error}`")
    lines.append("")
    return lines


def _assert_no_proof_leak(text: str) -> None:
    lowered = text.lower()
    if "### technical details" in lowered:
        return
    for token in _PROOF_TOKENS:
        if token.lower() in lowered:
            raise ValueError(f"Primary Markdown leaked proof token: {token}")
    if _HEX_HASH.search(lowered):
        raise ValueError("Primary Markdown leaked a content hash.")
