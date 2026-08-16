"""Explicit response-type routing from structured intent.

Do not overfit free-text classification. Tests should pass ResponseIntent
fixtures rather than exact user strings.
"""

from __future__ import annotations

from app.response.contracts import ResponseIntent, ResponseType

KIND_TO_TYPE: dict[str, ResponseType] = {
    "definition": ResponseType.DEFINITION,
    "parameter_pressure": ResponseType.DEFINITION,
    "product": ResponseType.PRODUCT_INTELLIGENCE,
    "what_is_prem3": ResponseType.PRODUCT_INTELLIGENCE,
    "assessment": ResponseType.ASSESSMENT,
    "feasibility": ResponseType.MODELING_FEASIBILITY,
    "enough_data": ResponseType.MODELING_FEASIBILITY,
    "advisory": ResponseType.ADVISORY,
    "insight": ResponseType.INSIGHT,
    "remediation": ResponseType.GUIDED_REMEDIATION,
    "what_to_fix": ResponseType.GUIDED_REMEDIATION,
    "semantic_interview": ResponseType.SEMANTIC_INTERVIEW,
    "semantic_question": ResponseType.SEMANTIC_QUESTION,
    "scope_scenario": ResponseType.SCOPE_SCENARIO,
    "data_summary": ResponseType.DATA_SUMMARY,
    "data_acquisition": ResponseType.DATA_ACQUISITION,
    "official_meridian": ResponseType.OFFICIAL_MERIDIAN_EDA,
    "model_ready_run": ResponseType.MODEL_READY,
    "blocked": ResponseType.BLOCKED,
    "learning": ResponseType.LEARNING,
    "what_learned": ResponseType.LEARNING,
    "domain_view": ResponseType.DOMAIN_VIEW,
    "judge_model_ready": ResponseType.JUDGE_DEMO,
    "product_model_ready": ResponseType.PRODUCT_INTELLIGENCE,
    "judge": ResponseType.JUDGE_DEMO,
}


def select_response_type(intent: ResponseIntent) -> ResponseType:
    if intent.response_type is not None:
        return intent.response_type
    if intent.kind in {"enough_data", "assessment"} and not intent.has_run_context:
        return ResponseType.DEFINITION
    if intent.kind == "model_ready" and intent.audience == "judge":
        return ResponseType.JUDGE_DEMO
    if intent.kind == "model_ready":
        return ResponseType.PRODUCT_INTELLIGENCE
    if intent.kind not in KIND_TO_TYPE:
        raise ValueError(f"Unknown response intent kind: {intent.kind}")
    return KIND_TO_TYPE[intent.kind]
