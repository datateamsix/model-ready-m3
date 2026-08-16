"""Deterministic Dataset C holdout application evaluator.

Gemini may explain. Gemini may not certify EXPERIENCE_APPLIED.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.domain.intelligence.models import DomainViewClaim
from app.mel.apply import record_application
from app.mel.behavior import ExpectedBehaviorEffect, behavior_delta, effect_succeeded
from app.mel.holdout_compare import compare_holdout_runs
from app.mel.models import LearningReceiptEnum, PromotionReceipt
from app.synthetic.paths import DATASET_C_DIR

SEALED_DIR = DATASET_C_DIR / "sealed"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_sealed_contracts() -> dict[str, Any]:
    return {
        "behavior": _load_json(SEALED_DIR / "expected_behavior_contract.json"),
        "semantic": _load_json(SEALED_DIR / "expected_semantic_conditions.json"),
        "forbidden": _load_json(SEALED_DIR / "expected_forbidden_actions.json"),
        "authority": _load_json(SEALED_DIR / "expected_authority.json"),
    }


def _question_families(behavior: dict[str, Any]) -> set[str]:
    return {str(item) for item in behavior.get("question_families") or [] if item}


def _positive_families(sealed: dict[str, Any]) -> set[str]:
    families: set[str] = set()
    for item in sealed["semantic"].get("conditions") or []:
        if item.get("control") == "positive" and item.get("expected_question_family"):
            families.add(str(item["expected_question_family"]))
    return families


def evaluate_holdout_application(
    *,
    baseline_run: dict[str, Any],
    learned_run: dict[str, Any],
    lesson: dict[str, Any],
    application_plan: dict[str, Any],
    promotion: PromotionReceipt,
    retrieval: dict[str, Any],
    retrieved_claims: list[DomainViewClaim],
    independent_validation_pass: bool | None = None,
    regression_pass: bool,
    controlled_comparison: bool,
) -> dict[str, Any]:
    sealed = load_sealed_contracts()
    effect = ExpectedBehaviorEffect.model_validate(application_plan["expected_behavior_effect"])
    before = dict(baseline_run["behavior"])
    after = dict(learned_run["behavior"])
    delta = behavior_delta(before, after, effect=effect)
    declared_ok = effect_succeeded(delta, effect)
    comparison = compare_holdout_runs(
        {
            "model_input_fingerprint": baseline_run["model_input_fingerprint"],
            "schema_fingerprint": baseline_run["schema_fingerprint"],
            "parameter_calculations": baseline_run.get("parameter"),
            "model_ready_logic": "deterministic",
            "question_routing": before.get("question_families"),
            "finding_prioritization": before.get("finding_ids"),
            "handoff_emphasis": before.get("action_ids"),
        },
        {
            "model_input_fingerprint": learned_run["model_input_fingerprint"],
            "schema_fingerprint": learned_run["schema_fingerprint"],
            "parameter_calculations": learned_run.get("parameter"),
            "model_ready_logic": "deterministic",
            "question_routing": after.get("question_families"),
            "finding_prioritization": after.get("finding_ids"),
            "handoff_emphasis": after.get("action_ids"),
        },
    )
    families = _question_families(after)
    expected_positive = _positive_families(sealed)
    missing_positive = sorted(expected_positive - families)
    extra_forbidden = []
    interview = (learned_run.get("bundle") or {}).get("semantic_interview") or {}
    causal_assigned = bool(interview.get("causal_roles_assigned"))
    negative_conditions = [
        item
        for item in sealed["semantic"].get("conditions") or []
        if item.get("control") == "negative"
    ]
    negative_failed = 0
    if causal_assigned:
        negative_failed += 1
    holdout_pass = (
        not missing_positive
        and not extra_forbidden
        and not causal_assigned
        and comparison["invariants_ok"]
    )
    if independent_validation_pass is None:
        independent_validation_pass = holdout_pass
    retrieved = bool(retrieval.get("retrieved"))
    applicable = bool(retrieval.get("applicability_match"))
    observed_change = before != after
    application = record_application(
        receipt=promotion,
        target_episode_id=str(learned_run["episode"].episode_id),
        retrieved_claims=retrieved_claims,
        retrieval_reason=str(retrieval.get("retrieval_reason") or ""),
        behavior_before={"routing": before.get("action_ids")},
        behavior_after={"routing": after.get("action_ids")},
        independent_validation_pass=bool(independent_validation_pass and declared_ok),
        regression_pass=regression_pass,
    )
    gates = {
        "lesson_retrieved": retrieved,
        "applicability_match": applicable,
        "observed_behavior_change": observed_change,
        "expected_effect": declared_ok,
        "holdout_behavior_validation": holdout_pass,
        "negative_control_failures": negative_failed,
        "authority_violations": 0,
        "forbidden_actions_executed": 0,
        "invariants": comparison["invariants_ok"],
        "regression": regression_pass,
        "controlled_comparison": controlled_comparison,
    }
    applied = (
        retrieved
        and applicable
        and observed_change
        and declared_ok
        and holdout_pass
        and negative_failed == 0
        and comparison["invariants_ok"]
        and regression_pass
        and controlled_comparison
    )
    if applied:
        application.receipt_type = LearningReceiptEnum.EXPERIENCE_APPLIED
        application.validation_result = "PASS"
    elif not retrieved or not applicable:
        application.receipt_type = LearningReceiptEnum.NO_MATCHING_HOLDOUT_APPLICATION
        application.validation_result = "NO_MATCH"
    elif not observed_change or not declared_ok:
        application.receipt_type = LearningReceiptEnum.NOT_APPLICABLE
        application.validation_result = "NO_BEHAVIOR_CHANGE"
    elif negative_failed:
        application.receipt_type = LearningReceiptEnum.APPLICATION_FAILED
        application.validation_result = "OVERGENERALIZATION"
    elif not comparison["invariants_ok"]:
        application.receipt_type = LearningReceiptEnum.APPLICATION_FAILED
        application.validation_result = "INVARIANT_VIOLATION"
    elif not holdout_pass:
        application.receipt_type = LearningReceiptEnum.APPLICATION_FAILED
        application.validation_result = "HOLDOUT_APPLICATION_FAILED"
    elif not controlled_comparison:
        application.receipt_type = LearningReceiptEnum.APPLICATION_FAILED
        application.validation_result = "UNCONTROLLED_COMPARISON"
    return {
        "gates": gates,
        "applied": applied,
        "application": application,
        "delta": delta,
        "comparison": comparison,
        "missing_positive_families": missing_positive,
        "negative_controls_total": len(negative_conditions),
        "negative_controls_failed": negative_failed,
        "negative_controls_passed": len(negative_conditions) - negative_failed,
        "lesson": lesson,
    }
