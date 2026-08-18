"""IMPORT_READY evaluator, receipts, and manifest fingerprint tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.control_plane.ids import new_import_object_id
from app.core.source_inventory import CanonicalRole
from app.governance.codes import IMPORT_CONTRACT_VERSION, ImportReadinessStatus, SourceType
from app.governance.import_contract import (
    ImportSourceObject,
    PreM3ImportContractV1,
    RoleAssignment,
)
from app.governance.import_evaluator import evaluate_import_readiness
from tests.unit.api_support import auth_header
from tests.unit.google_support import google_harness
from tests.unit.test_prem3_gcs_import_governance import _verified_upload


def _ready_contract(**overrides) -> PreM3ImportContractV1:
    object_id = overrides.pop("object_id", None) or new_import_object_id()
    version = overrides.pop("version_identity", "gen-1:md5-1")
    role = overrides.pop("role", CanonicalRole.PAID_MEDIA)
    now = datetime.now(UTC)
    obj = ImportSourceObject(
        object_id=object_id,
        provider="google_ads",
        role=role,
        logical_name="geo.csv",
        source_identity="ufile_source1",
        version_identity=version,
        object_type="file",
        format="csv",
        schema_fingerprint=None,
        size_bytes=12,
        row_estimate=None,
        source_metadata={},
    )
    draft = PreM3ImportContractV1(
        contract_version=IMPORT_CONTRACT_VERSION,
        tenant_id="ten_test00000000000000",
        workspace_id="wsp_test00000000000000",
        dataset_id="dset_test0000000000000",
        source_type=SourceType.GCS_UPLOAD,
        source_binding_id="upl_test00000000000000",
        objects=[obj],
        role_assignments=[
            RoleAssignment(object_id=object_id, role=role, provider="google_ads")
        ],
        created_at=now,
        verified_at=now,
        status=ImportReadinessStatus.NOT_IMPORT_READY,
        manifest_fingerprint="pending",
        **overrides,
    )
    return draft.model_copy(update={"manifest_fingerprint": draft.compute_fingerprint()})


def test_only_deterministic_evaluator_can_emit_import_ready() -> None:
    contract = _ready_contract()
    contract = contract.model_copy(
        update={"status": ImportReadinessStatus.IMPORT_READY, "objects": []}
    )
    receipt = evaluate_import_readiness(contract)
    assert receipt.status is ImportReadinessStatus.NOT_IMPORT_READY
    root = Path("app")
    for path in root.rglob("*.py"):
        if path.name in {"import_evaluator.py", "codes.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "status = ImportReadinessStatus.IMPORT_READY" not in text


def test_import_ready_has_receipt() -> None:
    receipt = evaluate_import_readiness(_ready_contract())
    assert receipt.status is ImportReadinessStatus.IMPORT_READY
    assert receipt.receipt_id.startswith("rcpt_")


def test_import_ready_receipt_contains_manifest_fingerprint() -> None:
    contract = _ready_contract()
    receipt = evaluate_import_readiness(contract)
    assert receipt.manifest_fingerprint == contract.compute_fingerprint()
    assert len(receipt.manifest_fingerprint) == 64


def test_import_manifest_export_deterministic() -> None:
    contract = _ready_contract(object_id="iobj_aaaaaaaaaaaaaaaaaaaa")
    assert contract.compute_fingerprint() == contract.compute_fingerprint()


def test_equivalent_manifest_same_fingerprint() -> None:
    first = _ready_contract(object_id="iobj_aaaaaaaaaaaaaaaaaaaa")
    second = _ready_contract(object_id="iobj_aaaaaaaaaaaaaaaaaaaa")
    assert first.compute_fingerprint() == second.compute_fingerprint()


def test_role_change_changes_manifest_fingerprint() -> None:
    paid = _ready_contract(object_id="iobj_aaaaaaaaaaaaaaaaaaaa", role=CanonicalRole.PAID_MEDIA)
    kpi = _ready_contract(object_id="iobj_aaaaaaaaaaaaaaaaaaaa", role=CanonicalRole.KPI)
    assert paid.compute_fingerprint() != kpi.compute_fingerprint()


def test_source_version_change_changes_manifest_fingerprint() -> None:
    first = _ready_contract(object_id="iobj_aaaaaaaaaaaaaaaaaaaa", version_identity="v1")
    second = _ready_contract(object_id="iobj_aaaaaaaaaaaaaaaaaaaa", version_identity="v2")
    assert first.compute_fingerprint() != second.compute_fingerprint()


def test_source_change_invalidates_current_import_readiness() -> None:
    harness = google_harness()
    upload = _verified_upload(harness)
    file_id = upload.files[0].upload_file_id
    client = harness["client"]
    workspace = harness["workspace"]
    dataset = harness["dataset"]
    client.put(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/import-binding",
        headers=auth_header(),
        json={
            "source_type": "GCS_UPLOAD",
            "upload_id": upload.upload_id,
            "selected_object_ids": [file_id],
            "role_assignments": [
                {"object_id": file_id, "role": "paid_media", "provider": "google_ads"}
            ],
        },
    )
    first = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/import-readiness",
        headers=auth_header(),
    ).json()
    assert first["status"] == "IMPORT_READY"
    mutated_files = [
        upload.files[0].model_copy(update={"generation": "999", "md5_hash": "changed"})
    ]
    harness["repo"].update_upload(upload.model_copy(update={"files": mutated_files}))
    second = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/import-readiness",
        headers=auth_header(),
    ).json()
    assert second["receipt_id"] != first["receipt_id"]
    assert second["manifest_fingerprint"] != first["manifest_fingerprint"]
    previous = harness["repo"].get_import_receipt(
        tenant_id=harness["tenant"].tenant_id,
        workspace_id=workspace["workspace_id"],
        dataset_id=dataset["dataset_id"],
        receipt_id=first["receipt_id"],
    )
    assert previous is not None
    assert previous.superseded is True


def test_import_ready_does_not_imply_model_ready() -> None:
    receipt = evaluate_import_readiness(_ready_contract())
    assert receipt.status is ImportReadinessStatus.IMPORT_READY
    assert receipt.status.value != "MODEL_READY"
    assert not hasattr(receipt, "model_ready")
