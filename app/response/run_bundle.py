"""Read-only backend presentation bundle. Does not recalculate readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.contracts import Issue, RemediationClass
from app.core.state import RunStage
from app.response.contracts import PresentationStatus, ResponseType


def build_run_presentation_bundle(
    *,
    summary: dict[str, Any] | None = None,
    issues: list[Issue] | list[dict[str, Any]] | None = None,
    source_inventory: dict[str, Any] | None = None,
    publish: dict[str, Any] | None = None,
    confirmation: dict[str, Any] | None = None,
    eda: dict[str, Any] | None = None,
    eda_analysis: dict[str, Any] | None = None,
    episode: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize existing run truth for later frontend consumption.

    Presentation may aggregate receipts. It may not invent metrics, collapse
    official Meridian into PreM3 findings, or compute MODEL_READY.
    """
    summary = summary or {}
    issue_rows = _issue_rows(issues)
    confirmation_status = (confirmation or {}).get("status")
    terminal = summary.get("final_state") or (summary.get("gate") or {}).get("terminal")
    return {
        "contract": "RunPresentationBundle",
        "response_type": ResponseType.JUDGE_DEMO.value,
        "run": {
            "run_id": summary.get("run_id"),
            "dataset_fingerprint": summary.get("dataset_fingerprint"),
            "status": summary.get("final_state"),
            "package_uri": summary.get("package_uri"),
            "created_at": summary.get("created_at"),
        },
        "timeline": _timeline(summary.get("state_history") or []),
        "metrics": {
            "rows": (summary.get("model_artifact") or {}).get("row_count"),
            "columns": (summary.get("model_artifact") or {}).get("column_count"),
            "issues_detected": summary.get("detected_issue_count"),
            "issues_resolved": summary.get("resolved_issue_count"),
            "issues_open": summary.get("open_issue_count"),
        },
        "source_inventory": source_inventory or {},
        "findings": [
            {
                "issue_id": item.get("issue_id"),
                "title": item.get("title"),
                "rule_id": item.get("rule_id"),
                "authority": "PREM3_DETERMINISTIC",
                "status": item.get("status"),
                "remediation_class": item.get("remediation_class"),
            }
            for item in issue_rows
        ],
        "actions": [
            {
                "issue_id": item.get("issue_id"),
                "action": (item.get("proposed_action") or {}).get("tool"),
                "status": item.get("status"),
                "owner": _owner(item.get("remediation_class")),
                "authority": item.get("remediation_class"),
            }
            for item in issue_rows
        ],
        "questions": [],
        "bigquery": {
            "table": (summary.get("publish") or {}).get("destination")
            or (publish or {}).get("table_id"),
            "parity": (summary.get("publish") or {}).get("parity_status")
            or (publish or {}).get("parity_status"),
            "fingerprint": (summary.get("model_artifact") or {}).get("fingerprint"),
        },
        "meridian": {
            "official": {
                "status": (summary.get("meridian_eda") or {}).get("status")
                or (eda or {}).get("status"),
                "error_count": (summary.get("meridian_eda") or {}).get("error_count"),
                "attention_count": (summary.get("meridian_eda") or {}).get("attention_count"),
                "info_count": (summary.get("meridian_eda") or {}).get("info_count"),
                "max_severity": (summary.get("meridian_eda") or {}).get("max_severity"),
            },
            "prem3_interpretation": eda_analysis or {},
        },
        "model_ready": {
            "confirmation_status": confirmation_status,
            "terminal": terminal,
            "computed_by_presentation": False,
        },
        "experience": episode or {},
        "artifacts": summary.get("artifact_uris") or {},
        "presentation_status": _presentation_status(terminal, confirmation_status),
    }


def load_run_presentation_bundle(artifact_dir: str | Path) -> dict[str, Any]:
    root = Path(artifact_dir)
    summary = _load_json(root / "run_summary.json")
    issues_doc = _load_json(root / "issues.json") or {}
    return build_run_presentation_bundle(
        summary=summary,
        issues=issues_doc.get("issues") or [],
        source_inventory=_load_json(root / "source_inventory_receipt.json"),
        publish=_load_json(root / "publish_receipt.json"),
        confirmation=_load_json(root / "model_ready_confirmation_receipt.json"),
        eda=_load_json(root / "eda" / "meridian_eda_receipt.json"),
        eda_analysis=_load_json(root / "eda" / "m3_eda_analysis.json"),
    )


def _timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_stage: dict[str, dict[str, Any]] = {}
    for event in events:
        stage = str(event.get("stage") or "")
        by_stage[stage] = {
            "stage": stage,
            "status": event.get("status") or "ACTIVE",
            "message": event.get("message"),
            "progress": event.get("progress"),
        }
    ordered: list[dict[str, Any]] = []
    for stage in RunStage:
        if stage.value in by_stage:
            ordered.append(by_stage[stage.value])
        else:
            ordered.append({"stage": stage.value, "status": "NOT_STARTED"})
    return ordered


def _issue_rows(issues: list[Issue] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in issues or []:
        if isinstance(item, Issue):
            rows.append(item.model_dump(mode="json"))
        else:
            rows.append(dict(item))
    return rows


def _owner(remediation_class: str | None) -> str:
    if remediation_class == RemediationClass.AUTO_SAFE.value:
        return "prem3"
    if remediation_class == RemediationClass.APPROVAL_REQUIRED.value:
        return "user"
    return "modeler"


def _presentation_status(terminal: str | None, confirmation_status: str | None) -> str:
    if confirmation_status == "CONFIRMED" or terminal == "MODEL_READY":
        return PresentationStatus.READY.value
    if terminal == "WAITING_FOR_APPROVAL":
        return PresentationStatus.USER_ACTION_REQUIRED.value
    if terminal == "FAILED":
        return PresentationStatus.BLOCKED.value
    return PresentationStatus.PENDING.value


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
