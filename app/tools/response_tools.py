"""Read-only presentation tools. They consume existing evidence and do not calculate."""

from __future__ import annotations

from typing import Any

from app.core.errors import ModelReadyError, ValidationBlockedError
from app.core.execution_context import bound_run_id
from app.core.run_repository import get_run_repository
from app.response.builder import ResponseBuilder
from app.response.contracts import ResponseIntent, ResponseType
from app.response.render import render_markdown
from app.response.routing import select_response_type


def present_run_response(response_kind: str = "assessment") -> dict[str, Any]:
    """Render a structured response from persisted run intelligence."""
    try:
        run_id = bound_run_id()
        repo = get_run_repository()
        state = repo.load_run(run_id)
        if state.run_id != run_id:
            raise ValidationBlockedError("Run identity mismatch.")
        bundle = _load_bundle(repo, run_id)
        intent = ResponseIntent(kind=response_kind, has_run_context=True)
        builder = ResponseBuilder()
        scenarios = repo.load_json(run_id, "intelligence/scope_scenarios.json")
        response = builder.from_intent(intent, bundle=bundle, scenarios=scenarios)
        payload = response.model_dump(mode="json")
        return {
            "status": "SUCCESS",
            "tool": "present_run_response",
            "run_id": run_id,
            "response_type": response.response_type.value,
            "response": payload,
            "markdown": render_markdown(response),
            "recalculated": False,
        }
    except ModelReadyError as exc:
        return {
            "status": "FAIL",
            "tool": "present_run_response",
            "error": str(exc),
            "error_type": type(exc).__name__,
        }


def present_product_response(
    topic: str, audience: str = "user"
) -> dict[str, Any]:
    """Render a structured product, learning, or judge/demo response."""
    intent = ResponseIntent(
        kind=topic,
        audience="judge" if audience == "judge" else "user",
    )
    if intent.kind == "model_ready":
        intent = ResponseIntent(
            kind="model_ready",
            audience="judge" if audience == "judge" else "user",
        )
    try:
        response_type = select_response_type(intent)
    except ValueError:
        intent = ResponseIntent(kind="product", audience=intent.audience)
        response_type = ResponseType.PRODUCT_INTELLIGENCE
    response = ResponseBuilder().from_intent(intent, topic=topic)
    return {
        "status": "SUCCESS",
        "tool": "present_product_response",
        "response_type": response_type.value,
        "response": response.model_dump(mode="json"),
        "markdown": render_markdown(response),
        "recalculated": False,
    }


def _load_bundle(repo: Any, run_id: str) -> dict[str, Any]:
    receipt = repo.load_json(run_id, "intelligence/pre_eda_diagnostic_receipt.json")
    if receipt is None:
        raise ValidationBlockedError(
            "No persisted run intelligence. Call run_pre_eda_diagnostics first."
        )
    budget = (receipt.get("diagnostics") or {}).get("parameter_budget") or {}
    return {
        "receipt": receipt,
        "modeling_feasibility": repo.load_json(
            run_id, "intelligence/modeling_feasibility.json"
        )
        or {},
        "semantic_interview": repo.load_json(
            run_id, "intelligence/semantic_readiness_interview.json"
        )
        or {},
        "guided_remediation": (
            repo.load_json(run_id, "intelligence/guided_remediation.json") or {}
        ).get("items")
        or [],
        "summary": repo.load_json(run_id, "intelligence/run_intelligence_summary.json") or {},
        "snapshot_meta": {
            "row_count": (receipt.get("source_endpoint") or {}).get("row_count"),
            "n_geos": budget.get("n_geos"),
            "n_times": budget.get("n_times"),
        },
    }


RESPONSE_TOOLS = [
    present_run_response,
    present_product_response,
]
