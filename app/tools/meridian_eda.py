"""Run official Meridian pre-modeling EDA against a confirmed BigQuery model input."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.contracts import utc_now
from app.core.errors import ValidationBlockedError
from app.core.meridian_eda_contracts import (
    PINNED_GOOGLE_MERIDIAN,
    MeridianEDAPriorContext,
    MeridianEDAReceipt,
    MeridianInputMapping,
    canonical_eda_config,
    eda_config_fingerprint,
    eda_idempotency_key,
)
from app.core.model_intent import ModelIntent
from app.tools.artifacts import write_json_artifact
from app.tools.meridian_contract import MeridianInputContract
from app.tools.meridian_eda_gate import (
    build_meridian_feedback,
    compact_category_payload,
    evaluate_meridian_eda_gate,
)
from app.tools.meridian_eda_job import invoke_meridian_eda_job, meridian_eda_job_configured
from app.tools.meridian_eda_mapping import mapping_from_contract
from app.tools.meridian_eda_runtime import meridian_available, run_official_meridian_eda
from app.tools.meridian_eda_serialize import compact_findings_for_agent, serialize_outcomes
from app.tools.model_consumption import fingerprint_frame


def resolve_eda_source(
    *,
    consumption_view: str | None,
    versioned_table: str | None,
) -> str:
    endpoint = consumption_view or versioned_table
    if not endpoint:
        raise ValidationBlockedError(
            "Meridian EDA requires a verified BigQuery model-consumption endpoint."
        )
    return endpoint


def assert_fingerprint_matches(frame: Any, expected: str) -> str:
    actual = fingerprint_frame(frame)
    if actual != expected:
        raise ValidationBlockedError(
            "EDA BigQuery fingerprint does not match the ModelReady Manifest: "
            f"expected={expected} actual={actual}"
        )
    return actual


def execute_meridian_eda(
    *,
    run_id: str,
    frame: Any,
    intent: ModelIntent,
    contract: MeridianInputContract,
    output_dir: str | Path,
    source_endpoint: str,
    content_fingerprint: str,
    html_uri: str | None = None,
    config_uri: str | None = None,
    request_uri: str | None = None,
    receipt_uri: str | None = None,
) -> dict[str, Any]:
    mapping = mapping_from_contract(intent=intent, contract=contract)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    config_fp = eda_config_fingerprint(mapping)
    idem_key = eda_idempotency_key(
        run_id=run_id,
        model_input_fingerprint=content_fingerprint,
        meridian_version=PINNED_GOOGLE_MERIDIAN,
        eda_config_fingerprint_value=config_fp,
    )
    existing = _matching_receipt(
        output / "meridian_eda_receipt.json",
        html_path=output / "meridian_eda_report.html",
        run_id=run_id,
        content_fingerprint=content_fingerprint,
        config_fp=config_fp,
        idem_key=idem_key,
    )
    if existing is not None:
        gate = evaluate_meridian_eda_gate(
            receipt=existing, html_path=output / "meridian_eda_report.html"
        )
        feedback = build_meridian_feedback(receipt=existing, gate=gate)
        write_json_artifact(
            output / "meridian_user_feedback.json", feedback.model_dump(mode="json")
        )
        return {
            "receipt": existing,
            "gate": gate,
            "feedback": feedback,
            "html_path": output / "meridian_eda_report.html",
            "config_path": output / "meridian_eda_config.json",
            "receipt_path": output / "meridian_eda_receipt.json",
            "mapping": mapping,
            "replayed": True,
            "compact": compact_eda_tool_result(
                run_id=run_id,
                source_endpoint=source_endpoint,
                fingerprint=content_fingerprint,
                html_uri=html_uri or existing.html_report_uri,
                receipt=existing,
                gate=gate,
                replayed=True,
                feedback=feedback,
            ),
        }

    started = utc_now()
    raw = _run_eda_engine(
        frame=frame,
        mapping=mapping,
        output_dir=output,
        run_id=run_id,
        source_endpoint=source_endpoint,
        content_fingerprint=content_fingerprint,
        html_uri=html_uri,
        config_uri=config_uri,
        request_uri=request_uri,
        receipt_uri=receipt_uri,
        config_fp=config_fp,
        idem_key=idem_key,
    )
    completed = utc_now()
    if raw.get("receipt") is not None:
        receipt = raw["receipt"]
        if isinstance(receipt, dict):
            receipt = MeridianEDAReceipt.model_validate(receipt)
    else:
        html_path = Path(raw["html_path"])
        prior = raw["prior_context"]
        if isinstance(prior, dict):
            prior = MeridianEDAPriorContext.model_validate(prior)
        receipt = serialize_outcomes(
            raw["outcomes"],
            run_id=run_id,
            source={
                "bigquery_endpoint": source_endpoint,
                "content_fingerprint": content_fingerprint,
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
            duration_seconds=_elapsed_seconds(started, completed),
            model_input_fingerprint=content_fingerprint,
            eda_config_fingerprint=config_fp,
            idempotency_key=idem_key,
            model_spec=(raw.get("config") or {}).get("model_spec"),
            compatibility_event=(
                raw.get("compatibility_event")
                or (raw.get("config") or {}).get("compatibility_event")
            ),
        )
        write_json_artifact(output / "meridian_eda_config.json", raw["config"])
        write_json_artifact(output / "meridian_eda_receipt.json", receipt.model_dump(mode="json"))
    html_path = output / "meridian_eda_report.html"
    config_path = output / "meridian_eda_config.json"
    receipt_path = output / "meridian_eda_receipt.json"
    write_json_artifact(config_path, {**canonical_eda_config(mapping), **(raw.get("config") or {})})
    write_json_artifact(receipt_path, receipt.model_dump(mode="json"))
    _assert_receipt_identity(
        receipt,
        run_id=run_id,
        content_fingerprint=content_fingerprint,
        config_fp=config_fp,
        idem_key=idem_key,
    )
    gate = evaluate_meridian_eda_gate(receipt=receipt, html_path=html_path)
    feedback = build_meridian_feedback(receipt=receipt, gate=gate)
    feedback_path = output / "meridian_user_feedback.json"
    write_json_artifact(feedback_path, feedback.model_dump(mode="json"))
    return {
        "receipt": receipt,
        "gate": gate,
        "feedback": feedback,
        "html_path": html_path,
        "config_path": config_path,
        "receipt_path": receipt_path,
        "feedback_path": feedback_path,
        "mapping": mapping,
        "replayed": False,
        "compact": compact_eda_tool_result(
            run_id=run_id,
            source_endpoint=source_endpoint,
            fingerprint=content_fingerprint,
            html_uri=html_uri,
            receipt=receipt,
            gate=gate,
            feedback=feedback,
        ),
    }


def compact_eda_tool_result(
    *,
    run_id: str,
    source_endpoint: str,
    fingerprint: str,
    html_uri: str | None,
    receipt: MeridianEDAReceipt,
    gate: dict[str, Any],
    replayed: bool = False,
    feedback: Any | None = None,
) -> dict[str, Any]:
    status = "PRE_MODELING_COMPLETE" if gate.get("status") == "PASS" else "EDA_BLOCKED"
    return {
        "run_id": run_id,
        "status": status,
        "replayed": replayed,
        "source": {"bigquery_endpoint": source_endpoint, "fingerprint": fingerprint},
        "report": {"html_uri": html_uri},
        "severity": {
            "max": receipt.severity_summary.get("max_severity"),
            "errors": receipt.severity_summary.get("error_count", 0),
            "attention": receipt.severity_summary.get("attention_count", 0),
            "info": receipt.severity_summary.get("info_count", 0),
        },
        "categories": compact_category_payload(receipt),
        "findings": compact_findings_for_agent(receipt.findings),
        "eda_gate": {
            "status": gate.get("status"),
            "outcome": gate.get("outcome"),
            "review_recommended": gate.get("review_recommended"),
        },
        "prior_context": receipt.prior_context.model_dump(mode="json"),
        "model_spec": receipt.model_spec.model_dump(mode="json"),
        "data_adequacy": receipt.data_adequacy.model_dump(mode="json"),
        "user_feedback": (
            feedback.model_dump(mode="json")
            if feedback is not None and hasattr(feedback, "model_dump")
            else feedback
        ),
        "idempotency": {
            "run_id": receipt.run_id,
            "model_input_fingerprint": receipt.model_input_fingerprint,
            "meridian_version": PINNED_GOOGLE_MERIDIAN,
            "eda_config_fingerprint": receipt.eda_config_fingerprint,
            "key": receipt.idempotency_key,
        },
    }


def _run_eda_engine(
    *,
    frame: Any,
    mapping: MeridianInputMapping,
    output_dir: Path,
    run_id: str,
    source_endpoint: str,
    content_fingerprint: str,
    html_uri: str | None,
    config_uri: str | None,
    request_uri: str | None,
    receipt_uri: str | None,
    config_fp: str,
    idem_key: str,
) -> dict[str, Any]:
    if meridian_eda_job_configured():
        return invoke_meridian_eda_job(
            run_id=run_id,
            mapping=mapping,
            output_dir=output_dir,
            source_endpoint=source_endpoint,
            content_fingerprint=content_fingerprint,
            html_uri=html_uri,
            config_uri=config_uri,
            request_uri=request_uri,
            receipt_uri=receipt_uri,
            config_fp=config_fp,
            idem_key=idem_key,
            timeout_seconds=settings.eda_job_timeout_seconds,
        )
    if meridian_available():
        return run_official_meridian_eda(frame=frame, mapping=mapping, output_dir=output_dir)
    raise ValidationBlockedError(
        "Official google-meridian is not importable in this process and no isolated "
        "EDA Cloud Run Job is configured via MODELREADY_EDA_JOB. "
        f"Pin {PINNED_GOOGLE_MERIDIAN} in the dedicated worker. "
        "Do not substitute custom EDA calculations."
    )


def _matching_receipt(
    receipt_path: Path,
    *,
    html_path: Path,
    run_id: str,
    content_fingerprint: str,
    config_fp: str,
    idem_key: str,
) -> MeridianEDAReceipt | None:
    if not receipt_path.is_file() or not html_path.is_file() or html_path.stat().st_size <= 0:
        return None
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt = MeridianEDAReceipt.model_validate(payload)
    try:
        _assert_receipt_identity(
            receipt,
            run_id=run_id,
            content_fingerprint=content_fingerprint,
            config_fp=config_fp,
            idem_key=idem_key,
        )
    except ValidationBlockedError:
        return None
    return receipt


def _assert_receipt_identity(
    receipt: MeridianEDAReceipt,
    *,
    run_id: str,
    content_fingerprint: str,
    config_fp: str,
    idem_key: str,
) -> None:
    version = str((receipt.meridian or {}).get("version") or PINNED_GOOGLE_MERIDIAN)
    if version != PINNED_GOOGLE_MERIDIAN:
        raise ValidationBlockedError(
            "EDA receipt meridian_version does not match the pinned worker: "
            f"expected={PINNED_GOOGLE_MERIDIAN} actual={version}"
        )
    if (
        receipt.run_id != run_id
        or receipt.model_input_fingerprint != content_fingerprint
        or receipt.eda_config_fingerprint != config_fp
        or receipt.idempotency_key != idem_key
    ):
        raise ValidationBlockedError(
            "EDA receipt idempotency does not match "
            "run_id + model_input_fingerprint + meridian_version + eda_config_fingerprint."
        )


def _elapsed_seconds(started: datetime, completed: datetime) -> float:
    return round((completed - started).total_seconds(), 3)
