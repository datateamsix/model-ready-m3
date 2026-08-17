"""Private Cloud Run smoke test for the already-deployed ADK API server.

Historical proof harness. The product ADK tool surface in this branch no longer
accepts package_uri or run_id arguments; this script talks to the deployed
revision, not an undeployed ExecutionContext bind. Do not deploy from this
mission.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
GCLOUD = "gcloud.cmd" if os.name == "nt" else "gcloud"
EXPECTED_RUNTIME_SA = "m3-runtime@modelready-m3.iam.gserviceaccount.com"
EXPECTED_APP = "app"
EXPECTED_AGENT_NAME = "modelready_m3"
SERVICE_NAME = "modelready-m3"
REGION = "us-central1"
PROJECT = "modelready-m3"

CLOUD_RUN_ENV = {
    "GOOGLE_CLOUD_PROJECT": PROJECT,
    "GOOGLE_CLOUD_LOCATION": "global",
    "GOOGLE_CLOUD_REGION": REGION,
    "GOOGLE_GENAI_USE_VERTEXAI": "true",
    "M3_GEMINI_MODEL": "gemini-2.5-flash",
    "M3_AGENT_NAME": EXPECTED_AGENT_NAME,
    "M3_RUNTIME_SA": EXPECTED_RUNTIME_SA,
    "MODELREADY_CLOUD_RUN_SERVICE": SERVICE_NAME,
    "MODELREADY_ORGANIZATION_ID": "music-center",
    "MODELREADY_WORKSPACE_ID": "mmm-demo",
    "MODELREADY_RAW_BUCKET": "modelready-m3-912257136465-raw",
    "MODELREADY_ARTIFACT_BUCKET": "modelready-m3-912257136465-artifacts",
    "MODELREADY_BQ_OPS_DATASET": "modelready_ops",
    "MODELREADY_BQ_EXPERIENCE_DATASET": "modelready_experience",
    "MODELREADY_BQ_MODELS_DATASET": "modelready_models",
    "MODELREADY_ENV": "demo",
    "MODELREADY_LOG_LEVEL": "INFO",
}

ROLE_PROMPT = (
    "Describe your role and the deterministic evidence required before you may "
    "claim MODEL_READY."
)
PROBE_PROMPT = (
    "Use the cloud_runtime_probe tool. Return its structured result and do not "
    "infer any missing values."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-url", default=None)
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--git-sha", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app_url = (args.app_url or _service_url()).rstrip("/")
    token = _identity_token(app_url)
    checks: list[tuple[str, bool, str]] = []

    unauth = _request_status(f"{app_url}/list-apps", token=None)
    checks.append(("unauthenticated callers rejected", unauth in {401, 403}, str(unauth)))

    apps = _json_request("GET", f"{app_url}/list-apps", token)
    app_ok = isinstance(apps, list) and EXPECTED_APP in apps
    checks.append(("private service reachable with identity token", app_ok, app_url))
    checks.append(("ADK app discovered", app_ok, str(apps)))

    session_id = f"cloud_test_session_{int(time.time())}"
    session = _json_request(
        "POST",
        f"{app_url}/apps/{EXPECTED_APP}/users/cloud_test_user/sessions/{session_id}",
        token,
        body={},
    )
    session_ok = isinstance(session, dict) and session.get("id") == session_id
    returned_id = session.get("id") if isinstance(session, dict) else session
    checks.append(("session created", session_ok, str(returned_id)))

    role_text, role_events = _run_prompt(app_url, token, ROLE_PROMPT, session_id)
    gemini_ok = bool(role_text.strip())
    checks.append(("Gemini response received", gemini_ok, _preview(role_text)))

    probe_text, probe_events = _run_prompt(app_url, token, PROBE_PROMPT, session_id)
    probe = _extract_probe(probe_events, probe_text)
    runtime_sa = (probe or {}).get("runtime", {}).get("service_account_email")
    checks.append(
        (
            "runtime service account",
            runtime_sa == EXPECTED_RUNTIME_SA,
            str(runtime_sa),
        )
    )
    probe_checks = (probe or {}).get("checks") or {}
    raw_ok = probe_checks.get("raw_bucket_access") == "PASS"
    checks.append(("raw GCS access", raw_ok, str(probe_checks.get("raw_bucket_access"))))
    checks.append(
        (
            "artifact GCS access",
            probe_checks.get("artifact_bucket_access") == "PASS",
            str(probe_checks.get("artifact_bucket_access")),
        )
    )
    checks.append(
        (
            "BigQuery job access",
            probe_checks.get("bigquery_job_access") == "PASS",
            str(probe_checks.get("bigquery_job_access")),
        )
    )

    print("MODELREADY CLOUD RUNTIME CHECK")
    print()
    for name, passed, detail in checks:
        mark = "[x]" if passed else "[ ]"
        print(f"{mark} {name}: {detail}")
    print()
    alive = all(passed for _name, passed, _detail in checks)
    print("CLOUD_ALIVE" if alive else "NOT_CLOUD_ALIVE")
    if args.write_evidence:
        _write_evidence(
            app_url=app_url,
            git_sha=args.git_sha or _git_sha(),
            apps=apps,
            session_ok=session_ok,
            gemini_ok=bool(role_text),
            probe=probe,
            unauth_status=unauth,
            role_events=role_events,
        )
    return 0 if alive else 1


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


def _identity_token(app_url: str) -> str:
    del app_url  # User accounts cannot set --audiences; Cloud Run accepts the user ID token.
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


def _request_status(url: str, token: str | None) -> int:
    request = urllib.request.Request(url, method="GET")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


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
    app_url: str, token: str, text: str, session_id: str
) -> tuple[str, list[dict[str, Any]]]:
    body = {
        "app_name": EXPECTED_APP,
        "user_id": "cloud_test_user",
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
    with urllib.request.urlopen(request, timeout=180) as response:
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


def _extract_probe(events: list[dict[str, Any]], text: str) -> dict[str, Any] | None:
    for event in events:
        for part in ((event.get("content") or {}).get("parts") or []):
            response = part.get("functionResponse") or part.get("function_response")
            if not response:
                continue
            name = response.get("name") or ""
            if name != "cloud_runtime_probe":
                continue
            result = response.get("response") or response.get("result")
            if isinstance(result, dict):
                return result
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        parsed = json.loads(text[start:end])
        if isinstance(parsed, dict) and "checks" in parsed:
            return parsed
    except (ValueError, json.JSONDecodeError):
        return None
    return None


def _write_evidence(
    *,
    app_url: str,
    git_sha: str,
    apps: Any,
    session_ok: bool,
    gemini_ok: bool,
    probe: dict[str, Any] | None,
    unauth_status: int,
    role_events: list[dict[str, Any]],
) -> None:
    deployer = subprocess.run(
        [GCLOUD, "config", "get-value", "account"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    describe = subprocess.run(
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
            "--format=json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    service = json.loads(describe.stdout)
    spec = ((service.get("spec") or {}).get("template") or {}).get("spec") or {}
    metadata = ((service.get("spec") or {}).get("template") or {}).get("metadata") or {}
    configured_sa = spec.get("serviceAccountName")
    metadata_sa = (probe or {}).get("runtime", {}).get("service_account_email")
    env_list = spec.get("containers", [{}])[0].get("env") or []
    env = {item.get("name"): item.get("value") for item in env_list if "value" in item}
    checks = (probe or {}).get("checks") or {}
    evidence = {
        "checked_at": datetime.now(UTC).isoformat(),
        "git_sha": git_sha,
        "cloud_run": {
            "service": SERVICE_NAME,
            "revision": metadata.get("name") or (probe or {}).get("runtime", {}).get("revision"),
            "region": REGION,
            "url": app_url,
            "private": unauth_status in {401, 403},
        },
        "deployer_identity": deployer,
        "runtime_identity": {
            "configured_service_account": configured_sa,
            "metadata_service_account": metadata_sa,
            "match": bool(configured_sa) and configured_sa == metadata_sa,
        },
        "vertex": {
            "location": env.get("GOOGLE_CLOUD_LOCATION"),
            "model": env.get("M3_GEMINI_MODEL"),
            "response_received": gemini_ok,
        },
        "gcs": {
            "raw_bucket_access": checks.get("raw_bucket_access") == "PASS",
            "artifact_bucket_access": checks.get("artifact_bucket_access") == "PASS",
        },
        "bigquery": {"job_access": checks.get("bigquery_job_access") == "PASS"},
        "adk": {
            "app": EXPECTED_APP,
            "agent_name": EXPECTED_AGENT_NAME,
            "list_apps": apps,
            "session_created": session_ok,
            "agent_response_received": gemini_ok,
            "event_count": len(role_events),
        },
        "security": {
            "GOOGLE_APPLICATION_CREDENTIALS": env.get("GOOGLE_APPLICATION_CREDENTIALS"),
            "GOOGLE_API_KEY": env.get("GOOGLE_API_KEY"),
            "unauthenticated_status": unauth_status,
        },
        "status": "CLOUD_ALIVE"
        if (
            unauth_status in {401, 403}
            and configured_sa == EXPECTED_RUNTIME_SA
            and metadata_sa == EXPECTED_RUNTIME_SA
            and env.get("GOOGLE_CLOUD_LOCATION") == "global"
            and env.get("GOOGLE_APPLICATION_CREDENTIALS") is None
            and env.get("GOOGLE_API_KEY") is None
            and gemini_ok
            and checks.get("identity") == "PASS"
            and checks.get("raw_bucket_access") == "PASS"
            and checks.get("artifact_bucket_access") == "PASS"
            and checks.get("bigquery_job_access") == "PASS"
        )
        else "NOT_CLOUD_ALIVE",
    }
    path = REPO_ROOT / "artifacts" / "deployment" / "cloud_runtime_proof.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _preview(text: str, limit: int = 80) -> str:
    compact = " ".join(text.split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


if __name__ == "__main__":
    raise SystemExit(main())
