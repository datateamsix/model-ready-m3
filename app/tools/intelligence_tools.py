"""High-level PreM3 intelligence tools. Gemini chooses among these; it does not calculate."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from app.core.errors import ModelReadyError, SafetyViolationError, ValidationBlockedError
from app.core.execution_context import bound_run_id
from app.core.run_repository import get_run_repository
from app.core.state import RunStage
from app.intelligence import orchestrator as intel_orch
from app.intelligence.persist import persist_intelligence_artifacts
from app.intelligence.recording import build_semantic_answer, merge_semantic_context
from app.intelligence.source import load_verified_snapshot
from app.mel.models import MelError
from app.tools.artifacts import write_json_artifact


def run_pre_eda_diagnostics() -> dict[str, Any]:
    """Compute PreM3 pre-EDA diagnostics from the verified BigQuery model input."""
    try:
        run_id = bound_run_id()
        repo = get_run_repository()
        state = repo.load_run(run_id)
        _require_published(state)
        snapshot = load_verified_snapshot(run_id, repo=repo)
        bundle = intel_orch.run_pre_eda_diagnostics(snapshot)
        uris = persist_intelligence_artifacts(repo=repo, state=state, bundle=bundle)
        return {
            "status": "SUCCESS",
            "tool": "run_pre_eda_diagnostics",
            "run_id": run_id,
            "finding_origin": "PREM3_PRE_EDA",
            "input_fingerprint": snapshot.endpoint.input_fingerprint,
            "resolved_source": snapshot.endpoint.resolved_source,
            "domain_view_version": bundle["receipt"]["domain_view_version"],
            "domain_view_fingerprint": bundle["receipt"]["domain_view_fingerprint"],
            "calculator_version": bundle["receipt"]["calculator_version"],
            "summary": bundle["summary"],
            "computational_readiness": bundle["computational_readiness"],
            "semantic_trigger_summary": bundle["receipt"]["semantic_trigger_summary"],
            "artifact_fingerprint": bundle["receipt"]["artifact_fingerprint"],
            "artifact_uris": uris,
            "model_ready_not_set": True,
        }
    except (ModelReadyError, MelError) as exc:
        return _fail("run_pre_eda_diagnostics", exc)


def inspect_modeling_feasibility() -> dict[str, Any]:
    """Return dimensional modeling feasibility. Distinct from MODEL_READY."""
    try:
        run_id = bound_run_id()
        repo = get_run_repository()
        state = repo.load_run(run_id)
        _require_published(state)
        existing = repo.load_json(run_id, "intelligence/modeling_feasibility.json")
        if existing is None:
            snapshot = load_verified_snapshot(run_id, repo=repo)
            bundle = intel_orch.run_pre_eda_diagnostics(snapshot)
            persist_intelligence_artifacts(repo=repo, state=state, bundle=bundle)
            existing = bundle["modeling_feasibility"]
        return {
            "status": "SUCCESS",
            "tool": "inspect_modeling_feasibility",
            "run_id": run_id,
            "finding_origin": "PREM3_PRE_EDA",
            "score": None,
            "model_ready_is_distinct": True,
            "feasibility": existing,
        }
    except (ModelReadyError, MelError) as exc:
        return _fail("inspect_modeling_feasibility", exc)


def generate_semantic_readiness_interview() -> dict[str, Any]:
    """Generate run-specific semantic questions. No generic questionnaire."""
    try:
        run_id = bound_run_id()
        repo = get_run_repository()
        state = repo.load_run(run_id)
        _require_published(state)
        existing = repo.load_json(run_id, "intelligence/semantic_readiness_interview.json")
        if existing is None:
            snapshot = load_verified_snapshot(run_id, repo=repo)
            bundle = intel_orch.run_pre_eda_diagnostics(snapshot)
            persist_intelligence_artifacts(repo=repo, state=state, bundle=bundle)
            existing = bundle["semantic_interview"]
        return {
            "status": "SUCCESS",
            "tool": "generate_semantic_readiness_interview",
            "run_id": run_id,
            "question_count": existing.get("question_count"),
            "semantic_status": existing.get("semantic_status"),
            "questions": existing.get("questions") or [],
            "causal_roles_assigned": False,
            "generic_questionnaire": False,
        }
    except (ModelReadyError, MelError) as exc:
        return _fail("generate_semantic_readiness_interview", exc)


def simulate_model_scope_scenarios(
    scenarios: list[dict[str, Any]] | str | None = None
) -> dict[str, Any]:
    """Read-only diagnostic scenarios. Never mutates production model input."""
    try:
        run_id = bound_run_id()
        repo = get_run_repository()
        state = repo.load_run(run_id)
        _require_published(state)
        snapshot = load_verified_snapshot(run_id, repo=repo)
        requested = _coerce_scenarios(scenarios)
        bundle = intel_orch.run_pre_eda_diagnostics(snapshot)
        result = intel_orch.run_scope_scenarios(snapshot, diagnostics=bundle, scenarios=requested)
        persist_intelligence_artifacts(repo=repo, state=state, bundle=bundle, scenarios=result)
        return {
            "status": "SUCCESS",
            "tool": "simulate_model_scope_scenarios",
            "run_id": run_id,
            "read_only": True,
            "mutated_production_input": False,
            "input_fingerprint": snapshot.endpoint.input_fingerprint,
            "scenarios": result,
        }
    except (ModelReadyError, MelError) as exc:
        return _fail("simulate_model_scope_scenarios", exc)


def record_semantic_context(
    question_id: str,
    answer: str,
    actor_role: str,
    affected_variables: list[str] | str | None = None,
    resolves_input_semantics: bool = False,
    modeler_review_remains: bool = True,
) -> dict[str, Any]:
    """Persist an explicit human semantic answer. Does not promote DOMAIN_VIEW."""
    try:
        run_id = bound_run_id()
        repo = get_run_repository()
        state = repo.load_run(run_id)
        if state.run_id != run_id:
            raise ValidationBlockedError("Run identity mismatch.")
        recorded = build_semantic_answer(
            run_id=run_id,
            question_id=question_id,
            answer=answer,
            actor_role=actor_role,
            affected_variables=_coerce_str_list(affected_variables),
            resolves_input_semantics=resolves_input_semantics,
            modeler_review_remains=modeler_review_remains,
        )
        existing = repo.load_json(run_id, "intelligence/semantic_context.json")
        payload = merge_semantic_context(existing, recorded)
        path = Path(tempfile.mkdtemp(prefix="prem3-sem-")) / "semantic_context.json"
        write_json_artifact(path, payload)
        uri = repo.upload_workspace_file(run_id, path, "intelligence/semantic_context.json")
        return {
            "status": "SUCCESS",
            "tool": "record_semantic_context",
            "run_id": run_id,
            "question_id": question_id,
            "scope": recorded.scope,
            "promoted_to_domain_view": False,
            "experience_learned": False,
            "experience_applied": False,
            "artifact_uri": uri,
            "answer": recorded.model_dump(mode="json"),
        }
    except (ModelReadyError, MelError) as exc:
        return _fail("record_semantic_context", exc)


def _require_published(state: Any) -> None:
    if state.stage in {
        RunStage.NEW,
        RunStage.DISCOVERING,
        RunStage.PROFILING,
        RunStage.MAPPING,
        RunStage.ASSESSING,
        RunStage.WAITING_FOR_APPROVAL,
        RunStage.REMEDIATING,
        RunStage.VALIDATING,
    }:
        raise ValidationBlockedError(
            "Intelligence tools require a published and verified model-consumption endpoint."
        )


def _coerce_scenarios(value: list[dict[str, Any]] | str | None) -> list[dict[str, Any]] | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            raise SafetyViolationError("scenarios must be a JSON list.")
        return parsed
    return value


def _coerce_str_list(value: list[str] | str | None) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            parsed = json.loads(text)
            if not isinstance(parsed, list):
                raise SafetyViolationError("affected_variables must be a list of strings.")
            return [str(item) for item in parsed]
        return [text]
    return [str(item) for item in value]


def _fail(tool: str, exc: ModelReadyError) -> dict[str, Any]:
    return {
        "status": "FAIL",
        "tool": tool,
        "error": str(exc),
        "error_type": type(exc).__name__,
    }


INTELLIGENCE_TOOLS = [
    run_pre_eda_diagnostics,
    inspect_modeling_feasibility,
    generate_semantic_readiness_interview,
    simulate_model_scope_scenarios,
    record_semantic_context,
]
