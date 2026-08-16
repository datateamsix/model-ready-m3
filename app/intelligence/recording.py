"""Record explicit human semantic answers. Never infer a stronger causal conclusion."""

from __future__ import annotations

from typing import Any

from app.core.errors import SafetyViolationError, ValidationBlockedError
from app.intelligence.contracts import ResponsibleActor, SemanticAnswer


def build_semantic_answer(
    *,
    run_id: str,
    question_id: str,
    answer: str,
    actor_role: str,
    affected_variables: list[str] | None = None,
    resolves_input_semantics: bool = False,
    modeler_review_remains: bool = True,
    scope: str = "RUN",
) -> SemanticAnswer:
    text = str(answer or "").strip()
    if not text:
        raise SafetyViolationError("record_semantic_context requires an explicit human answer.")
    if not question_id:
        raise ValidationBlockedError("question_id is required.")
    if scope not in {"RUN", "ORGANIZATION"}:
        raise SafetyViolationError("semantic context scope must be RUN or ORGANIZATION.")
    if scope == "ORGANIZATION":
        raise SafetyViolationError("semantic answers must not be promoted to GLOBAL DOMAIN_VIEW.")
    lowered = text.lower()
    if any(
        token in lowered for token in ("therefore it is a confounder", "therefore it is a mediator")
    ):
        raise SafetyViolationError(
            "PreM3 will not rewrite a human answer into a stronger causal conclusion."
        )
    return SemanticAnswer(
        question_id=question_id,
        answer=text,
        actor_role=ResponsibleActor(actor_role),
        run_id=run_id,
        scope=scope,
        provenance="EXPLICIT_HUMAN_ANSWER",
        affected_variables=list(affected_variables or []),
        resolves_input_semantics=bool(resolves_input_semantics),
        modeler_review_remains=bool(modeler_review_remains),
    )


def merge_semantic_context(
    existing: dict[str, Any] | None, answer: SemanticAnswer
) -> dict[str, Any]:
    payload = dict(existing or {})
    answers = list(payload.get("answers") or [])
    answers.append(answer.model_dump(mode="json"))
    payload["run_id"] = answer.run_id
    payload["answers"] = answers
    payload["promoted_to_domain_view"] = False
    return payload
