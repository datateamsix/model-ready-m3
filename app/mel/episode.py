"""Close a completed assignment into an ExperienceEpisode.

Does not change the run coordinator or MODEL_READY. Learning is downstream.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

from app.core.contracts import DurableRunState
from app.core.errors import ValidationBlockedError
from app.core.run_repository import RunRepository
from app.core.state import SUCCESS_MILESTONES, TERMINAL_STAGES, RunStage
from app.mel.alignment import align_precheck_and_eda
from app.mel.fingerprint import fingerprint_payload
from app.mel.models import (
    EpisodeTerminalOutcome,
    EvidenceRef,
    ExperienceEpisode,
    MelError,
)
from app.mel.promote import load_active_view
from app.tools.artifacts import write_json_artifact

EPISODE_RELATIVE = "experience/experience_episode.json"

KNOWN_EVIDENCE = (
    ("inventory", "inventory.json"),
    ("issues", "issues.json"),
    ("readiness", "readiness_receipt.json"),
    ("publish", "publish_receipt.json"),
    ("parity", "model_consumption/parity.json"),
    ("meridian_contract", "meridian_input_contract.json"),
    ("pre_eda", "intelligence/pre_eda_diagnostic_receipt.json"),
    ("feasibility", "intelligence/modeling_feasibility.json"),
    ("semantic", "intelligence/semantic_readiness_interview.json"),
    ("scenarios", "intelligence/scope_scenarios.json"),
    ("guided_remediation", "intelligence/guided_remediation.json"),
    ("official_eda", "eda/meridian_eda_receipt.json"),
    ("handoff", "handoff/pre_modeling_handoff.json"),
    ("response", "response/run_response.json"),
)


def episode_id_for(run_id: str) -> str:
    digest = hashlib.sha256(f"episode:{run_id}".encode()).hexdigest()[:16]
    return f"ep-{run_id}-{digest}"


def terminal_outcome_for(state: DurableRunState) -> EpisodeTerminalOutcome | None:
    status = str(state.status or "")
    if state.stage is RunStage.MODEL_READY or state.stage in SUCCESS_MILESTONES:
        return EpisodeTerminalOutcome.MODEL_READY
    if "USER_REQUIRED" in status or state.stage is RunStage.WAITING_FOR_APPROVAL:
        return EpisodeTerminalOutcome.USER_REQUIRED
    if "EDA_BLOCKED" in status:
        return EpisodeTerminalOutcome.EDA_BLOCKED
    if "CONTRACT" in status:
        return EpisodeTerminalOutcome.CONTRACT_BLOCKED
    if "CANCEL" in status:
        return EpisodeTerminalOutcome.CANCELLED
    if state.stage is RunStage.FAILED or state.stage in TERMINAL_STAGES:
        return EpisodeTerminalOutcome.FAILED
    return None


def _fingerprint_blob(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return fingerprint_payload(payload)


def collect_evidence_index(repo: RunRepository, run_id: str) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for kind, relative in KNOWN_EVIDENCE:
        payload = repo.load_json(run_id, relative)
        refs.append(
            EvidenceRef(
                kind=kind,
                path=relative,
                fingerprint=_fingerprint_blob(payload) if payload is not None else None,
                present=payload is not None,
            )
        )
    return refs


def close_experience_episode(
    run_id: str,
    *,
    repo: RunRepository,
    runtime_revision: str | None = None,
    holdout: bool = False,
) -> ExperienceEpisode:
    if not repo.run_exists(run_id):
        raise ValidationBlockedError(f"Run {run_id} does not exist.")
    state = repo.load_run(run_id)
    outcome = terminal_outcome_for(state)
    if outcome is None:
        raise MelError(f"non-terminal run cannot close episode: {state.stage.value}")
    view = load_active_view()
    evidence = collect_evidence_index(repo, run_id)
    pre_eda = repo.load_json(run_id, "intelligence/pre_eda_diagnostic_receipt.json")
    official = repo.load_json(run_id, "eda/meridian_eda_receipt.json")
    alignments = align_precheck_and_eda(pre_eda, official)
    summary = {
        "stage": state.stage.value,
        "status": state.status,
        "detected_issue_count": len(state.detected_issue_ids),
        "resolved_issue_count": len(state.resolved_issue_ids),
        "open_issue_count": len(state.open_issue_ids),
        "bigquery_table": state.bigquery_table,
        "model_consumption_view": state.model_consumption_view,
        "evidence_present": [item.kind for item in evidence if item.present],
        "alignment_counts": _alignment_counts(alignments),
    }
    identity = {
        "run_id": run_id,
        "package_fingerprint": state.package_fingerprint,
        "model_input_fingerprint": state.physical_schema_fingerprint,
        "terminal_outcome": outcome.value,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "domain_view_fingerprint": view.content_fingerprint,
    }
    episode = ExperienceEpisode(
        episode_id=episode_id_for(run_id),
        run_id=run_id,
        organization_id=state.organization_id or None,
        workspace_id=state.workspace_id or None,
        package_identity=state.package_uri,
        episode_started_at=state.created_at.isoformat(),
        episode_closed_at=state.updated_at.isoformat(),
        terminal_outcome=outcome,
        input_fingerprint=state.package_fingerprint,
        model_input_fingerprint=state.physical_schema_fingerprint,
        domain_view_version=view.domain_view_version,
        domain_view_fingerprint=view.content_fingerprint,
        intelligence_version="2.0.0",
        runtime_revision=runtime_revision,
        meridian_version="google-meridian==1.8.0",
        evidence_index=evidence,
        summary=summary,
        alignments=alignments,
        learning_eligible=True,
        content_fingerprint=fingerprint_payload(identity),
        holdout=holdout,
    )
    persist_episode(repo, episode)
    return episode


def maybe_close_experience_episode(
    run_id: str,
    *,
    repo: RunRepository,
    runtime_revision: str | None = None,
    holdout: bool = False,
) -> dict[str, Any]:
    """Close a terminal run into an episode without failing the assignment.

    MEL evaluation is downstream of MODEL_READY. Closure errors are recorded,
    never converted into run failure.
    """
    try:
        if not repo.run_exists(run_id):
            return {"status": "SKIPPED", "reason": "missing_run"}
        state = repo.load_run(run_id)
        if terminal_outcome_for(state) is None:
            return {"status": "SKIPPED", "reason": "non_terminal"}
        episode = close_experience_episode(
            run_id,
            repo=repo,
            runtime_revision=runtime_revision,
            holdout=holdout,
        )
        return {
            "status": "CLOSED",
            "episode_id": episode.episode_id,
            "terminal_outcome": episode.terminal_outcome.value,
            "content_fingerprint": episode.content_fingerprint,
        }
    except Exception as exc:
        return {
            "status": "MEL_EVALUATION_FAILED",
            "error": str(exc),
            "error_type": type(exc).__name__,
        }


def persist_episode(repo: RunRepository, episode: ExperienceEpisode) -> str:
    root = Path(tempfile.mkdtemp(prefix="prem3-episode-"))
    path = root / EPISODE_RELATIVE
    write_json_artifact(path, episode.model_dump(mode="json"))
    return repo.upload_workspace_file(episode.run_id, path, EPISODE_RELATIVE)


def load_episode(repo: RunRepository, run_id: str) -> ExperienceEpisode | None:
    payload = repo.load_json(run_id, EPISODE_RELATIVE)
    if payload is None:
        return None
    return ExperienceEpisode.model_validate(payload)


def _alignment_counts(alignments: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in alignments:
        key = item.relation.value
        counts[key] = counts.get(key, 0) + 1
    return counts
