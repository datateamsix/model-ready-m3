"""Cloud Run Job entrypoint for official google-meridian pre-modeling EDA.

This process is the only production runtime that installs google-meridian.
It must not import the ADK agent, sample_posterior, or fit Meridian.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from app.core.contracts import utc_now
from app.core.errors import ValidationBlockedError
from app.core.meridian_eda_contracts import (
    PINNED_GOOGLE_MERIDIAN,
    MeridianEDAPriorContext,
    MeridianInputMapping,
    canonical_eda_config,
    eda_config_fingerprint,
    eda_idempotency_key,
)
from app.integrations.bigquery import get_bigquery_client
from app.integrations.gcs import download_file, upload_file
from app.tools.artifacts import write_json_artifact
from app.tools.bigquery_publish import read_bigquery_table
from app.tools.meridian_eda_runtime import run_official_meridian_eda
from app.tools.meridian_eda_serialize import serialize_outcomes
from app.tools.model_consumption import fingerprint_frame
from app.tools.model_frame import coerce_model_frame_types


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help"}:
        print(
            "usage: MERIDIAN_EDA_REQUEST_URI=gs://... "
            "python -m app.tools.meridian_eda_worker\n"
            "Cloud Run Job entrypoint for official Meridian pre-modeling EDA.\n"
            "Official google-meridian has no supported standalone CLI.\n"
            "This process calls run_official_meridian_eda only.\n"
            "Required request keys: run_id, source_endpoint, content_fingerprint, "
            "mapping, html_uri, config_uri, receipt_uri, eda_config_fingerprint, "
            "idempotency_key\n"
            "Forbidden: sample_posterior, model fitting, budget optimization."
        )
        return 0
    request_uri = (os.environ.get("MERIDIAN_EDA_REQUEST_URI") or "").strip()
    if not request_uri:
        print("MERIDIAN_EDA_REQUEST_URI is required", file=sys.stderr)
        return 2
    work = Path("/tmp/meridian-eda")
    work.mkdir(parents=True, exist_ok=True)
    request_path = work / "request.json"
    try:
        download_file(request_uri, request_path)
        request = json.loads(request_path.read_text(encoding="utf-8"))
        _execute(request, work)
        return 0
    except Exception as exc:
        failure = {
            "status": "FAIL",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        failure_path = work / "meridian_eda_worker_fail.json"
        write_json_artifact(failure_path, failure)
        receipt_uri = None
        try:
            payload = json.loads(request_path.read_text(encoding="utf-8"))
            receipt_uri = payload.get("receipt_uri")
        except Exception:
            receipt_uri = None
        if receipt_uri:
            try:
                upload_file(failure_path, str(receipt_uri).replace(
                    "meridian_eda_receipt.json", "meridian_eda_worker_fail.json"
                ))
            except Exception:
                pass
        print(str(exc), file=sys.stderr)
        traceback.print_exc()
        return 1


def _execute(request: dict[str, Any], work: Path) -> None:
    mapping = MeridianInputMapping.model_validate(request["mapping"])
    run_id = str(request["run_id"])
    source = str(request["source_endpoint"])
    expected_fp = str(request["content_fingerprint"])
    html_uri = str(request["html_uri"])
    config_uri = str(request["config_uri"])
    receipt_uri = str(request["receipt_uri"])
    expected_config_fp = str(request["eda_config_fingerprint"])
    expected_key = str(request["idempotency_key"])
    output = work / "eda"
    output.mkdir(parents=True, exist_ok=True)
    frame = coerce_model_frame_types(read_bigquery_table(source, client=get_bigquery_client()))
    actual_fp = fingerprint_frame(frame)
    if actual_fp != expected_fp:
        raise ValidationBlockedError(
            "EDA worker fingerprint mismatch: "
            f"expected={expected_fp} actual={actual_fp}"
        )
    config_fp = eda_config_fingerprint(mapping)
    if config_fp != expected_config_fp:
        raise ValidationBlockedError(
            "EDA worker config fingerprint mismatch: "
            f"expected={expected_config_fp} actual={config_fp}"
        )
    idem_key = eda_idempotency_key(
        run_id=run_id,
        model_input_fingerprint=actual_fp,
        meridian_version=PINNED_GOOGLE_MERIDIAN,
        eda_config_fingerprint_value=config_fp,
    )
    if idem_key != expected_key:
        raise ValidationBlockedError(
            "EDA worker idempotency key mismatch: "
            f"expected={expected_key} actual={idem_key}"
        )
    started = utc_now()
    raw = run_official_meridian_eda(
        frame=frame,
        mapping=mapping,
        output_dir=output,
        n_draws_prior=int(request.get("n_draws_prior", 500)),
        seed=int(request.get("seed", 0)),
    )
    completed = utc_now()
    if str(raw["meridian_version"]) != PINNED_GOOGLE_MERIDIAN:
        raise ValidationBlockedError(
            "EDA worker meridian_version is not pinned: "
            f"expected={PINNED_GOOGLE_MERIDIAN} actual={raw['meridian_version']}"
        )
    prior = raw["prior_context"]
    if isinstance(prior, dict):
        prior = MeridianEDAPriorContext.model_validate(prior)
    receipt = serialize_outcomes(
        raw["outcomes"],
        run_id=run_id,
        source={
            "bigquery_endpoint": source,
            "content_fingerprint": actual_fp,
            "model_scope": mapping.model_scope,
        },
        meridian={
            "version": raw["meridian_version"],
            "backend": raw["backend"],
            "python_version": raw["python_version"],
            "pinned": PINNED_GOOGLE_MERIDIAN,
        },
        prior_context=prior,
        html_report_uri=html_uri,
        eda_config_uri=config_uri,
        started_at=started,
        completed_at=completed,
        duration_seconds=round((completed - started).total_seconds(), 3),
        model_input_fingerprint=actual_fp,
        eda_config_fingerprint=config_fp,
        idempotency_key=idem_key,
        model_spec=(raw.get("config") or {}).get("model_spec"),
        compatibility_event=(
            raw.get("compatibility_event")
            or (raw.get("config") or {}).get("compatibility_event")
        ),
    )
    html_path = Path(raw["html_path"])
    config_path = output / "meridian_eda_config.json"
    receipt_path = output / "meridian_eda_receipt.json"
    write_json_artifact(config_path, {**canonical_eda_config(mapping), **raw["config"]})
    write_json_artifact(receipt_path, receipt.model_dump(mode="json"))
    upload_file(html_path, html_uri)
    upload_file(config_path, config_uri)
    upload_file(receipt_path, receipt_uri)


if __name__ == "__main__":
    raise SystemExit(main())
