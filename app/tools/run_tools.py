"""Run-level operational tools for CLOUD_TASKMASTER.

Gemini chooses authorized run operations. The coordinator enforces legality.
Deterministic tools execute and prove. Transform parameters are never agent-supplied.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.contracts import Issue, IssueStatus, RemediationClass, utc_now
from app.core.errors import ModelReadyError, SafetyViolationError, ValidationBlockedError
from app.core.run_coordinator import RunCoordinator
from app.core.run_repository import (
    RunRepository,
    assert_runtime_package,
    fingerprint_package_dir,
    get_run_repository,
    validate_package_uri,
)
from app.core.state import RunStage
from app.tools.adk_tools import (
    get_meridian_pocket_card,
    lookup_provider_card,
    search_provider_directory,
)
from app.tools.artifacts import write_json_artifact
from app.tools.meridian_eda_gate import evaluate_meridian_eda_gate

_RUN_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


def initialize_dataset_run(
    package_uri: str, requested_run_id: str | None = None
) -> dict[str, Any]:
    """Create or safely resume a Dataset A run from an immutable GCS package URI."""
    try:
        repo = get_run_repository()
        normalized = validate_package_uri(package_uri, repo)
        run_id = _resolve_run_id(requested_run_id)
        records = repo.inventory_package(normalized)
        assert_runtime_package(records)
        scratch = _scratch_dir(run_id)
        package_dir = scratch / "package"
        downloaded = repo.download_package(normalized, package_dir)
        assert_runtime_package(downloaded)
        fingerprint, _hashes = fingerprint_package_dir(package_dir)

        if repo.run_exists(run_id):
            existing = repo.load_run(run_id)
            if existing.package_fingerprint != fingerprint:
                raise ValidationBlockedError(
                    "run_id is already bound to a different package fingerprint."
                )
            if existing.package_uri.rstrip("/") != normalized.rstrip("/"):
                raise ValidationBlockedError(
                    "run_id is already bound to a different package URI."
                )
            if existing.stage is RunStage.MODEL_READY:
                return _completed_payload(repo, existing, resumed=True)
            coordinator = _restore_coordinator(repo, existing, package_dir)
            return _assessment_payload(coordinator, resumed=True)

        coordinator = RunCoordinator(
            package_dir, scratch, run_id=run_id, workspace=scratch
        )
        coordinator.package_uri = normalized
        coordinator.durable_prefix = repo.artifact_prefix(run_id)
        coordinator.source_objects = [
            {
                "relative": item.get("relative"),
                "generation": item.get("generation"),
                "name": item.get("name"),
            }
            for item in downloaded
        ]
        coordinator.prepare_workspace()
        coordinator.profile_and_map()
        coordinator.assess()
        coordinator.write_issues()
        return _persist_consequential(repo, coordinator, extra={"resumed": False})
    except ModelReadyError as exc:
        return _fail("initialize_dataset_run", exc)


def inspect_dataset_run(run_id: str) -> dict[str, Any]:
    """Read-only reconstruction of durable run state. Does not modify the run."""
    try:
        repo = get_run_repository()
        state = repo.load_run(run_id)
        issues = repo.load_issues(run_id)
        readiness = repo.load_json(run_id, "readiness_report.json")
        publish = repo.load_json(run_id, "publish_receipt.json")
        contract = repo.load_json(run_id, "meridian_input_contract.json")
        provenance = repo.load_json(run_id, "provenance.json")
        summary = repo.load_json(run_id, "run_summary.json")
        eda = repo.load_json(run_id, "eda/meridian_eda_receipt.json")
        counts = _issue_counts(issues)
        return {
            "status": "SUCCESS",
            "run_id": run_id,
            "stage": state.stage.value,
            "run_status": state.status,
            "package": {
                "uri": state.package_uri,
                "fingerprint": state.package_fingerprint,
                "input_file_count": state.input_file_count,
            },
            "issues": _compact_issues(issues),
            "issue_counts": counts,
            "readiness": {"status": (readiness or {}).get("status")},
            "publish": {
                "status": (publish or {}).get("status"),
                "parity_status": (publish or {}).get("parity_status"),
                "table": state.bigquery_table,
            },
            "meridian_contract": {"status": (contract or {}).get("status")},
            "provenance": {
                "status": ((summary or {}).get("provenance") or {}).get("status"),
                "record_count": len(
                    (provenance or {}).get("records") or (provenance or {}).get("transforms") or []
                ),
            },
            "artifacts": {
                "artifact_prefix": state.artifact_prefix,
                "model_artifact_uri": state.model_artifact_uri,
                "readiness_uri": state.readiness_uri,
                "provenance_uri": state.provenance_uri,
                "manifest_uri": state.manifest_uri,
                "publish_receipt_uri": state.publish_receipt_uri,
                "meridian_contract_uri": state.meridian_contract_uri,
                "run_summary_uri": state.run_summary_uri,
            },
            "bigquery_table": state.bigquery_table,
            "meridian_eda": {
                "status": (eda or {}).get("status"),
                "max_severity": ((eda or {}).get("severity_summary") or {}).get("max_severity"),
            },
            "allowed_next_actions": _allowed_next_actions(
                state.stage, issues, run_id=run_id, repo=repo
            ),
        }
    except ModelReadyError as exc:
        return _fail("inspect_dataset_run", exc)


def apply_safe_remediations(run_id: str, issue_ids: list[str] | str) -> dict[str, Any]:
    """Remediate requested AUTO_SAFE issues. Agent supplies IDs, not transform parameters."""
    try:
        requested = _coerce_issue_ids(issue_ids)
        repo = get_run_repository()
        state = repo.load_run(run_id)
        if state.stage is RunStage.MODEL_READY:
            return _completed_payload(repo, state, resumed=True)
        coordinator = _restore_coordinator(repo, state)
        result = coordinator.remediate_selected(requested)
        payload = _persist_consequential(
            repo,
            coordinator,
            extra={
                "requested_issue_ids": requested,
                "resolved": result["resolved"],
                "rejected": result["rejected"],
            },
        )
        detected, resolved, open_count = coordinator.issue_counts()
        payload["counts"] = {"resolved": resolved, "open": open_count, "detected": detected}
        return payload
    except ModelReadyError as exc:
        return _fail("apply_safe_remediations", exc)


def validate_and_publish_run(run_id: str) -> dict[str, Any]:
    """Validate the model frame, publish a run-scoped BigQuery table, and write the contract."""
    try:
        repo = get_run_repository()
        state = repo.load_run(run_id)
        if state.stage is RunStage.MODEL_READY:
            return _completed_payload(repo, state, resumed=True)
        if state.stage is RunStage.PUBLISHING and state.publish_receipt_uri:
            publish = repo.load_json(run_id, "publish_receipt.json") or {}
            if publish.get("status") == "PUBLISHED" and publish.get("parity_status") == "PASS":
                coordinator = _restore_coordinator(repo, state)
                return _publish_payload(coordinator, replayed=True)
        coordinator = _restore_coordinator(repo, state)
        blockers = coordinator.validation_blockers()
        if blockers:
            raise ValidationBlockedError(
                "validate_and_publish_run preconditions failed: " + ", ".join(blockers)
            )
        coordinator.validate_local()
        published = coordinator.publish()
        payload = _persist_consequential(repo, coordinator)
        payload.update(_publish_fields(coordinator, published))
        return payload
    except ModelReadyError as exc:
        return _fail("validate_and_publish_run", exc)


def run_meridian_eda(run_id: str) -> dict[str, Any]:
    """Run official Google Meridian pre-modeling EDA against confirmed BigQuery input."""
    try:
        repo = get_run_repository()
        state = repo.load_run(run_id)
        if state.stage is RunStage.MODEL_READY:
            return _completed_payload(repo, state, resumed=True)
        coordinator = _restore_coordinator(repo, state)
        executed = coordinator.run_meridian_eda()
        payload = _persist_consequential(repo, coordinator)
        payload.update(executed["compact"])
        payload["allowed_next_actions"] = _allowed_next_actions(
            coordinator.stage, coordinator.issues, coordinator=coordinator
        )
        return payload
    except ModelReadyError as exc:
        return _fail("run_meridian_eda", exc)


def complete_dataset_run(
    run_id: str, eda_analysis: dict[str, Any] | str | None = None
) -> dict[str, Any]:
    """Request evidence-backed MODEL_READY. Status strings cannot be passed in."""
    try:
        repo = get_run_repository()
        state = repo.load_run(run_id)
        if state.stage is RunStage.MODEL_READY:
            return _completed_payload(repo, state, resumed=True)
        coordinator = _restore_coordinator(repo, state)
        missing = [
            name
            for name, path in (
                ("readiness_report.json", coordinator.readiness_path),
                ("publish_receipt.json", coordinator.publish_path),
                ("meridian_input_contract.json", coordinator.contract_path),
                ("provenance.json", coordinator.provenance_path),
                ("model_ready_manifest.json", coordinator.model_ready_manifest_path),
                ("eda/meridian_eda_receipt.json", coordinator.eda_receipt_path),
                ("eda/meridian_eda_report.html", coordinator.eda_html_path),
            )
            if not path.is_file()
        ]
        if missing:
            raise ValidationBlockedError(
                f"complete_dataset_run missing evidence files: {missing}"
            )
        analysis = _sanitize_eda_analysis(eda_analysis)
        completed = coordinator.complete(eda_analysis=analysis)
        payload = _persist_consequential(
            repo, coordinator, extra={"gate": completed.get("gate")}
        )
        gate = completed.get("gate") or {}
        detected, resolved, open_count = coordinator.issue_counts()
        payload.update(
            {
                "status": "MODEL_READY",
                "terminal": gate.get("terminal"),
                "issue_counts": {
                    "detected": detected,
                    "resolved": resolved,
                    "open": open_count,
                },
                "artifacts": (completed.get("summary") or {}).get("artifact_uris"),
                "bigquery_table": coordinator.to_durable_state().bigquery_table,
                "consumption_view": coordinator.consumption_view,
                "gate": gate,
            }
        )
        return payload
    except ModelReadyError as exc:
        payload = _fail("complete_dataset_run", exc)
        if "EDA_BLOCKED" in str(exc):
            payload["status"] = "EDA_BLOCKED"
        return payload


def _scratch_dir(run_id: str) -> Path:
    return Path(tempfile.gettempdir()) / "modelready" / run_id


def _resolve_run_id(requested: str | None) -> str:
    if requested is None or str(requested).strip() == "":
        return f"m3cloud{uuid4().hex[:12]}"
    value = str(requested).strip()
    if not _RUN_ID_RE.match(value):
        raise SafetyViolationError("requested_run_id must be a short alphanumeric id.")
    return value


def _restore_coordinator(
    repo: RunRepository,
    state: Any,
    package_dir: Path | None = None,
) -> RunCoordinator:
    preserved: Path | None = None
    if package_dir is not None and package_dir.exists():
        preserved = Path(tempfile.mkdtemp(prefix="m3-pkg-")) / "package"
        shutil.copytree(package_dir, preserved)
    scratch = _scratch_dir(state.run_id)
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    incoming = scratch / "package"
    if preserved is not None:
        shutil.copytree(preserved, incoming)
    else:
        repo.download_package(state.package_uri, incoming)
    fingerprint, _hashes = fingerprint_package_dir(incoming)
    if fingerprint != state.package_fingerprint:
        raise ValidationBlockedError(
            "Raw package fingerprint no longer matches the bound run. Start a new run_id."
        )
    repo.restore_evidence(state.run_id, scratch)
    coordinator = RunCoordinator(
        incoming, scratch, run_id=state.run_id, workspace=scratch
    )
    issues = repo.load_issues(state.run_id)
    issues_file = scratch / "issues.json"
    if issues_file.is_file() and not issues:
        payload = json.loads(issues_file.read_text(encoding="utf-8"))
        issues = [Issue.model_validate(item) for item in payload.get("issues") or []]
    if not (scratch / "raw").exists():
        shutil.copytree(incoming, scratch / "raw")
    coordinator.restore_from_durable(state, issues)
    return coordinator


def _persist_consequential(
    repo: RunRepository, coordinator: RunCoordinator, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    coordinator.write_issues()
    gate = (extra or {}).get("gate") if extra else None
    summary = coordinator.write_summary(gate if isinstance(gate, dict) else None)
    state = coordinator.to_durable_state()
    write_json_artifact(coordinator.workspace / "run_state.json", state.model_dump(mode="json"))
    uris = repo.sync_artifacts(coordinator.run_id, coordinator.workspace)
    state = coordinator.to_durable_state()
    state.updated_at = utc_now()
    repo.save_run(state)
    repo.save_issues(coordinator.run_id, coordinator.issues)
    payload = _assessment_payload(coordinator, resumed=bool((extra or {}).get("resumed")))
    payload["artifact_uris"] = uris
    payload["run_summary_uri"] = state.run_summary_uri
    if extra:
        payload.update(extra)
    payload["model_artifact"] = summary.get("model_artifact")
    return payload


def _assessment_payload(coordinator: RunCoordinator, *, resumed: bool) -> dict[str, Any]:
    issues = coordinator.issues
    counts = _issue_counts(issues)
    return {
        "status": "SUCCESS",
        "run_id": coordinator.run_id,
        "stage": coordinator.stage.value,
        "resumed": resumed,
        "package": {
            "uri": coordinator.package_uri,
            "fingerprint": coordinator.dataset_fp,
            "input_file_count": coordinator.input_file_count,
        },
        "issues": _compact_issues(issues),
        "issue_counts": {
            "detected": counts["detected"],
            "auto_safe": counts["auto_safe"],
            "approval_required": counts["approval_required"],
            "blocked": counts["blocked"],
            "resolved": counts["resolved"],
            "open": counts["open"],
        },
        "allowed_next_actions": _allowed_next_actions(
            coordinator.stage, issues, coordinator=coordinator
        ),
    }


def _publish_payload(coordinator: RunCoordinator, *, replayed: bool) -> dict[str, Any]:
    payload = _assessment_payload(coordinator, resumed=replayed)
    payload.update(_publish_fields(coordinator, None))
    payload["replayed"] = replayed
    return payload


def _publish_fields(
    coordinator: RunCoordinator, published: dict[str, Any] | None
) -> dict[str, Any]:
    readiness = coordinator._load_json_if_exists(coordinator.readiness_path) or {}
    publish = coordinator._load_json_if_exists(coordinator.publish_path) or {}
    contract = coordinator._load_json_if_exists(coordinator.contract_path) or {}
    provenance = coordinator._load_json_if_exists(coordinator.provenance_path) or {}
    records = provenance.get("records") or provenance.get("transforms") or []
    return {
        "readiness": {"status": readiness.get("status")},
        "publish": {
            "status": publish.get("status"),
            "table": coordinator._publish_destination(publish),
            "parity_status": publish.get("parity_status"),
            "partition_field": publish.get("partition_field"),
            "clustering_fields": publish.get("clustering_fields"),
            "physical_schema_fingerprint": publish.get("physical_schema_fingerprint"),
        },
        "meridian_contract": {"status": contract.get("status")},
        "provenance": {
            "status": coordinator._provenance_status(None, readiness),
            "record_count": len(records),
        },
        "published": published,
    }


def _completed_payload(repo: RunRepository, state: Any, *, resumed: bool) -> dict[str, Any]:
    issues = repo.load_issues(state.run_id)
    summary = repo.load_json(state.run_id, "run_summary.json") or {}
    gate = summary.get("gate") or {}
    counts = _issue_counts(issues)
    return {
        "status": "MODEL_READY" if state.stage is RunStage.MODEL_READY else "SUCCESS",
        "run_id": state.run_id,
        "stage": state.stage.value,
        "resumed": resumed,
        "replayed": True,
        "terminal": gate.get("terminal"),
        "issue_counts": {
            "detected": counts["detected"],
            "resolved": counts["resolved"],
            "open": counts["open"],
        },
        "artifacts": {
            "artifact_prefix": state.artifact_prefix,
            "model_artifact_uri": state.model_artifact_uri,
            "run_summary_uri": state.run_summary_uri,
        },
        "bigquery_table": state.bigquery_table,
        "allowed_next_actions": _allowed_next_actions(
            state.stage, issues, run_id=state.run_id, repo=repo
        ),
    }


def _compact_issues(issues: list[Issue]) -> list[dict[str, Any]]:
    return [
        {
            "issue_id": issue.issue_id,
            "rule_id": issue.rule_id,
            "title": issue.title,
            "remediation_class": issue.remediation_class.value,
            "status": issue.status.value,
        }
        for issue in issues
    ]


def _issue_counts(issues: list[Issue]) -> dict[str, int]:
    return {
        "detected": len(issues),
        "auto_safe": sum(
            issue.remediation_class is RemediationClass.AUTO_SAFE for issue in issues
        ),
        "approval_required": sum(
            issue.remediation_class is RemediationClass.APPROVAL_REQUIRED for issue in issues
        ),
        "blocked": sum(issue.remediation_class is RemediationClass.BLOCKED for issue in issues),
        "resolved": sum(issue.status is IssueStatus.RESOLVED for issue in issues),
        "open": sum(issue.status is not IssueStatus.RESOLVED for issue in issues),
    }


def _allowed_next_actions(
    stage: RunStage,
    issues: list[Issue],
    *,
    coordinator: RunCoordinator | None = None,
    run_id: str | None = None,
    repo: RunRepository | None = None,
) -> list[str]:
    actions = ["inspect_dataset_run"]
    if stage in {RunStage.FAILED, RunStage.COMPLETE}:
        return actions
    open_auto_safe = [
        issue
        for issue in issues
        if issue.remediation_class is RemediationClass.AUTO_SAFE
        and issue.status is not IssueStatus.RESOLVED
    ]
    open_blockers = [
        issue
        for issue in issues
        if issue.remediation_class in {RemediationClass.APPROVAL_REQUIRED, RemediationClass.BLOCKED}
        and issue.status is not IssueStatus.RESOLVED
    ]
    if stage in {RunStage.ASSESSING, RunStage.REMEDIATING} and open_auto_safe:
        actions.append("apply_safe_remediations")
    if (
        stage in {RunStage.ASSESSING, RunStage.REMEDIATING, RunStage.VALIDATING}
        and not open_auto_safe
        and not open_blockers
    ):
        actions.append("validate_and_publish_run")
    if stage is RunStage.PUBLISHING:
        eda_complete, eda_gate_status = _eda_progress(coordinator, run_id, repo)
        if not eda_complete:
            actions.append("run_meridian_eda")
        elif eda_gate_status == "PASS":
            actions.append("complete_dataset_run")
    return actions


def _eda_progress(
    coordinator: RunCoordinator | None,
    run_id: str | None,
    repo: RunRepository | None,
) -> tuple[bool, str | None]:
    receipt: dict[str, Any] | None = None
    html_exists = False
    if coordinator is not None:
        receipt = coordinator._load_json_if_exists(coordinator.eda_receipt_path)
        html_exists = coordinator.eda_html_path.is_file()
    elif repo is not None and run_id:
        receipt = repo.load_json(run_id, "eda/meridian_eda_receipt.json")
        html_exists = receipt is not None
    if not receipt or not html_exists:
        return False, None
    gate = evaluate_meridian_eda_gate(
        receipt=receipt,
        html_persisted=True,
    )
    return True, str(gate.get("status"))


def _sanitize_eda_analysis(value: dict[str, Any] | str | None) -> dict[str, Any] | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise SafetyViolationError("eda_analysis must be a JSON object.")
    forbidden = {
        "severity",
        "eda_gate",
        "error_count",
        "attention_count",
        "info_count",
        "status",
        "parity_status",
        "MODEL_READY",
        "bigquery_table",
    }
    leaked = sorted(key for key in value if key in forbidden)
    if leaked:
        raise SafetyViolationError(
            "eda_analysis may not supply gate, severity, or MODEL_READY fields: "
            + ", ".join(leaked)
        )
    return value


def _coerce_issue_ids(issue_ids: list[str] | str) -> list[str]:
    if isinstance(issue_ids, str):
        text = issue_ids.strip()
        if text.startswith("["):
            parsed = json.loads(text)
            if not isinstance(parsed, list):
                raise SafetyViolationError("issue_ids must be a list of strings.")
            issue_ids = parsed
        elif text:
            issue_ids = [text]
        else:
            issue_ids = []
    if not isinstance(issue_ids, list):
        raise SafetyViolationError("issue_ids must be a list of strings.")
    return [str(item) for item in issue_ids]


def _fail(tool: str, exc: ModelReadyError) -> dict[str, Any]:
    return {
        "status": "FAIL",
        "tool": tool,
        "error": str(exc),
        "error_type": type(exc).__name__,
    }


RUN_READY_TOOLS = [
    initialize_dataset_run,
    inspect_dataset_run,
    apply_safe_remediations,
    validate_and_publish_run,
    run_meridian_eda,
    complete_dataset_run,
]

READ_ONLY_CONTEXT_TOOLS = [
    get_meridian_pocket_card,
    lookup_provider_card,
    search_provider_directory,
]
