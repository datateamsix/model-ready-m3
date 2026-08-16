"""Dynamic semantic-readiness triggers and interview generation.

Correlation and co-occurrence trigger questions. They never assign causal roles.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.intelligence.analyzers import analyze_channel_spend_distribution
from app.intelligence.contracts import (
    AuthorityRef,
    DecisionClass,
    KnowledgeClass,
    ResponsibleActor,
    SemanticQuestion,
    SemanticReadinessStatus,
)
from app.intelligence.registry import rule_authority
from app.intelligence.snapshot import DiagnosticSnapshot

_PROMO = re.compile(r"promo|promotion|campaign_flag", re.I)
_PRICE = re.compile(r"price|discount|markdown", re.I)
_GQV = re.compile(r"gqv|query_volume|search_volume|branded_search", re.I)
_REMARKET = re.compile(r"remarket|retarget|crm|high.?intent", re.I)
_ORGANIC = re.compile(r"organic", re.I)
_SEARCH = re.compile(r"paid_search|search", re.I)
_UPPER = re.compile(r"tv|social|display|video|upper", re.I)
_PRODUCT = re.compile(r"product|sku|campaign_map", re.I)


def detect_semantic_question_triggers(
    snapshot: DiagnosticSnapshot,
    *,
    spend: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    triggers: list[dict[str, Any]] = []
    columns = list(snapshot.frame.columns)
    controls = list(snapshot.contract.controls)
    channels = [spec.channel for spec in snapshot.channels]
    promo_vars = [name for name in [*controls, *columns] if _PROMO.search(name)]
    price_vars = [name for name in [*controls, *columns] if _PRICE.search(name)]
    gqv_vars = [name for name in columns if _GQV.search(name)]
    remarket = [name for name in channels if _REMARKET.search(name)]
    organic = [
        spec.channel
        for spec in snapshot.channels
        if spec.is_organic or _ORGANIC.search(spec.channel)
    ]
    search = [name for name in channels if _SEARCH.search(name)]
    upper = [name for name in channels if _UPPER.search(name)]
    product_vars = [name for name in columns if _PRODUCT.search(name)]
    if promo_vars and snapshot.n_paid_media:
        triggers.append(
            _trigger(
                "PROMOTION_TIMING",
                promo_vars,
                channels,
                "Promotion-like variables coexist with paid media.",
            )
        )
    if price_vars and snapshot.n_paid_media:
        triggers.append(
            _trigger(
                "PRICE_DISCOUNT_TIMING",
                price_vars,
                channels,
                "Price/discount-like variables coexist with paid media.",
            )
        )
    if gqv_vars and search and upper:
        triggers.append(
            _trigger(
                "GOOGLE_QUERY_VOLUME",
                gqv_vars,
                search + upper,
                "GQV-like variables coexist with paid search and upper-funnel media.",
            )
        )
    if search and upper:
        triggers.append(
            _trigger(
                "DOWNSTREAM_MEDIA",
                search + upper,
                search + upper,
                "Upper-funnel and paid-search treatments coexist.",
            )
        )
    if remarket:
        triggers.append(
            _trigger(
                "REMARKETING_TARGETING",
                remarket,
                remarket,
                "Remarketing/retargeting/high-intent channel names are present.",
            )
        )
    if organic:
        triggers.append(
            _trigger(
                "ORGANIC_MEDIA_TIMING",
                organic,
                organic,
                "Organic media is present in the verified input.",
            )
        )
    if product_vars:
        triggers.append(
            _trigger(
                "PRODUCT_CAMPAIGN_MAPPING",
                product_vars,
                channels,
                "Product/campaign mapping fields are present but unresolved.",
            )
        )
    spend = spend or analyze_channel_spend_distribution(snapshot)
    if _budget_spike(snapshot, spend):
        triggers.append(
            _trigger(
                "BUDGET_SETTING",
                [spec.spend_column or spec.channel for spec in snapshot.channels],
                channels,
                "Spend concentration or high-spend periods warrant budget-process questions.",
            )
        )
    existing = [
        str(item.get("family") or item.get("question_family") or "")
        for item in snapshot.semantic_answers
        if item.get("status") == "UNRESOLVED"
    ]
    for family in existing:
        if family and family not in {item["question_family"] for item in triggers}:
            triggers.append(
                _trigger(
                    family,
                    [],
                    [],
                    "Unresolved semantic classification already present on the run.",
                )
            )
    return triggers


def generate_semantic_readiness_interview(
    snapshot: DiagnosticSnapshot,
    *,
    triggers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    triggers = triggers if triggers is not None else detect_semantic_question_triggers(snapshot)
    answered = {str(item.get("question_id")) for item in snapshot.semantic_answers}
    questions: list[SemanticQuestion] = []
    for trigger in triggers:
        question = _question_for(trigger, snapshot)
        if question is None:
            continue
        if question.question_id in answered:
            question.status = "ANSWERED"
        questions.append(question)
    if not questions:
        status = SemanticReadinessStatus.CLEAR
    elif any(
        item.blocks_current_input_if_unresolved and item.status == "OPEN" for item in questions
    ):
        status = SemanticReadinessStatus.USER_CONTEXT_REQUIRED
    elif any(item.modeler_review_if_unresolved and item.status == "OPEN" for item in questions):
        status = SemanticReadinessStatus.MODELER_REVIEW_REQUIRED
    else:
        status = SemanticReadinessStatus.QUESTIONS_OPEN
    return {
        "question_count": len(questions),
        "semantic_status": status.value,
        "triggers": triggers,
        "questions": [item.model_dump(mode="json") for item in questions],
        "causal_roles_assigned": False,
        "generic_questionnaire": False,
    }


def _trigger(
    family: str, variables: list[str], channels: list[str], evidence: str
) -> dict[str, Any]:
    return {
        "question_family": family,
        "affected_variables": [name for name in variables if name],
        "affected_channels": channels,
        "evidence": evidence,
        "causal_role_assigned": False,
    }


def _budget_spike(snapshot: DiagnosticSnapshot, spend: dict[str, Any]) -> bool:
    shares = [item.get("share_of_spend") or 0 for item in spend.get("channels") or []]
    if shares and max(shares) >= 0.6:
        return True
    time_col = snapshot.time_column
    totals = None
    for spec in snapshot.channels:
        if spec.spend_column and spec.spend_column in snapshot.frame.columns:
            series = pd.to_numeric(snapshot.frame[spec.spend_column], errors="coerce").fillna(0)
            totals = series if totals is None else totals.add(series, fill_value=0)
    if totals is None or totals.sum() == 0:
        return False
    by_time = totals.groupby(snapshot.frame[time_col]).sum()
    median = float(by_time.median()) if not by_time.empty else 0.0
    if median <= 0:
        return False
    return bool((by_time > median * 2.5).any())


def _question_for(trigger: dict[str, Any], snapshot: DiagnosticSnapshot) -> SemanticQuestion | None:
    family = trigger["question_family"]
    meta = rule_authority("PREM3-SEM-001")
    authority = AuthorityRef(
        knowledge_class=KnowledgeClass.MMM_JUDGMENT,
        decision_class=DecisionClass.MODELER_REVIEW_REQUIRED,
        rule_id="PREM3-SEM-001",
        source_url=str(meta.get("source_url") or ""),
        source_tier=str(meta.get("source_tier") or ""),
        blocks_model_ready=False,
    )
    templates = {
        "BUDGET_SETTING": (
            "How was total budget and channel allocation determined during the modeling window?",
            "Spend patterns can share causes with the KPI. "
            "The table cannot establish the budget process.",
            "possible shared causes of treatment and KPI (endogeneity)",
            "Whether budget-setting should be treated as a confounder, "
            "documented as a process, or left to the modeler.",
        ),
        "PROMOTION_TIMING": (
            "Were promotions scheduled independently, or were they deliberately "
            "coordinated with media campaigns?",
            "Promotion-like variables coexist with media. Timing process is not in the table.",
            "confounder, predictor, treatment, or mediator remain possible",
            "Whether the promotion variable stays a control, becomes a treatment, "
            "or requires modeler review.",
        ),
        "PRICE_DISCOUNT_TIMING": (
            "Were price changes determined independently of media, or were they timed "
            "to support advertising activity?",
            "Price/discount-like variables coexist with media. "
            "Independence is not calculable from correlation.",
            "price as confounder vs mediator vs independent control remains unresolved",
            "Whether price remains a control. Do not automatically treat price as a control.",
        ),
        "GOOGLE_QUERY_VOLUME": (
            "Did upper-funnel activity materially influence branded search/query demand "
            "during the modeling period?",
            "GQV-like variables coexist with paid search and upper-funnel media.",
            "GQV as confounder vs mediator remains ambiguous",
            "Whether GQV is held out, used as a control, or reserved for modeler specification.",
        ),
        "DOWNSTREAM_MEDIA": (
            "Was paid search (or similar downstream media) allocated because upper-funnel "
            "activity already created demand?",
            "Upper-funnel and search-like treatments coexist. "
            "This pattern is a review trigger, not a causal conclusion.",
            "possible downstream treatment / selection structure",
            "Whether downstream media stays in scope or is flagged for modeler review.",
        ),
        "REMARKETING_TARGETING": (
            "Was this media delivered because users had already shown demand or intent?",
            "Remarketing/retargeting/high-intent activity is present.",
            "selection bias, endogeneity, or downstream treatment",
            "Whether the channel remains in the current input or is reserved for "
            "modeler review. Do not auto-remove it.",
        ),
        "ORGANIC_MEDIA_TIMING": (
            "Was organic activity independent of paid media timing, or did paid campaigns "
            "influence organic volume?",
            "Organic media is in the verified input.",
            "organic as treatment vs collider/mediator remains unresolved",
            "Whether organic remains a treatment in the current input.",
        ),
        "PRODUCT_CAMPAIGN_MAPPING": (
            "Do the mapped product/campaign fields represent the intended modeled intervention?",
            "Product/campaign mapping fields exist. "
            "Semantic correctness is not in the numeric table.",
            "incorrect treatment mapping",
            "Whether current input mappings are valid. This can affect current input semantics.",
        ),
        "PAID_SEARCH_UPPER_FUNNEL": (
            "Did upper-funnel campaigns materially drive branded search "
            "during the modeling period?",
            "Paid search and upper-funnel media coexist.",
            "search as downstream treatment remains possible",
            "Modeler review of search/upper-funnel structure.",
        ),
        "HIGH_INTENT_TARGETING": (
            "Was high-intent targeting delivered because users had already shown demand?",
            "High-intent targeting appears in channel or metadata names.",
            "selection bias / endogeneity",
            "Whether the channel remains in current input. Do not auto-reclassify.",
        ),
    }
    template = templates.get(family)
    if template is None:
        return None
    question, why, issue, changes = template
    blocks_input = family in {"PRODUCT_CAMPAIGN_MAPPING"} and any(
        snapshot.mapping_confidence.get(name, "HIGH") in {"LOW", "UNRESOLVED"}
        for name in trigger.get("affected_variables") or []
    )
    return SemanticQuestion(
        question_id=f"SEM-{family}-{snapshot.endpoint.run_id}",
        question_family=family,
        question=question,
        why_pre_m3_is_asking=why,
        trigger_evidence={
            "evidence": trigger.get("evidence"),
            "run_id": snapshot.endpoint.run_id,
            "input_fingerprint": snapshot.endpoint.input_fingerprint,
        },
        possible_causal_issue=issue,
        affected_variables=list(trigger.get("affected_variables") or []),
        affected_channels=list(trigger.get("affected_channels") or []),
        what_changes_based_on_answer=changes,
        required_human_role=(
            ResponsibleActor.ANALYST if family != "BUDGET_SETTING" else ResponsibleActor.MARKETER
        ),
        decision_class=(
            DecisionClass.USER_REQUIRED if blocks_input else DecisionClass.MODELER_REVIEW_REQUIRED
        ),
        blocks_current_input_if_unresolved=blocks_input,
        modeler_review_if_unresolved=not blocks_input,
        source_authority=authority,
        source_refs=[str(meta.get("source_url") or "")],
        status="OPEN",
    )
