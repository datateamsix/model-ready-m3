"""PUBLISH_READY evaluator and destination-binding tests."""

from __future__ import annotations

from datetime import UTC, datetime

from app.governance.codes import (
    BIGQUERY_DEPOT_DATASET_ID,
    DRIVE_DEPOT_NAME,
    PUBLISH_CONTRACT_VERSION,
    PUBLISH_DRIVE_ARTIFACTS,
    PublishReadinessStatus,
)
from app.governance.publish_contract import (
    PreM3PublishContractV1,
    PublishDestination,
    PublishDestinationKind,
)
from app.governance.publish_evaluator import (
    customer_model_ready_table_id,
    evaluate_publish_readiness,
)
from app.service.publish_governance import drive_export_path, drive_reports_path
from tests.unit.api_support import auth_header
from tests.unit.google_support import connect_google, google_harness
from tests.unit.test_prem3_gcs_import_governance import _verified_upload


def _publish_contract(*, model_ready: bool, write_verified: bool, destinations=None):
    now = datetime.now(UTC)
    dests = destinations
    if dests is None:
        dests = [
            PublishDestination(
                kind=PublishDestinationKind.GOOGLE_DRIVE,
                binding_id="folder_0001",
                target_identity="folder_0001",
                write_verified=write_verified,
            ),
            PublishDestination(
                kind=PublishDestinationKind.BIGQUERY,
                binding_id=f"cust-proj.{BIGQUERY_DEPOT_DATASET_ID}",
                target_identity=f"cust-proj.{BIGQUERY_DEPOT_DATASET_ID}",
                location="US",
                write_verified=write_verified,
            ),
        ]
    draft = PreM3PublishContractV1(
        contract_version=PUBLISH_CONTRACT_VERSION,
        tenant_id="ten_test00000000000000",
        workspace_id="wsp_test00000000000000",
        dataset_id="dset_test0000000000000",
        run_id="run_test00000000000000",
        model_ready_fingerprint="ready-fp" if model_ready else None,
        model_ready_verified=model_ready,
        destinations=dests,
        required_artifacts=list(PUBLISH_DRIVE_ARTIFACTS),
        created_at=now,
        status=PublishReadinessStatus.NOT_PUBLISH_READY,
        contract_fingerprint="pending",
    )
    return draft.model_copy(update={"contract_fingerprint": draft.compute_fingerprint()})


def test_publish_ready_requires_model_ready() -> None:
    receipt = evaluate_publish_readiness(_publish_contract(model_ready=False, write_verified=True))
    assert receipt.status is PublishReadinessStatus.NOT_PUBLISH_READY
    assert any(
        item.code.value == "MODEL_READY_REQUIRED" and not item.passed
        for item in receipt.check_results
    )


def test_publish_ready_requires_bound_destination() -> None:
    receipt = evaluate_publish_readiness(
        _publish_contract(model_ready=True, write_verified=True, destinations=[])
    )
    assert receipt.status is PublishReadinessStatus.NOT_PUBLISH_READY
    assert any(
        item.code.value == "BINDING_MISSING" and not item.passed
        for item in receipt.check_results
    )


def test_publish_ready_requires_write_verification() -> None:
    receipt = evaluate_publish_readiness(_publish_contract(model_ready=True, write_verified=False))
    assert receipt.status is PublishReadinessStatus.NOT_PUBLISH_READY
    assert any(
        item.code.value == "DESTINATION_NOT_WRITABLE" and not item.passed
        for item in receipt.check_results
    )


def test_publish_ready_uses_deterministic_destination() -> None:
    table = customer_model_ready_table_id("dset_test0000000000000", "run_test00000000000000")
    assert table.startswith("model_ready_")
    assert "dset_test0000000000000" in table
    assert drive_export_path("wsp_a", "dset_b", "run_c") == (
        f"{DRIVE_DEPOT_NAME}/exports/wsp_a/dset_b/run_c/"
    )
    assert drive_reports_path("wsp_a", "dset_b", "run_c") == (
        f"{DRIVE_DEPOT_NAME}/reports/wsp_a/dset_b/run_c/"
    )


def test_model_cannot_select_publish_destination() -> None:
    harness = google_harness()
    upload = _verified_upload(harness)
    created = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/evaluations",
        headers=auth_header(),
        json={"upload_id": upload.upload_id, "destination": "attacker-project.other"},
    )
    assert created.status_code == 422
    accepted = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/evaluations",
        headers=auth_header(),
        json={"upload_id": upload.upload_id},
    )
    assert accepted.status_code == 202
    publish = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/evaluations/{accepted.json()['run_id']}/publish-readiness",
        headers=auth_header(),
        json={"destination_project_id": "attacker"},
    )
    assert publish.status_code == 422 or publish.json().get("status") == "NOT_PUBLISH_READY"


def test_drive_publish_contract_uses_bound_prem3_modeling_folder() -> None:
    assert DRIVE_DEPOT_NAME == "prem3-modeling"
    receipt = evaluate_publish_readiness(_publish_contract(model_ready=True, write_verified=True))
    assert any("GOOGLE_DRIVE:folder_0001" in item for item in receipt.destination_summaries)


def test_bq_publish_contract_uses_bound_prem3_modeling_dataset() -> None:
    receipt = evaluate_publish_readiness(_publish_contract(model_ready=True, write_verified=True))
    assert any(
        item.endswith(f".{BIGQUERY_DEPOT_DATASET_ID}") for item in receipt.destination_summaries
    )


def test_publish_ready_receipt_contains_model_ready_fingerprint() -> None:
    receipt = evaluate_publish_readiness(_publish_contract(model_ready=True, write_verified=True))
    assert receipt.status is PublishReadinessStatus.PUBLISH_READY
    assert receipt.model_ready_fingerprint == "ready-fp"


def test_publish_ready_does_not_publish_data_by_itself() -> None:
    harness = google_harness()
    connection_id = connect_google(harness, capabilities=["GOOGLE_DRIVE"])
    harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/integrations/drive/setup",
        headers=auth_header(),
        json={"connection_id": connection_id},
    )
    created_before = list(harness["drive"].created)
    receipt = evaluate_publish_readiness(_publish_contract(model_ready=True, write_verified=True))
    assert receipt.published is False
    assert harness["drive"].created == created_before
    assert harness["bigquery"].created_datasets == []
