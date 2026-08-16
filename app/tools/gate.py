"""Evidence-backed MODEL_READY gate. Caller-supplied PASS strings are rejected."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.contracts import BigQueryPublishReceipt, ReadinessReceipt
from app.core.errors import ValidationBlockedError
from app.tools.meridian_contract import MeridianInputContract
from app.tools.meridian_eda_gate import evaluate_meridian_eda_gate
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


def evaluate_final_model_ready_gate(
    *,
    readiness: ReadinessReceipt | dict[str, Any] | str | Path,
    publish: BigQueryPublishReceipt | dict[str, Any] | str | Path,
    meridian_contract: MeridianInputContract | dict[str, Any] | str | Path,
    provenance: dict[str, Any] | str | Path,
    confirmation: dict[str, Any] | str | Path,
    consumption: dict[str, Any] | str | Path,
    eda: dict[str, Any] | str | Path,
    html_path: str | Path | None = None,
    html_persisted: bool | None = None,
) -> dict[str, Any]:
    base = evaluate_model_ready_gate(
        readiness=readiness,
        publish=publish,
        meridian_contract=meridian_contract,
        provenance=provenance,
    )
    confirmation_obj = _load_json(confirmation)
    consumption_obj = _load_json(consumption)
    checks = confirmation_obj.get("checks") or {}
    confirmation_pass = (
        confirmation_obj.get("status") == "MODEL_READY"
        and bool(checks)
        and all(bool(value) for value in checks.values())
    )
    consumption_pass = consumption_obj.get("status") == "PROMOTION_VERIFIED"
    view_pass = bool(checks.get("stable_view_matches"))
    registry_pass = bool(checks.get("registry_recorded"))
    physical_pass = bool(checks.get("physical_schema_matches"))
    partition_pass = bool(checks.get("partitioning_matches"))
    cluster_pass = bool(checks.get("clustering_matches"))
    description_pass = bool(checks.get("column_descriptions_match"))
    eda_gate = evaluate_meridian_eda_gate(
        receipt=eda,
        html_path=html_path,
        html_persisted=html_persisted if html_path is None else None,
    )
    eda_pass = eda_gate.get("status") == "PASS"
    eda_html = bool(checks.get("meridian_eda_html_persisted"))
    eda_complete = bool(checks.get("meridian_eda_complete"))
    eda_zero = bool(checks.get("meridian_eda_zero_errors"))
    eda_spec = bool(checks.get("meridian_eda_model_spec_disclosed"))
    eda_not_final = bool(checks.get("meridian_eda_not_approved_for_final_modeling"))
    eda_aks = bool(checks.get("meridian_eda_aks_disabled"))
    eda_adequacy = bool(checks.get("meridian_eda_data_adequacy_captured"))
    eda_knots = bool(checks.get("meridian_eda_knots_identifiable"))
    handoff_pass = bool(checks.get("pre_modeling_handoff_persisted"))
    eda_evidence = eda_gate.get("evidence") or {}
    evidence = {
        **base["evidence"],
        "confirmation_pass": confirmation_pass,
        "consumption_pass": consumption_pass,
        "stable_view_pass": view_pass,
        "registry_pass": registry_pass,
        "physical_schema_pass": physical_pass,
        "partition_pass": partition_pass,
        "cluster_pass": cluster_pass,
        "column_description_pass": description_pass,
        "meridian_eda_pass": eda_pass,
        "meridian_eda_html_pass": eda_html,
        "meridian_eda_complete": eda_complete,
        "meridian_eda_zero_errors": eda_zero,
        "meridian_eda_model_spec_disclosed": eda_spec,
        "meridian_eda_not_approved_for_final_modeling": eda_not_final,
        "meridian_eda_aks_disabled": eda_aks,
        "meridian_eda_data_adequacy_captured": eda_adequacy,
        "meridian_eda_knots_identifiable": eda_knots,
        "handoff_pass": handoff_pass,
        "meridian_eda_review_recommended": bool(eda_gate.get("review_recommended")),
        "n_geos": eda_evidence.get("n_geos"),
        "n_times": eda_evidence.get("n_times"),
        "n_knots": eda_evidence.get("n_knots"),
        "n_controls": eda_evidence.get("n_controls"),
        "n_treatments": eda_evidence.get("n_treatments"),
        "n_parameters": eda_evidence.get("n_parameters"),
        "n_data_points": eda_evidence.get("n_data_points"),
        "data_adequacy_ratio": eda_evidence.get("data_adequacy_ratio"),
        "model_spec_source": eda_evidence.get("model_spec_source"),
        "model_spec_knots": eda_evidence.get("model_spec_knots"),
    }
    if not all(
        [
            confirmation_pass,
            consumption_pass,
            view_pass,
            registry_pass,
            physical_pass,
            partition_pass,
            cluster_pass,
            description_pass,
            eda_pass,
            eda_html,
            eda_complete,
            eda_zero,
            eda_spec,
            eda_not_final,
            eda_aks,
            eda_adequacy,
            eda_knots,
            handoff_pass,
        ]
    ):
        raise ValidationBlockedError(f"MODEL_READY blocked: {evidence}")
    base["evidence"] = evidence
    base["terminal"] = {
        **base["terminal"],
        "versioned_bigquery_post_write_passed": True,
        "physical_bigquery_schema_passed": physical_pass,
        "partitioned_by_time": partition_pass,
        "clustered_by_geo": cluster_pass,
        "column_descriptions_present": description_pass,
        "stable_model_consumption_view_promoted": view_pass,
        "stable_view_independently_verified": view_pass,
        "model_ready_registry_recorded": registry_pass,
        "final_confirmation_receipt_passed": confirmation_pass,
        "meridian_eda_passed": True,
        "meridian_eda_html_persisted": True,
        "meridian_eda_model_spec_disclosed": True,
        "meridian_eda_data_adequacy_captured": True,
        "meridian_eda_knots_identifiable": True,
        "pre_modeling_handoff_persisted": True,
        "review_recommended": bool(eda_gate.get("review_recommended")),
    }
    return base


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
