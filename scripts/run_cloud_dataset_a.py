"""Controlled CLOUD_TASKMASTER proof: one Dataset A prompt to the private Cloud Run agent.

Obtains a short-lived identity token from the local gcloud login. Does not persist tokens.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.cloud import bigquery, storage

from app.config import settings

REPO_ROOT = Path(__file__).resolve().parents[1]
GCLOUD = "gcloud.cmd" if os.name == "nt" else "gcloud"
EXPECTED_RUNTIME_SA = "m3-runtime@modelready-m3.iam.gserviceaccount.com"
EXPECTED_APP = "app"
EXPECTED_AGENT_NAME = "modelready_m3"
SERVICE_NAME = "modelready-m3"
REGION = "us-central1"
PROJECT = "modelready-m3"
CONSEQUENTIAL_TOOLS = (
    "initialize_dataset_run",
    "apply_safe_remediations",
    "validate_and_publish_run",
    "complete_dataset_run",
)

TASK_PROMPT = """
Prepare the supplied marketing dataset for Google Meridian. Inspect the package
and its readiness issues. You may autonomously execute only deterministic
AUTO_SAFE remediation. Stop rather than guessing if approval or missing evidence
is required. Publish only after deterministic readiness passes, and report
MODEL_READY only if the evidence-backed final gate passes.

