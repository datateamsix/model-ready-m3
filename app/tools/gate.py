"""Evidence-backed MODEL_READY gate. Caller-supplied PASS strings are rejected."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.contracts import BigQueryPublishReceipt, ReadinessReceipt
from app.core.errors import ValidationBlockedError
from app.tools.meridian_contract import MeridianInputContract
from app.tools.validation import REQUIRED_DATASET_A_TOOLS, validate_provenance_complete


def evaluate_model_ready_gate(
    *,
    readiness: ReadinessReceipt | dict[str, Any] | str | Path,
    publish: BigQueryPublishReceipt | dict[str, Any] | str | Path,
    meridian_contract: MeridianInputContract | dict[str, Any] | str | Path,
    provenance: dict[str, Any] | str | Path,
) -> dict[str, Any]:
    readiness_obj = _load_readiness(readiness)
    publish_obj = _load_publish(publish)
    contract_obj = _load_contract(meridian_contract)
    provenance_obj = _load_json(provenance)

    readiness_pass = readiness_obj.status == "PASS" and readiness_obj.blocking_checks_passed
    publish_pass = publish_obj.status == "PUBLISHED"
    parity_pass = publish_obj.parity_status == "PASS"
    contract_pass = contract_obj.status == "COMPLETE"
    records = provenance_obj.get("records") or provenance_obj.get("transforms") or []
    mr018 = next((check for check in readiness_obj.checks if check.rule_id == "MR-018"), None)
    structure = validate_provenance_complete(provenance_obj, REQUIRED_DATASET_A_TOOLS)
    provenance_pass = mr018 is not None and mr018.passed and structure.passed

    evidence = {
        "readiness_pass": readiness_pass,
        "publish_pass": publish_pass,
        "parity_pass": parity_pass,
        "contract_pass": contract_pass,
        "provenance_pass": provenance_pass,
        "readiness_status": readiness_obj.status,
        "publish_status": publish_obj.status,
        "parity_status": publish_obj.parity_status,
        "contract_status": contract_obj.status,
        "provenance_records": len(records),
        "mr018_passed": bool(mr018.passed) if mr018 is not None else False,
    }
    if not all([readiness_pass, publish_pass, parity_pass, contract_pass, provenance_pass]):
        raise ValidationBlockedError(f"MODEL_READY blocked: {evidence}")
    return {
        "status": "MODEL_READY",
        "run_id": readiness_obj.run_id,
        "evidence": evidence,
        "terminal": {
            "deterministic_readiness_passed": True,
            "bigquery_model_artifact_published": True,
            "publish_parity_passed": True,
            "meridian_input_contract_generated": True,
            "provenance_complete": True,
        },
    }


def _load_json(value: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return json.loads(Path(value).read_text(encoding="utf-8"))


def _load_readiness(value: ReadinessReceipt | dict[str, Any] | str | Path) -> ReadinessReceipt:
    if isinstance(value, ReadinessReceipt):
        return value
    return ReadinessReceipt.model_validate(
        _load_json(value) if not isinstance(value, dict) else value
    )


def _load_publish(
    value: BigQueryPublishReceipt | dict[str, Any] | str | Path,
) -> BigQueryPublishReceipt:
    if isinstance(value, BigQueryPublishReceipt):
        return value
    payload = value if isinstance(value, dict) else _load_json(value)
    return BigQueryPublishReceipt.model_validate(payload)


def _load_contract(
    value: MeridianInputContract | dict[str, Any] | str | Path,
) -> MeridianInputContract:
    if isinstance(value, MeridianInputContract):
        return value
    payload = value if isinstance(value, dict) else _load_json(value)
    return MeridianInputContract.model_validate(payload)
