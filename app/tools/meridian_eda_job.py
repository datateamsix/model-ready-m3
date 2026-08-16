"""Invoke the isolated Meridian EDA Cloud Run Job. Does not import google-meridian."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from google.api_core import exceptions as google_exceptions
from google.cloud import run_v2

from app.config import settings
from app.core.errors import ValidationBlockedError
from app.core.meridian_eda_contracts import (
    DEFAULT_PRIOR_N_DRAW,
    DEFAULT_PRIOR_SEED,
    PINNED_GOOGLE_MERIDIAN,
    MeridianEDAReceipt,
    MeridianInputMapping,
    canonical_eda_config,
)
from app.integrations.gcs import download_file, upload_file
from app.tools.artifacts import write_json_artifact
from app.tools.meridian_eda_gate import build_meridian_refusal_feedback

_POLL_SECONDS = 10
_START_RPC_TIMEOUT_SECONDS = 120.0


def meridian_eda_job_configured() -> bool:
    return bool((settings.eda_job or "").strip())


def invoke_meridian_eda_job(
    *,
    run_id: str,
    mapping: MeridianInputMapping,
    output_dir: Path,
    source_endpoint: str,
    content_fingerprint: str,
    html_uri: str | None,
    config_uri: str | None,
    request_uri: str | None,
    receipt_uri: str | None,
    config_fp: str,
    idem_key: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    if not meridian_eda_job_configured():
        raise ValidationBlockedError("MODELREADY_EDA_JOB is not configured.")
    if not request_uri or not html_uri or not config_uri or not receipt_uri:
        raise ValidationBlockedError(
            "Isolated Meridian EDA job requires GCS request, HTML, config, and receipt URIs."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    request = {
        "run_id": run_id,
        "source_endpoint": source_endpoint,
        "content_fingerprint": content_fingerprint,
        "mapping": mapping.model_dump(mode="json"),
        "n_draws_prior": DEFAULT_PRIOR_N_DRAW,
        "seed": DEFAULT_PRIOR_SEED,
        "html_uri": html_uri,
        "config_uri": config_uri,
        "receipt_uri": receipt_uri,
        "eda_config_fingerprint": config_fp,
        "idempotency_key": idem_key,
        "pinned_google_meridian": PINNED_GOOGLE_MERIDIAN,
    }
    request_path = output_dir / "meridian_eda_request.json"
    write_json_artifact(request_path, request)
    upload_file(request_path, request_uri)
    try:
        execution_name = _run_job(
            request_uri=request_uri, timeout_seconds=timeout_seconds
        )
    except ValidationBlockedError as exc:
        _persist_job_refusal(
            run_id=run_id,
            output_dir=output_dir,
            receipt_uri=receipt_uri,
            error=str(exc),
        )
        raise
    html_path = output_dir / "meridian_eda_report.html"
    config_path = output_dir / "meridian_eda_config.json"
    receipt_path = output_dir / "meridian_eda_receipt.json"
    download_file(html_uri, html_path)
    download_file(config_uri, config_path)
    download_file(receipt_uri, receipt_path)
    if not html_path.is_file() or html_path.stat().st_size <= 0:
        raise ValidationBlockedError("Isolated Meridian EDA job did not persist the HTML report.")
    if not receipt_path.is_file() or receipt_path.stat().st_size <= 0:
        raise ValidationBlockedError(
            "Isolated Meridian EDA job succeeded but the EDA receipt is missing."
        )
    receipt = MeridianEDAReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return {
        "html_path": str(html_path),
        "config": {**canonical_eda_config(mapping), **config},
        "receipt": receipt,
        "meridian_version": str((receipt.meridian or {}).get("version") or PINNED_GOOGLE_MERIDIAN),
        "python_version": str((receipt.meridian or {}).get("python_version") or ""),
        "backend": str((receipt.meridian or {}).get("backend") or "cpu"),
        "prior_context": receipt.prior_context,
        "execution_name": execution_name,
    }


def _run_job(*, request_uri: str, timeout_seconds: int) -> str:
    project = settings.project_id
    region = settings.cloud_region
    job = (settings.eda_job or "").strip()
    if not project or not region or not job:
        raise ValidationBlockedError("Meridian EDA job project, region, or name is missing.")
    job_name = f"projects/{project}/locations/{region}/jobs/{job}"
    client = run_v2.JobsClient()
    start_error: Exception | None = None
    execution_name = ""
    try:
        operation = client.run_job(
            request=run_v2.RunJobRequest(
                name=job_name,
                overrides=run_v2.RunJobRequest.Overrides(
                    container_overrides=[
                        run_v2.RunJobRequest.Overrides.ContainerOverride(
                            env=[
                                run_v2.EnvVar(name="MERIDIAN_EDA_REQUEST_URI", value=request_uri),
                            ]
                        )
                    ]
                ),
            ),
            timeout=_START_RPC_TIMEOUT_SECONDS,
        )
        metadata = getattr(operation, "metadata", None)
        execution_name = str(getattr(metadata, "name", "") or "")
    except (
        google_exceptions.GoogleAPICallError,
        TimeoutError,
        google_exceptions.RetryError,
    ) as exc:
        start_error = exc
    if not execution_name:
        execution_name = _latest_execution_name(job_name)
    if not execution_name:
        raise ValidationBlockedError(
            "Isolated Meridian EDA Cloud Run Job did not start: "
            f"{start_error or 'missing execution name'}"
        )
    _poll_execution(execution_name, timeout_seconds=timeout_seconds)
    return execution_name


def _latest_execution_name(job_name: str) -> str:
    client = run_v2.ExecutionsClient()
    newest: Any = None
    for item in client.list_executions(parent=job_name):
        newest = item
        break
    return str(getattr(newest, "name", "") or "")


def _poll_execution(execution_name: str, *, timeout_seconds: int) -> None:
    client = run_v2.ExecutionsClient()
    deadline = time.monotonic() + max(timeout_seconds, _POLL_SECONDS)
    last: Any = None
    while time.monotonic() < deadline:
        last = client.get_execution(name=execution_name)
        succeeded = int(getattr(last, "succeeded_count", 0) or 0)
        failed = int(getattr(last, "failed_count", 0) or 0)
        cancelled = int(getattr(last, "cancelled_count", 0) or 0)
        if succeeded >= 1:
            return
        if failed or cancelled:
            raise ValidationBlockedError(
                "Isolated Meridian EDA Cloud Run Job failed: "
                f"name={execution_name} failed={failed} cancelled={cancelled}"
            )
        time.sleep(_POLL_SECONDS)
    raise ValidationBlockedError(
        "Isolated Meridian EDA Cloud Run Job timed out: "
        f"name={execution_name} last={getattr(last, 'name', execution_name)}"
    )


def _persist_job_refusal(
    *,
    run_id: str,
    output_dir: Path,
    receipt_uri: str,
    error: str,
) -> None:
    official = error
    fail_uri = receipt_uri.replace("meridian_eda_receipt.json", "meridian_eda_worker_fail.json")
    fail_path = output_dir / "meridian_eda_worker_fail.json"
    try:
        download_file(fail_uri, fail_path)
        payload = json.loads(fail_path.read_text(encoding="utf-8"))
        official = str(payload.get("error") or error)
    except Exception:
        official = error
    feedback = build_meridian_refusal_feedback(run_id=run_id, official_message=official)
    write_json_artifact(
        output_dir / "meridian_user_feedback.json", feedback.model_dump(mode="json")
    )