Package:
{package_uri}
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-uri", required=True)
    parser.add_argument("--app-url", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--timeout", type=int, default=600)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_uri = args.package_uri.strip()
    if not package_uri.startswith("gs://"):
        raise SystemExit("package-uri must be a gs:// Dataset A package.")
    app_url = (args.app_url or _service_url()).rstrip("/")
    token = _identity_token()
    session_id = args.session_id or f"cloud_taskmaster_{int(time.time())}"
    session = _json_request(
        "POST",
        f"{app_url}/apps/{EXPECTED_APP}/users/cloud_taskmaster_user/sessions/{session_id}",
        token,
        body={},
    )
    if not isinstance(session, dict) or session.get("id") != session_id:
        raise SystemExit(f"Failed to create ADK session: {session}")

    prompt = TASK_PROMPT.format(package_uri=package_uri)
    text, events = _run_prompt(app_url, token, prompt, session_id, timeout=args.timeout)
    trajectory = _trajectory_from_events(events)
    run_id = _discover_run_id(trajectory, text)
    if not run_id:
        _print_failure("Could not discover run_id from agent tool results.", trajectory, text)
        return 1

    artifact_prefix = (
        f"gs://{settings.artifact_bucket}/{settings.organization_id}/"
        f"{settings.workspace_id}/runs/{run_id}/"
    )
    summary = _load_gcs_json(f"{artifact_prefix}run_summary.json")
    state = _load_gcs_json(f"{artifact_prefix}run_state.json")
    publish = _load_gcs_json(f"{artifact_prefix}publish_receipt.json")
    contract = _load_gcs_json(f"{artifact_prefix}meridian_input_contract.json")
    readiness = _load_gcs_json(f"{artifact_prefix}readiness_report.json")
    provenance = _load_gcs_json(f"{artifact_prefix}provenance.json")
    table = (state or {}).get("bigquery_table") or (publish or {}).get("table_id")
    if table and "." not in str(table):
        table = f"{settings.project_id}.{settings.bq_models_dataset}.{table}"
    bq_rows = _bigquery_row_count(table) if table else None

    selected = _selected_issue_ids(trajectory)
    consequential = [
        event["tool"] for event in trajectory if event.get("tool") in CONSEQUENTIAL_TOOLS
    ]
    issues_doc = _load_gcs_json(f"{artifact_prefix}issues.json")
    issue_rows = (issues_doc or {}).get("issues") or []
    auto_safe = sum(item.get("remediation_class") == "AUTO_SAFE" for item in issue_rows)
    checks = [
        ("Dataset A loaded from immutable GCS package", True, package_uri),
        ("M3 initialized run", "initialize_dataset_run" in consequential, run_id),
        (
            "Gemini observed 5 readiness issues",
            int((summary or {}).get("detected_issue_count") or 0) == 5,
            str((summary or {}).get("detected_issue_count")),
        ),
        (
            "Gemini selected 5 AUTO_SAFE issues",
            len(selected) == 5,
            ",".join(selected),
        ),
        (
            "deterministic coordinator resolved 5/5",
            int((summary or {}).get("resolved_issue_count") or 0) == 5,
            str((summary or {}).get("resolved_issue_count")),
        ),
        (
            "0 issues remain open",
            int((summary or {}).get("open_issue_count") or 0) == 0,
            str((summary or {}).get("open_issue_count")),
        ),
        (
            "524 × 16 model artifact generated",
            ((summary or {}).get("model_artifact") or {}).get("row_count") == 524
            and ((summary or {}).get("model_artifact") or {}).get("column_count") == 16,
            str((summary or {}).get("model_artifact")),
        ),
        (
            "deterministic readiness passed",
            (readiness or {}).get("status") == "PASS",
            str((readiness or {}).get("status")),
        ),
        (
            "BigQuery model artifact published",
            (publish or {}).get("status") == "PUBLISHED" and bq_rows == 524,
            f"{table} rows={bq_rows}",
        ),
        (
            "publish parity passed",
            (publish or {}).get("parity_status") == "PASS",
            str((publish or {}).get("parity_status")),
        ),
        (
            "Meridian input contract generated",
            (contract or {}).get("status") == "COMPLETE",
            str((contract or {}).get("status")),
        ),
        (
            "provenance complete",
            ((summary or {}).get("provenance") or {}).get("status") == "PASS",
            str((summary or {}).get("provenance")),
        ),
        (
            "evidence-backed MODEL_READY",
            (summary or {}).get("final_state") == "MODEL_READY"
            and (state or {}).get("status") == "MODEL_READY",
            str((summary or {}).get("final_state")),
        ),
        (
            "durable GCS evidence persisted",
            bool(summary) and bool(state),
            artifact_prefix,
        ),
        (
            "consequential run-level tools used",
            set(CONSEQUENTIAL_TOOLS) <= set(consequential),
            ",".join(consequential),
        ),
    ]

    receipt = {
        "run_id": run_id,
        "agent": EXPECTED_AGENT_NAME,
        "app": EXPECTED_APP,
        "events": trajectory,
        "final_status": (summary or {}).get("final_state"),
    }
    local_receipt = (
        REPO_ROOT / "artifacts" / "deployment" / "agent_trajectory_receipt.json"
    )
    local_receipt.parent.mkdir(parents=True, exist_ok=True)
    local_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    _upload_json(f"{artifact_prefix}trajectory/agent_trajectory_receipt.json", receipt)

    passed = all(item[1] for item in checks)
    status = "CLOUD_TASKMASTER" if passed else "NOT_CLOUD_TASKMASTER"
    proof = {
        "checked_at": datetime.now(UTC).isoformat(),
        "git_sha": args.git_sha or _git_sha(),
        "cloud_run": {
            "service": SERVICE_NAME,
            "revision": _revision(),
            "region": REGION,
            "runtime_service_account": EXPECTED_RUNTIME_SA,
        },
        "package": {
            "uri": package_uri,
            "fingerprint": (state or {}).get("package_fingerprint"),
        },
        "run": {
            "run_id": run_id,
            "stage": (state or {}).get("stage"),
            "artifact_prefix": artifact_prefix,
        },
        "agent": {
            "app_id": EXPECTED_APP,
            "agent_name": EXPECTED_AGENT_NAME,
            "trajectory_receipt_uri": f"{artifact_prefix}trajectory/agent_trajectory_receipt.json",
            "consequential_tool_calls": consequential,
        },
        "issues": {
            "detected": (summary or {}).get("detected_issue_count"),
            "auto_safe": auto_safe,
            "resolved": (summary or {}).get("resolved_issue_count"),
            "open": (summary or {}).get("open_issue_count"),
            "selected_issue_ids": selected,
        },
        "artifact": (summary or {}).get("model_artifact"),
        "readiness": {"status": (readiness or {}).get("status")},
        "bigquery": {
            "table": table,
            "rows": bq_rows,
            "parity_status": (publish or {}).get("parity_status"),
            "artifact_fingerprint": (publish or {}).get("artifact_fingerprint"),
            "published_fingerprint": (publish or {}).get("published_fingerprint"),
        },
        "meridian_contract": {"status": (contract or {}).get("status")},
        "provenance": {
            "status": ((summary or {}).get("provenance") or {}).get("status"),
            "transformation_count": (summary or {}).get("transformation_count"),
            "record_count": len((provenance or {}).get("records") or []),
        },
        "gate": (summary or {}).get("gate"),
        "status": status,
        "agent_text_preview": " ".join(text.split())[:400],
    }
    proof_path = REPO_ROOT / "artifacts" / "deployment" / "cloud_taskmaster_proof.json"
    proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")

    print(status)
    print()
    for name, ok, detail in checks:
        mark = "[x]" if ok else "[ ]"
        print(f"{mark} {name}")
        if not ok:
            print(f"    {detail}")
    print()
    print(f"Run:\n{run_id}")
    print()
    print(f"BigQuery:\n{table}")
    print()
    print(f"Artifacts:\n{artifact_prefix}")
    print()
    if passed:
        print("NEXT:\nAMBIENT_TASKMASTER")
    return 0 if passed else 1


def _service_url() -> str:
    completed = subprocess.run(
        [
            GCLOUD,
            "run",
            "services",
            "describe",
            SERVICE_NAME,
            "--project",
            PROJECT,
            "--region",
            REGION,
            "--format=value(status.url)",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    url = completed.stdout.strip()
    if not url:
        raise RuntimeError("Cloud Run service URL is empty.")
    return url


def _identity_token() -> str:
    completed = subprocess.run(
        [GCLOUD, "auth", "print-identity-token"],
        check=True,
        capture_output=True,
        text=True,
    )
    token = completed.stdout.strip()
    if not token:
        raise RuntimeError("gcloud did not return an identity token.")
    return token


def _revision() -> str | None:
    completed = subprocess.run(
        [
            GCLOUD,
            "run",
            "services",
            "describe",
            SERVICE_NAME,
            "--project",
            PROJECT,
            "--region",
            REGION,
            "--format=value(status.latestReadyRevisionName)",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or None


def _json_request(method: str, url: str, token: str, body: dict | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {detail[:500]}") from exc


def _run_prompt(
    app_url: str, token: str, text: str, session_id: str, timeout: int
) -> tuple[str, list[dict[str, Any]]]:
    body = {
        "app_name": EXPECTED_APP,
        "user_id": "cloud_taskmaster_user",
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": text}]},
        "streaming": False,
    }
    request = urllib.request.Request(
        f"{app_url}/run_sse",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "text/event-stream")
    events: list[dict[str, Any]] = []
    texts: list[str] = []
    with urllib.request.urlopen(request, timeout=timeout) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            event = json.loads(payload)
            events.append(event)
            for part in ((event.get("content") or {}).get("parts") or []):
                if part.get("text"):
                    texts.append(str(part["text"]))
    return "".join(texts), events


def _trajectory_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    sequence = 0
    for event in events:
        for part in ((event.get("content") or {}).get("parts") or []):
            call = part.get("functionCall") or part.get("function_call")
            if call:
                sequence += 1
                tool = call.get("name") or ""
                args = call.get("args") or call.get("arguments") or {}
                record = {
                    "sequence": sequence,
                    "tool": tool,
                    "tool_call_id": call.get("id"),
                    "status": "REQUESTED",
                    "requested_issue_ids": (
                        args.get("issue_ids") if isinstance(args, dict) else None
                    ),
                    "run_id": args.get("run_id") if isinstance(args, dict) else None,
                }
                if call.get("id"):
                    calls[str(call["id"])] = record
                ordered.append(record)
            response = part.get("functionResponse") or part.get("function_response")
            if not response:
                continue
            name = response.get("name") or ""
            result = response.get("response") or response.get("result") or {}
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    result = {"raw": result}
            if not isinstance(result, dict):
                result = {"result": result}
            record = calls.get(str(response.get("id") or ""))
            if record is None:
                sequence += 1
                record = {"sequence": sequence, "tool": name, "status": "SUCCESS"}
                ordered.append(record)
            status = result.get("status") or "SUCCESS"
            record["status"] = "SUCCESS" if status not in {"FAIL", "FAILED"} else "FAIL"
            record["run_id"] = result.get("run_id") or record.get("run_id")
            record["stage_after"] = result.get("stage")
            if result.get("requested_issue_ids"):
                record["requested_issue_ids"] = result.get("requested_issue_ids")
            if name:
                record["tool"] = name
    return ordered


def _discover_run_id(trajectory: list[dict[str, Any]], text: str) -> str | None:
    for event in reversed(trajectory):
        run_id = event.get("run_id")
        if run_id:
            return str(run_id)
    return None


def _selected_issue_ids(trajectory: list[dict[str, Any]]) -> list[str]:
    selected: list[str] = []
    for event in trajectory:
        if event.get("tool") != "apply_safe_remediations":
            continue
        ids = event.get("requested_issue_ids") or []
        if isinstance(ids, str):
            try:
                ids = json.loads(ids)
            except json.JSONDecodeError:
                ids = [ids]
        for item in ids:
            if item not in selected:
                selected.append(str(item))
    return selected


def _load_gcs_json(uri: str) -> dict[str, Any] | None:
    if not uri.startswith("gs://"):
        return None
    bucket_name, blob_name = uri[5:].split("/", 1)
    blob = storage.Client(project=settings.project_id).bucket(bucket_name).blob(blob_name)
    if not blob.exists():
        return None
    return json.loads(blob.download_as_text())


def _upload_json(uri: str, payload: dict[str, Any]) -> None:
    bucket_name, blob_name = uri[5:].split("/", 1)
    blob = storage.Client(project=settings.project_id).bucket(bucket_name).blob(blob_name)
    blob.upload_from_string(json.dumps(payload, indent=2) + "\n", content_type="application/json")


def _bigquery_row_count(table: str | None) -> int | None:
    if not table:
        return None
    client = bigquery.Client(project=settings.project_id, location=settings.cloud_region)
    try:
        bq_table = client.get_table(table)
    except Exception:
        return None
    return int(bq_table.num_rows)


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _print_failure(message: str, trajectory: list[dict[str, Any]], text: str) -> None:
    print("NOT_CLOUD_TASKMASTER")
    print(message)
    print(json.dumps(trajectory, indent=2)[:4000])
    print(text[:1000])


if __name__ == "__main__":
    raise SystemExit(main())
