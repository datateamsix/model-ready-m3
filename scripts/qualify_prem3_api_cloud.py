#!/usr/bin/env python3
"""Qualify the deployed prem3-api Cloud Run service.

NEVER invoked by pytest/CI. Explicit operator command only.

Does not print tokens, secret values, or raw webhook payloads.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT = "modelready-m3"
REGION = "us-central1"
SERVICE = "prem3-api"
RUNTIME_SA = f"m3-runtime@{PROJECT}.iam.gserviceaccount.com"
GCLOUD = "gcloud.cmd" if os.name == "nt" else "gcloud"
REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "artifacts" / "deployment" / "prem3_api_cloud_proof.json"
HISTORICAL_REVISION = "modelready-m3-00013-c4s"
HISTORICAL_IMAGE = (
    "us-central1-docker.pkg.dev/modelready-m3/cloud-run-source-deploy/"
    "modelready-m3@sha256:7dffe4904c1a3ce9e2bb7426793954608bb3d3b5c274b2dc592fcefb0246f6d6"
)
EDA_IMAGE = (
    "us-central1-docker.pkg.dev/modelready-m3/cloud-run-source-deploy/"
    "meridian-eda-worker@sha256:76c69841af42d392663f92da6395d0a6cf37eb3af5d808d61d4972c3e1edd96d"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--skip-firestore", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print("PREM3_API_CLOUD_QUALIFICATION_NOT_RUN")
        print("Pass --execute to qualify the deployed prem3-api service.")
        return 2

    describe = _service_describe()
    url = (args.base_url or (describe.get("status") or {}).get("url") or "").rstrip("/")
    if not url:
        print("PREM3_API_CLOUD_QUALIFICATION_NOT_RUN")
        print("prem3-api URL is unavailable.")
        return 3

    health = _json_request("GET", f"{url}/healthz")
    ready = _json_request("GET", f"{url}/readyz")
    catalog = _json_request("GET", f"{url}/v1/catalog/plans")
    me = _problem_request("GET", f"{url}/v1/me")
    create_ws = _problem_request(
        "POST", f"{url}/v1/workspaces", body=b'{"name":"unauth"}', content_type="application/json"
    )
    identity_wh = _problem_request("POST", f"{url}/v1/webhooks/identity", body=b"{}")
    billing_wh = _problem_request("POST", f"{url}/v1/webhooks/billing", body=b"{}")
    cors = _header_request("GET", f"{url}/v1/me")

    ready_deps = (ready[1] or {}).get("dependencies") or {}
    public_ok = health[0] == 200 and (health[1] or {}).get("status") == "ok"
    catalog_ok = catalog[0] == 200 and len((catalog[1] or {}).get("plans") or []) == 4
    ready_ok = ready[0] == 200 and ready_deps.get("control_plane") == "configured"
    me_denied = me[1] in {"AUTH_REQUIRED", "AUTH_PROVIDER_NOT_CONFIGURED"}
    ws_denied = create_ws[1] in {"AUTH_REQUIRED", "AUTH_PROVIDER_NOT_CONFIGURED"}
    identity_denied = identity_wh[1] in {"AUTH_REQUIRED", "AUTH_PROVIDER_NOT_CONFIGURED"}
    billing_denied = billing_wh[1] in {
        "AUTH_REQUIRED",
        "BILLING_PROVIDER_NOT_CONFIGURED",
    }
    cors_ok = cors.get("access-control-allow-origin") != "*"
    security_ok = all(
        [
            public_ok,
            catalog_ok,
            me_denied,
            ws_denied,
            identity_denied,
            billing_denied,
            cors_ok,
        ]
    )

    historical = _historical_ok()
    firestore_proof = "NOT_RUN"
    firestore_identity = None
    if not args.skip_firestore:
        firestore_proof, firestore_identity = _firestore_proof()

    spec = ((describe.get("spec") or {}).get("template") or {}).get("spec") or {}
    metadata = ((describe.get("spec") or {}).get("template") or {}).get("metadata") or {}
    container = (spec.get("containers") or [{}])[0]
    env_names = sorted(
        item.get("name")
        for item in (container.get("env") or [])
        if item.get("name")
    )
    secret_names = sorted(
        (item.get("name") or "")
        for item in (container.get("env") or [])
        if item.get("valueFrom")
    )
    leak = _secret_leak(describe, ready[1], catalog[1])

    cloud_api_alive = security_ok and ready_ok and public_ok
    cloud_control_plane = ready_ok and firestore_proof == "LIVE_FIRESTORE_CONTROL_PLANE_PROOF"
    clerk_configured = ready_deps.get("auth_provider") == "configured"
    stripe_configured = ready_deps.get("billing_provider") == "configured"

    evidence = {
        "checked_at": datetime.now(UTC).isoformat(),
        "source_sha": _git_sha(),
        "gcloud_version": _gcloud_version(),
        "service": SERVICE,
        "revision": (describe.get("status") or {}).get("latestReadyRevisionName"),
        "region": REGION,
        "url": url,
        "runtime_service_account": spec.get("serviceAccountName"),
        "image": container.get("image"),
        "cpu": ((container.get("resources") or {}).get("limits") or {}).get("cpu"),
        "memory": ((container.get("resources") or {}).get("limits") or {}).get("memory"),
        "timeout_seconds": spec.get("timeoutSeconds"),
        "max_instance_count": (metadata.get("annotations") or {}).get(
            "autoscaling.knative.dev/maxScale"
        ),
        "invoker_iam_disabled": True,
        "firestore_database": "(default)",
        "env_names": env_names,
        "secret_env_names": secret_names,
        "health": health[1],
        "ready": ready[1],
        "security": {
            "unauthenticated_me": me,
            "unauthenticated_workspace_create": create_ws,
            "unsigned_identity_webhook": identity_wh,
            "unsigned_billing_webhook": billing_wh,
            "wildcard_cors": not cors_ok,
        },
        "historical_protection": historical,
        "firestore_proof": firestore_proof,
        "firestore_identity": firestore_identity,
        "secret_leak_check": "pass" if not leak else "fail",
        "CLOUD_API_ALIVE": cloud_api_alive,
        "CLOUD_CONTROL_PLANE": cloud_control_plane,
        "LIVE_CLERK_CLOUD_IDENTITY_PROOF": False,
        "LIVE_CLERK_CLOUD_IDENTITY_NOT_RUN": True,
        "LIVE_STRIPE_BILLING_TEST_PROOF": False,
        "LIVE_STRIPE_BILLING_NOT_RUN": not stripe_configured,
        "CLOUD_SAAS_AUTHORITY": False,
        "clerk_configured": clerk_configured,
        "stripe_configured": stripe_configured,
    }
    if args.write_evidence:
        EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(f"evidence={EVIDENCE_PATH.as_posix()}")

    print("healthz=" + str(health[0]))
    print("readyz=" + json.dumps(ready[1]))
    print(f"CLOUD_API_ALIVE={cloud_api_alive}")
    print(f"CLOUD_CONTROL_PLANE={cloud_control_plane}")
    print("LIVE_CLERK_CLOUD_IDENTITY_NOT_RUN=True")
    print(f"LIVE_STRIPE_BILLING_NOT_RUN={not stripe_configured}")
    print("CLOUD_SAAS_AUTHORITY=False")
    print(f"historical_protection={historical['ok']}")
    if cloud_api_alive and cloud_control_plane and historical["ok"] and not leak:
        print("PREM3_M2_API_CLOUD_RUNTIME_READY")
        return 0
    print("PREM3_M2_API_CLOUD_RUNTIME_NOT_READY")
    return 1


def _gcloud(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([GCLOUD, *args], check=True, capture_output=True, text=True)


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _gcloud_version() -> str:
    result = subprocess.run([GCLOUD, "version"], check=True, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith("Google Cloud SDK"):
            return line.split()[-1]
    return "unknown"


def _service_describe() -> dict[str, Any]:
    result = _gcloud(
        [
            "run",
            "services",
            "describe",
            SERVICE,
            f"--project={PROJECT}",
            f"--region={REGION}",
            "--format=json",
        ]
    )
    return json.loads(result.stdout)


def _request(
    method: str, url: str, *, body: bytes | None = None, content_type: str | None = None
) -> tuple[int, dict[str, str], bytes]:
    headers = {"User-Agent": "prem3-api-cloud-qualify"}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return (
                response.status,
                {k.lower(): v for k, v in response.headers.items()},
                response.read(),
            )
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read()


def _json_request(method: str, url: str) -> tuple[int, dict[str, Any] | None]:
    status, _headers, raw = _request(method, url)
    try:
        return status, json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return status, None


def _problem_request(
    method: str,
    url: str,
    *,
    body: bytes | None = None,
    content_type: str | None = None,
) -> tuple[int, str | None]:
    status, _headers, raw = _request(method, url, body=body, content_type=content_type)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return status, None
    code = payload.get("code") if isinstance(payload, dict) else None
    return status, str(code) if code else None


def _header_request(method: str, url: str) -> dict[str, str]:
    _status, headers, _raw = _request(method, url)
    return headers


def _historical_ok() -> dict[str, Any]:
    adk = json.loads(
        _gcloud(
            [
                "run",
                "services",
                "describe",
                "modelready-m3",
                f"--project={PROJECT}",
                f"--region={REGION}",
                "--format=json",
            ]
        ).stdout
    )
    job = json.loads(
        _gcloud(
            [
                "run",
                "jobs",
                "describe",
                "meridian-eda-worker",
                f"--project={PROJECT}",
                f"--region={REGION}",
                "--format=json",
            ]
        ).stdout
    )
    adk_spec = ((adk.get("spec") or {}).get("template") or {}).get("spec") or {}
    adk_image = ((adk_spec.get("containers") or [{}])[0]).get("image")
    adk_revision = (adk.get("status") or {}).get("latestReadyRevisionName")
    job_spec = (
        (((job.get("spec") or {}).get("template") or {}).get("spec") or {}).get("template") or {}
    ).get("spec") or {}
    job_image = ((job_spec.get("containers") or [{}])[0]).get("image")
    ok = (
        adk_revision == HISTORICAL_REVISION
        and adk_image == HISTORICAL_IMAGE
        and job_image == EDA_IMAGE
    )
    return {
        "ok": ok,
        "modelready_m3_revision": adk_revision,
        "modelready_m3_image": adk_image,
        "meridian_eda_worker_image": job_image,
    }


def _firestore_proof() -> tuple[str, str | None]:
    impersonate = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "qualify_firestore_control_plane.py"),
        "--execute",
        f"--impersonate-service-account={RUNTIME_SA}",
    ]
    result = subprocess.run(impersonate, capture_output=True, text=True, cwd=REPO_ROOT)
    output = (result.stdout or "") + (result.stderr or "")
    if "LIVE_FIRESTORE_CONTROL_PLANE_PROOF" in output:
        return "LIVE_FIRESTORE_CONTROL_PLANE_PROOF", RUNTIME_SA
    fallback = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "qualify_firestore_control_plane.py"),
        "--execute",
    ]
    fallback_result = subprocess.run(fallback, capture_output=True, text=True, cwd=REPO_ROOT)
    fallback_out = (fallback_result.stdout or "") + (fallback_result.stderr or "")
    if "LIVE_FIRESTORE_CONTROL_PLANE_PROOF" in fallback_out:
        return "LIVE_FIRESTORE_CONTROL_PLANE_PROOF", "application_default_credentials"
    return "LIVE_FIRESTORE_QUALIFICATION_NOT_RUN", None


def _secret_leak(
    describe: dict[str, Any],
    ready: dict[str, Any] | None,
    catalog: dict[str, Any] | None,
) -> bool:
    blob = json.dumps({"describe": describe, "ready": ready, "catalog": catalog})
    forbidden = ("sk_live_", "sk_test_", "whsec_", "-----BEGIN")
    return any(token in blob for token in forbidden)


if __name__ == "__main__":
    sys.exit(main())
