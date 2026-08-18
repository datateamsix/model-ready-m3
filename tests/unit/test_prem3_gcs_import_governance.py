"""GCS_UPLOAD import governance compiled from verified Mission 10 uploads."""

from __future__ import annotations

from app.core.source_inventory import CanonicalRole
from app.governance.codes import ImportReadinessStatus, SourceType
from app.governance.import_contract import RoleAssignment
from app.governance.import_evaluator import evaluate_import_readiness
from app.service.import_governance import compile_verified_gcs_upload
from tests.unit.api_support import auth_header
from tests.unit.google_support import google_harness
from tests.unit.test_prem3_uploads_evaluations import (
    test_create_evaluation_requires_verified_upload_and_server_run_id,
)


def _verified_upload(harness, *, filename: str = "geo.csv", data: bytes = b"hello,world\n"):
    client = harness["client"]
    workspace = harness["workspace"]
    dataset = harness["dataset"]
    created = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/uploads",
        headers=auth_header(),
        json={
            "files": [
                {
                    "filename": filename,
                    "content_type": "text/csv" if filename.endswith(".csv") else "application/json",
                    "size_bytes": len(data) if data else 1,
                }
            ]
        },
    )
    assert created.status_code == 201, created.text
    upload = harness["repo"].get_upload(
        tenant_id=harness["tenant"].tenant_id,
        workspace_id=workspace["workspace_id"],
        dataset_id=dataset["dataset_id"],
        upload_id=created.json()["upload_id"],
    )
    assert upload is not None
    harness["store"].put_bytes(
        bucket="prem3-test-raw",
        object_name=upload.files[0].object_name,
        data=data or b"x",
        content_type=upload.files[0].content_type,
    )
    complete = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}"
        f"/uploads/{created.json()['upload_id']}/complete",
        headers=auth_header(),
    )
    assert complete.status_code == 200, complete.text
    verified = harness["repo"].get_upload(
        tenant_id=harness["tenant"].tenant_id,
        workspace_id=workspace["workspace_id"],
        dataset_id=dataset["dataset_id"],
        upload_id=created.json()["upload_id"],
    )
    assert verified is not None
    return verified


def test_verified_gcs_upload_can_compile_import_contract() -> None:
    harness = google_harness()
    upload = _verified_upload(harness)
    file_id = upload.files[0].upload_file_id
    contract = compile_verified_gcs_upload(
        upload=upload,
        role_assignments=[
            RoleAssignment(object_id=file_id, role=CanonicalRole.PAID_MEDIA, provider="google_ads")
        ],
    )
    assert contract.source_type is SourceType.GCS_UPLOAD
    receipt = evaluate_import_readiness(contract)
    assert receipt.status is ImportReadinessStatus.IMPORT_READY


def test_gcs_import_requires_supported_format() -> None:
    harness = google_harness()
    upload = _verified_upload(harness)
    file_id = upload.files[0].upload_file_id
    mutated = upload.model_copy(
        update={
            "files": [
                upload.files[0].model_copy(
                    update={"original_filename": "notes.txt", "content_type": "text/plain"}
                )
            ]
        }
    )
    contract = compile_verified_gcs_upload(
        upload=mutated,
        role_assignments=[
            RoleAssignment(object_id=file_id, role=CanonicalRole.PAID_MEDIA, provider="google_ads")
        ],
    )
    receipt = evaluate_import_readiness(contract)
    assert receipt.status is ImportReadinessStatus.NOT_IMPORT_READY
    assert any(
        item.code.value == "FORMAT_UNSUPPORTED" and not item.passed
        for item in receipt.check_results
    )


def test_gcs_import_requires_nonempty_file() -> None:
    harness = google_harness()
    upload = _verified_upload(harness, data=b"hello,world\n")
    file_id = upload.files[0].upload_file_id
    mutated = upload.model_copy(
        update={
            "files": [
                upload.files[0].model_copy(
                    update={"actual_size_bytes": 0, "declared_size_bytes": 0}
                )
            ]
        }
    )
    contract = compile_verified_gcs_upload(
        upload=mutated,
        role_assignments=[
            RoleAssignment(object_id=file_id, role=CanonicalRole.PAID_MEDIA, provider="google_ads")
        ],
    )
    receipt = evaluate_import_readiness(contract)
    assert receipt.status is ImportReadinessStatus.NOT_IMPORT_READY
    assert any(
        item.code.value == "OBJECT_EMPTY" and not item.passed
        for item in receipt.check_results
    )


def test_gcs_import_uses_frozen_generation_checksum() -> None:
    harness = google_harness()
    upload = _verified_upload(harness)
    file_id = upload.files[0].upload_file_id
    contract = compile_verified_gcs_upload(
        upload=upload,
        role_assignments=[
            RoleAssignment(object_id=file_id, role=CanonicalRole.PAID_MEDIA, provider="google_ads")
        ],
    )
    assert upload.files[0].generation
    assert contract.objects[0].version_identity.startswith(f"{upload.files[0].generation}:")


def test_gcs_import_requires_role_assignment() -> None:
    harness = google_harness()
    upload = _verified_upload(harness)
    contract = compile_verified_gcs_upload(upload=upload, role_assignments=[])
    receipt = evaluate_import_readiness(contract)
    assert receipt.status is ImportReadinessStatus.NOT_IMPORT_READY
    assert any(
        item.code.value == "SOURCE_ROLE_MISSING" and not item.passed
        for item in receipt.check_results
    )


def test_gcs_import_ambiguity_blocks_import_ready() -> None:
    harness = google_harness()
    upload = _verified_upload(harness)
    file_id = upload.files[0].upload_file_id
    contract = compile_verified_gcs_upload(
        upload=upload,
        role_assignments=[
            RoleAssignment(object_id=file_id, role=CanonicalRole.PAID_MEDIA, provider="google_ads"),
            RoleAssignment(object_id=file_id, role=CanonicalRole.KPI, provider="google_ads"),
        ],
    )
    receipt = evaluate_import_readiness(contract)
    assert receipt.status is ImportReadinessStatus.NOT_IMPORT_READY
    assert any(
        item.code.value == "SOURCE_ROLE_AMBIGUOUS" and not item.passed
        for item in receipt.check_results
    )


def test_existing_evaluation_behavior_unchanged() -> None:
    test_create_evaluation_requires_verified_upload_and_server_run_id()
