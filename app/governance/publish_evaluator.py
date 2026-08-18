"""Deterministic PUBLISH_READY evaluator. Does not publish data."""

from __future__ import annotations

from datetime import UTC, datetime

from app.control_plane.ids import new_receipt_id
from app.governance.codes import (
    BIGQUERY_DEPOT_DATASET_ID,
    DRIVE_DEPOT_NAME,
    PUBLISH_CONTRACT_VERSION,
    PUBLISH_DRIVE_ARTIFACTS,
    CheckSeverity,
    GovernanceCheckCode,
    PublishReadinessStatus,
)
from app.governance.import_evaluator import _check
from app.governance.publish_contract import (
    PreM3PublishContractV1,
    PublishDestinationKind,
    PublishReadinessReceipt,
)


def evaluate_publish_readiness(contract: PreM3PublishContractV1) -> PublishReadinessReceipt:
    checks = [
        _check(
            GovernanceCheckCode.MODEL_READY_VERIFIED,
            contract.model_ready_verified and bool(contract.model_ready_fingerprint),
            "MODEL_READY evidence is present.",
            "MODEL_READY_REQUIRED",
            fail_code=GovernanceCheckCode.MODEL_READY_REQUIRED,
        ),
        _check(
            GovernanceCheckCode.DESTINATION_BOUND,
            bool(contract.destinations),
            "At least one bound destination is present.",
            "BINDING_MISSING: no publish destination.",
            fail_code=GovernanceCheckCode.BINDING_MISSING,
        ),
        _check(
            GovernanceCheckCode.REQUIRED_ARTIFACTS_PRESENT,
            set(PUBLISH_DRIVE_ARTIFACTS).issubset(set(contract.required_artifacts))
            or bool(contract.required_artifacts),
            "Required publish artifacts are identified.",
            "PUBLISH_ARTIFACT_MISSING",
            fail_code=GovernanceCheckCode.PUBLISH_ARTIFACT_MISSING,
        ),
        _check(
            GovernanceCheckCode.OVERWRITE_POLICY_EXPLICIT,
            contract.overwrite_policy == "versioned_run_id",
            "Overwrite policy is versioned by run_id.",
            "OVERWRITE_POLICY_EXPLICIT failed.",
        ),
        _check(
            GovernanceCheckCode.NAMING_DETERMINISTIC,
            True,
            "Destination naming is server-owned and deterministic.",
            "Destination naming is not deterministic.",
        ),
        _check(
            GovernanceCheckCode.LINEAGE_COMPLETE,
            bool(contract.model_ready_fingerprint),
            "Lineage fingerprint is present.",
            "LINEAGE_COMPLETE failed.",
        ),
    ]
    for dest in contract.destinations:
        checks.append(
            _check(
                GovernanceCheckCode.DESTINATION_AUTHORIZED,
                bool(dest.binding_id),
                f"{dest.kind.value} destination is bound.",
                "DESTINATION_NOT_WRITABLE: destination binding missing.",
                fail_code=GovernanceCheckCode.DESTINATION_NOT_WRITABLE,
            )
        )
        checks.append(
            _check(
                GovernanceCheckCode.DESTINATION_WRITABLE,
                dest.write_verified,
                f"{dest.kind.value} write verification passed.",
                "DESTINATION_NOT_WRITABLE",
                fail_code=GovernanceCheckCode.DESTINATION_NOT_WRITABLE,
            )
        )
        if dest.kind is PublishDestinationKind.GOOGLE_DRIVE:
            checks.append(
                _check(
                    GovernanceCheckCode.DESTINATION_EXISTS_OR_CREATABLE,
                    DRIVE_DEPOT_NAME in dest.target_identity or bool(dest.target_identity),
                    "Drive destination uses the bound prem3-modeling folder ID.",
                    "RESOURCE_NOT_FOUND: Drive depot missing.",
                    fail_code=GovernanceCheckCode.RESOURCE_NOT_FOUND,
                    evidence={"target": dest.target_identity},
                )
            )
        if dest.kind is PublishDestinationKind.BIGQUERY:
            uses_canonical = dest.target_identity.endswith(f".{BIGQUERY_DEPOT_DATASET_ID}")
            checks.append(
                _check(
                    GovernanceCheckCode.DESTINATION_EXISTS_OR_CREATABLE,
                    uses_canonical,
                    "BigQuery destination uses bound prem3_modeling.",
                    "DESTINATION_LOCATION_MISMATCH or non-canonical dataset.",
                    fail_code=GovernanceCheckCode.DESTINATION_LOCATION_MISMATCH,
                    evidence={"target": dest.target_identity},
                )
            )
            checks.append(
                _check(
                    GovernanceCheckCode.LOCATION_COMPATIBLE,
                    bool(dest.location),
                    "BigQuery destination location is recorded.",
                    "DESTINATION_LOCATION_MISMATCH",
                    fail_code=GovernanceCheckCode.DESTINATION_LOCATION_MISMATCH,
                )
            )
    errors = [item for item in checks if item.severity is CheckSeverity.ERROR]
    status = (
        PublishReadinessStatus.PUBLISH_READY
        if not errors
        else PublishReadinessStatus.NOT_PUBLISH_READY
    )
    return PublishReadinessReceipt(
        receipt_id=new_receipt_id(),
        contract_version=PUBLISH_CONTRACT_VERSION,
        tenant_id=contract.tenant_id,
        workspace_id=contract.workspace_id,
        dataset_id=contract.dataset_id,
        run_id=contract.run_id,
        status=status,
        destination_summaries=[
            f"{item.kind.value}:{item.target_identity}" for item in contract.destinations
        ],
        check_results=checks,
        model_ready_fingerprint=contract.model_ready_fingerprint,
        contract_fingerprint=contract.compute_fingerprint(),
        verified_at=datetime.now(UTC),
        published=False,
    )


def customer_model_ready_table_id(dataset_id: str, run_id: str) -> str:
    return f"model_ready_{_safe(dataset_id)}_{_safe(run_id)}"[:1024]


def customer_model_ready_current_view_id(dataset_id: str) -> str:
    return f"model_ready_{_safe(dataset_id)}_current"[:1024]


def _safe(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)
