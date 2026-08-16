"""Hard presentation-contract validation.

Style-guide word counts are presentation targets, not brittle reject rules.
Hard checks: required fields, authority, grounding, ownership, origin
separation, MODEL_READY gate evidence, and primary-content safety.
"""

from __future__ import annotations

import re

from app.intelligence.contracts import ResponsibleActor
from app.response.contracts import (
    FORBIDDEN_CAUSAL_CLAIMS,
    FORBIDDEN_PRIMARY_SUBSTRINGS,
    TOP_FINDINGS_MAX,
    PresentationStatus,
    ResponseType,
    StructuredResponse,
)

_SEMVER = re.compile(r"\b\d+\.\d+\.\d+\b")
_GROUNDED_NUMBER = re.compile(r"\b\d+\.\d+\b|\b\d{3,}\b")


class ResponseContractError(ValueError):
    """Structured response failed a hard presentation contract."""


def validate_structured_response(response: StructuredResponse) -> None:
    _validate_identity(response)
    _validate_no_primary_stack_trace(response)
    _validate_actions(response)
    _validate_questions(response)
    _validate_metrics_grounded(response)
    _validate_findings(response)
    _validate_official_meridian(response)
    _validate_model_ready(response)
    _validate_blocked(response)
    _validate_disclosure(response)
    _validate_causal_restraint(response)
    _validate_no_duplicate_title_summary(response)


def _validate_identity(response: StructuredResponse) -> None:
    if not response.title.strip():
        raise ResponseContractError("Structured response requires a title.")
    if not response.summary.strip():
        raise ResponseContractError("Structured response requires a summary.")


def _validate_no_primary_stack_trace(response: StructuredResponse) -> None:
    primary = " ".join(
        [
            response.title,
            response.summary,
            response.blocked_reason or "",
            *(finding.observed_fact for finding in response.findings),
            *(finding.interpretation or "" for finding in response.findings),
            *(finding.why_it_matters for finding in response.findings),
            *(action.action for action in response.actions),
            *(section.body or "" for section in response.sections),
        ]
    ).lower()
    for needle in FORBIDDEN_PRIMARY_SUBSTRINGS:
        if needle.lower() in primary:
            raise ResponseContractError("Primary response content must not expose a stack trace.")


def _validate_actions(response: StructuredResponse) -> None:
    for action in response.actions:
        if not action.owner:
            raise ResponseContractError(f"Action {action.action_id} requires an owner.")
        if not action.action.strip():
            raise ResponseContractError(f"Action {action.action_id} requires imperative text.")
        if not action.can_prem3_execute and action.owner is ResponsibleActor.PREM3:
            raise ResponseContractError(
                f"External action {action.action_id} cannot use PREM3 as owner."
            )


def _validate_questions(response: StructuredResponse) -> None:
    for question in response.questions:
        if question.trigger_evidence:
            continue
        if question.open_human_question and question.prior_provenance:
            continue
        raise ResponseContractError(
            f"Semantic question {question.question_id} requires trigger evidence."
        )
    for question in response.questions:
        if not question.question.strip():
            raise ResponseContractError(f"{question.question_id} is missing the question text.")
        if not question.why_asking.strip():
            raise ResponseContractError(f"{question.question_id} is missing why_asking.")
        if not question.affected_scope and not question.open_human_question:
            raise ResponseContractError(f"{question.question_id} is missing affected scope.")
        if not question.decision_authority:
            raise ResponseContractError(f"{question.question_id} is missing decision authority.")


def _validate_metrics_grounded(response: StructuredResponse) -> None:
    evidence_ids = {item.evidence_id for item in _all_evidence(response)}
    for metric in response.metrics:
        if metric.evidence_id not in evidence_ids:
            raise ResponseContractError(
                f"Metric {metric.metric_id} references unknown evidence {metric.evidence_id}."
            )
    allowed_values = {_norm_number(item.value) for item in response.metrics}
    allowed_values.update(_norm_number(item.value) for item in _all_evidence(response))
    allowed_values.discard(None)
    prose = _SEMVER.sub("", f"{response.title} {response.summary}")
    for match in _GROUNDED_NUMBER.finditer(prose):
        token = match.group(0)
        if token in allowed_values:
            continue
        if _looks_like_version(token):
            continue
        raise ResponseContractError(
            f"Unreferenced calculated number {token} in title/summary."
        )


def _validate_findings(response: StructuredResponse) -> None:
    for finding in response.findings:
        if not finding.observed_fact.strip():
            raise ResponseContractError(f"{finding.finding_id} requires observed_fact.")
        interpreted = (finding.interpretation or "").strip()
        if interpreted and interpreted == finding.observed_fact.strip():
            raise ResponseContractError(
                f"{finding.finding_id} must keep observation distinct from interpretation."
            )
        if not finding.evidence:
            raise ResponseContractError(f"{finding.finding_id} requires evidence refs.")
        if finding.origin is None:
            raise ResponseContractError(f"{finding.finding_id} requires an origin.")


