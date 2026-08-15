"""Run official Meridian pre-modeling EDA against a confirmed BigQuery model input."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.contracts import utc_now
from app.core.errors import ValidationBlockedError
from app.core.meridian_eda_contracts import (
    PINNED_GOOGLE_MERIDIAN,
    MeridianEDAPriorContext,
    MeridianEDAReceipt,
    MeridianInputMapping,
)
from app.core.model_intent import ModelIntent
from app.tools.artifacts import write_json_artifact
from app.tools.meridian_contract import MeridianInputContract
from app.tools.meridian_eda_gate import compact_category_payload, evaluate_meridian_eda_gate
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
) -> dict[str, Any]:
    mapping = mapping_from_contract(intent=intent, contract=contract)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    raw = _run_eda_engine(frame=frame, mapping=mapping, output_dir=output)
    completed = utc_now()
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
    )
    config_path = output / "meridian_eda_config.json"
    receipt_path = output / "meridian_eda_receipt.json"
    write_json_artifact(config_path, raw["config"])
    write_json_artifact(receipt_path, receipt.model_dump(mode="json"))
    gate = evaluate_meridian_eda_gate(receipt=receipt, html_path=html_path)
    return {
        "receipt": receipt,
        "gate": gate,
        "html_path": html_path,
        "config_path": config_path,
        "receipt_path": receipt_path,
        "mapping": mapping,
        "compact": compact_eda_tool_result(
            run_id=run_id,
            source_endpoint=source_endpoint,
            fingerprint=content_fingerprint,
            html_uri=html_uri,
            receipt=receipt,
            gate=gate,
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
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "status": "EDA_COMPLETE",
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
    }


def _run_eda_engine(
    *,
    frame: Any,
    mapping: MeridianInputMapping,
    output_dir: Path,
) -> dict[str, Any]:
    worker = (os.environ.get("MERIDIAN_EDA_PYTHON") or "").strip()
    if meridian_available() and not worker:
        return run_official_meridian_eda(frame=frame, mapping=mapping, output_dir=output_dir)
    if worker:
        raise ValidationBlockedError(
            "Dedicated Meridian EDA worker invocation is configured via "
            "MERIDIAN_EDA_PYTHON, but this milestone requires the worker to write "
            "structured outcomes in-process. Install google-meridian=="
            f"{PINNED_GOOGLE_MERIDIAN} in a dedicated interpreter and keep it "
            "out of the M3 ADK runtime."
        )
    raise ValidationBlockedError(
        "Official google-meridian is not importable in this process. "
        f"Pin {PINNED_GOOGLE_MERIDIAN} in a dedicated EDA worker. "
        "Do not substitute custom EDA calculations."
    )


def _elapsed_seconds(started: datetime, completed: datetime) -> float:
    return round((completed - started).total_seconds(), 3)
