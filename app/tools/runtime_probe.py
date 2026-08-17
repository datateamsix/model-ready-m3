"""Read-only Cloud Run identity and resource probe. Not part of Map/Mend/Prove."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import Any

from google.cloud import storage

from app.config import settings
from app.integrations.bigquery import get_bigquery_client
from app.mel.promote import active_domain_view_meta

_METADATA_ROOT = "http://metadata.google.internal/computeMetadata/v1"
_SECRET_KEY_FRAGMENTS = (
    "token",
    "credential",
    "secret",
    "authorization",
    "api_key",
    "passwd",
    "password",
)


def cloud_runtime_probe() -> dict[str, Any]:
    """Diagnostic, read-only runtime proof. Never returns tokens or secrets."""
    metadata = _read_metadata()
    if os.environ.get("K_SERVICE"):
        environment = "cloud_run"
    elif metadata["available"]:
        environment = "cloud"
    else:
        environment = "local"
    service_account_email = metadata["service_account_email"]
    project_id = metadata["project_id"] or settings.project_id
    expected_sa = (settings.runtime_sa or "").strip()
    identity = (
        "PASS"
        if service_account_email
        and expected_sa
        and service_account_email == expected_sa
        else "FAIL"
    )
    raw_access, raw_detail = _probe_gcs(settings.raw_bucket)
    artifact_access, artifact_detail = _probe_gcs(settings.artifact_bucket)
    bq_access, bq_detail = _probe_bigquery()
    domain_view = _probe_domain_view()
    checks = {
        "identity": identity,
        "raw_bucket_access": raw_access,
        "artifact_bucket_access": artifact_access,
        "bigquery_job_access": bq_access,
        "domain_view": domain_view["status"],
    }
    status = "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL"
    payload = {
        "status": status,
        "runtime": {
            "environment": environment,
            "service": os.environ.get("K_SERVICE"),
            "revision": os.environ.get("K_REVISION"),
            "configuration": os.environ.get("K_CONFIGURATION"),
            "project_id": project_id,
            "service_account_email": service_account_email,
        },
        "configuration": {
            "vertex_location": settings.vertex_location,
            "cloud_region": settings.cloud_region,
            "gemini_model": settings.gemini_model,
        },
        "checks": checks,
        "details": {
            "identity_expected": expected_sa or None,
            "raw_bucket": settings.raw_bucket,
            "raw_bucket_detail": raw_detail,
            "artifact_bucket": settings.artifact_bucket,
            "artifact_bucket_detail": artifact_detail,
            "bigquery_detail": bq_detail,
            "domain_view": domain_view,
        },
    }
    return strip_secrets(payload)


def strip_secrets(value: Any) -> Any:
    """Drop credential-like keys from a JSON-safe structure."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
                continue
            cleaned[str(key)] = strip_secrets(item)
        return cleaned
    if isinstance(value, list):
        return [strip_secrets(item) for item in value]
    return value


def _read_metadata() -> dict[str, Any]:
    project_id = _metadata_get("project/project-id")
    email = _metadata_get("instance/service-accounts/default/email")
    return {
        "available": bool(project_id or email),
        "project_id": project_id,
        "service_account_email": email,
    }


def _metadata_get(relative_path: str) -> str | None:
    if "token" in relative_path.lower() or "identity" in relative_path.lower():
        return None
    request = urllib.request.Request(
        f"{_METADATA_ROOT}/{relative_path}",
        headers={"Metadata-Flavor": "Google"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=0.4) as response:
            return response.read().decode("utf-8").strip() or None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def _probe_gcs(bucket_name: str | None) -> tuple[str, str]:
    if not bucket_name:
        return "FAIL", "bucket not configured"
    try:
        client = storage.Client(project=settings.project_id)
        iterator = client.list_blobs(bucket_name, max_results=1)
        next(iter(iterator), None)
        return "PASS", "list_blobs max_results=1 succeeded"
    except Exception as exc:
        return "FAIL", f"{type(exc).__name__}: {exc}"


def _probe_domain_view() -> dict[str, Any]:
    try:
        meta = active_domain_view_meta()
        return {"status": "PASS", **meta}
    except Exception as exc:
        return {
            "status": "FAIL",
            "source": "unavailable",
            "detail": f"{type(exc).__name__}: {exc}",
        }


def _probe_bigquery() -> tuple[str, str]:
    try:
        client = get_bigquery_client()
        job = client.query("SELECT 1 AS ok", location=settings.cloud_region)
        rows = list(job.result(timeout=30))
        if not rows or int(rows[0]["ok"]) != 1:
            return "FAIL", "SELECT 1 did not return 1"
        dataset_id = f"{settings.project_id}.{settings.bq_models_dataset}"
        client.get_dataset(dataset_id)
        return "PASS", f"SELECT 1 succeeded; dataset {dataset_id} resolved"
    except Exception as exc:
        return "FAIL", f"{type(exc).__name__}: {exc}"


CLOUD_RUNTIME_DIAGNOSTIC_TOOLS = [cloud_runtime_probe]