def _validate_official_meridian(response: StructuredResponse) -> None:
    for item in response.official_meridian:
        if not item.finding_text.strip():
            raise ResponseContractError(f"{item.finding_id} missing official finding text.")
        prem3_text = (item.prem3_why_it_matters or "").strip()
        if prem3_text and prem3_text == item.finding_text.strip():
            raise ResponseContractError(
                f"{item.finding_id} collapsed official Meridian text into PreM3 interpretation."
            )
        if item.severity not in {"ERROR", "ATTENTION", "INFO"}:
            raise ResponseContractError(f"{item.finding_id} has invalid official severity.")
    for finding in response.findings:
        if finding.official_finding_text and not finding.prem3_interpretation:
            raise ResponseContractError(
                f"{finding.finding_id} must keep PreM3 interpretation separate."
            )


def _validate_model_ready(response: StructuredResponse) -> None:
    if response.response_type is not ResponseType.MODEL_READY:
        return
    gate = response.gate_evidence
    if gate is None:
        raise ResponseContractError("MODEL_READY responses require deterministic gate evidence.")
    if gate.gate_status != "MODEL_READY":
        raise ResponseContractError("MODEL_READY response cannot be built from a non-ready gate.")
    if not gate.bigquery_verified:
        raise ResponseContractError("MODEL_READY requires verified BigQuery input.")
    if not gate.content_fingerprint_matched:
        raise ResponseContractError("MODEL_READY requires a matching content fingerprint.")
    if not gate.official_meridian_eda_complete:
        raise ResponseContractError("MODEL_READY requires official Meridian EDA completion.")
    if gate.official_error_count != 0:
        raise ResponseContractError("MODEL_READY requires official Meridian ERROR count = 0.")
    if not gate.handoff_persisted:
        raise ResponseContractError("MODEL_READY requires a persisted modeler handoff.")


def _validate_blocked(response: StructuredResponse) -> None:
    if response.response_type is not ResponseType.BLOCKED:
        return
    if not (response.blocked_reason or "").strip():
        raise ResponseContractError("Blocked responses require a failure reason.")
    if not (response.retry_condition or "").strip():
        raise ResponseContractError("Blocked responses require a retry condition.")
    if not response.actions:
        raise ResponseContractError("Blocked responses require a next action.")
    if response.status is not PresentationStatus.BLOCKED:
        raise ResponseContractError("Blocked responses must use presentation status BLOCKED.")


def _validate_disclosure(response: StructuredResponse) -> None:
    summary_ids = response.disclosure.summary_finding_ids
    known = {item.finding_id for item in response.findings}
    missing = [item for item in summary_ids if item not in known]
    if missing:
        raise ResponseContractError(f"Summary findings are not retained: {missing}.")
    if len(summary_ids) > TOP_FINDINGS_MAX:
        raise ResponseContractError("Default summary may expose at most 5 material findings.")
    extra = len(response.findings) - len(summary_ids)
    if extra != response.disclosure.additional_finding_count:
        raise ResponseContractError("additional_finding_count must match retained findings.")
    if extra > 0 and not response.disclosure.view_all_available:
        raise ResponseContractError("Additional findings require a VIEW ALL capability.")


def _validate_causal_restraint(response: StructuredResponse) -> None:
    text = " ".join(
        [
            response.summary,
            *(finding.interpretation or "" for finding in response.findings),
            *(finding.prem3_interpretation or "" for finding in response.findings),
            *(insight.statement for insight in response.insights),
            *(item.prem3_guidance or "" for item in response.official_meridian),
        ]
    ).lower()
    if not any(question.question_id for question in response.questions) and not any(
        "causal" in (finding.why_it_matters or "").lower() for finding in response.findings
    ):
        return
    for claim in FORBIDDEN_CAUSAL_CLAIMS:
        if claim in text:
            raise ResponseContractError(f"Causal overclaim is not permitted: {claim}.")


def _validate_no_duplicate_title_summary(response: StructuredResponse) -> None:
    if response.title.strip().lower() == response.summary.strip().lower():
        raise ResponseContractError("Title and summary must not repeat the same statement.")


def _all_evidence(response: StructuredResponse) -> list:
    refs = []
    for finding in response.findings:
        refs.extend(finding.evidence)
    refs.extend(response.proof.receipts)
    for question in response.questions:
        refs.extend(question.trigger_evidence)
    return refs


def _norm_number(value: object) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        if isinstance(value, float):
            return str(value)
        return str(value)
    text = str(value)
    return text if _GROUNDED_NUMBER.fullmatch(text) else None


def _looks_like_version(token: str) -> bool:
    return token.count(".") >= 2
