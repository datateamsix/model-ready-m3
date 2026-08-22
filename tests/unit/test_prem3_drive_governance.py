"""Drive depot binding and Drive IMPORT_READY governance tests."""

from __future__ import annotations

from app.control_plane.entitlements import PlanId
from app.governance.codes import DRIVE_DEPOT_NAME
from app.integrations.google.adapters import DriveFile
from tests.unit.api_support import auth_header, make_client, seed_tenant
from tests.unit.google_support import connect_google, google_harness


def _setup_drive(harness):
    connection_id = connect_google(harness, capabilities=["GOOGLE_DRIVE"])
    response = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/integrations/drive/setup",
        headers=auth_header(),
        json={"connection_id": connection_id, "import_enabled": True, "export_enabled": True},
    )
    assert response.status_code == 200, response.text
    return connection_id, response.json()


def test_canonical_drive_folder_name_is_prem3_modeling() -> None:
    assert DRIVE_DEPOT_NAME == "prem3-modeling"
    harness = google_harness()
    _connection_id, binding = _setup_drive(harness)
    assert binding["root_folder_name"] == "prem3-modeling"


def test_drive_binding_uses_folder_id_not_name_as_authority() -> None:
    harness = google_harness()
    _connection_id, binding = _setup_drive(harness)
    assert binding["root_folder_id"] != DRIVE_DEPOT_NAME
    assert binding["root_folder_id"].startswith("folder_")


def test_drive_depot_setup_idempotent() -> None:
    harness = google_harness()
    connection_id, first = _setup_drive(harness)
    created_after_first = list(harness["drive"].created)
    second = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/integrations/drive/setup",
        headers=auth_header(),
        json={"connection_id": connection_id, "import_enabled": True, "export_enabled": True},
    )
    assert second.status_code == 200
    assert second.json()["root_folder_id"] == first["root_folder_id"]
    assert harness["drive"].created == created_after_first


def test_cross_tenant_drive_binding_denied() -> None:
    harness = google_harness()
    connection_id, _binding = _setup_drive(harness)
    other_tenant, other_identity = seed_tenant(
        harness["repo"],
        provider_org="org_other",
        provider_user="user_other",
        plan_id=PlanId.PROJECT,
    )
    foreign, _ = make_client(repo=harness["repo"], identity=other_identity)
    other_ws = foreign.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "Other"}
    ).json()
    denied = foreign.post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/integrations/drive/setup",
        headers=auth_header(),
        json={"connection_id": connection_id},
    )
    assert denied.status_code == 404
    missing = harness["repo"].get_drive_binding(
        tenant_id=other_tenant.tenant_id, workspace_id=other_ws["workspace_id"]
    )
    assert missing is None


def test_deleted_bound_folder_not_replaced_by_same_name_automatically() -> None:
    harness = google_harness()
    connection_id, binding = _setup_drive(harness)
    harness["drive"].trash(binding["root_folder_id"])
    created_before = list(harness["drive"].created)
    repaired = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/integrations/drive/setup",
        headers=auth_header(),
        json={"connection_id": connection_id},
    )
    assert repaired.status_code == 200
    assert repaired.json()["status"] == "DEGRADED"
    assert repaired.json()["root_folder_id"] == binding["root_folder_id"]
    assert harness["drive"].created == created_before


def test_drive_import_requires_explicit_selected_objects() -> None:
    harness = google_harness()
    connection_id, _binding = _setup_drive(harness)
    put = harness["client"].put(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-binding",
        headers=auth_header(),
        json={
            "source_type": "GOOGLE_DRIVE",
            "connection_id": connection_id,
            "selected_object_ids": [],
            "role_assignments": [],
        },
    )
    assert put.status_code == 200, put.text
    ready = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-readiness",
        headers=auth_header(),
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "NOT_IMPORT_READY"


def test_drive_import_requires_supported_materialization_type() -> None:
    harness = google_harness()
    connection_id, _binding = _setup_drive(harness)
    harness["drive"].seed(
        DriveFile(
            file_id="sheet_file_0001",
            name="budget.gsheet",
            mime_type="application/vnd.google-apps.spreadsheet",
            parents=(),
            md5="abc",
            head_revision_id="rev1",
            version="1",
            size_bytes=12,
        )
    )
    harness["client"].put(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-binding",
        headers=auth_header(),
        json={
            "source_type": "GOOGLE_DRIVE",
            "connection_id": connection_id,
            "selected_object_ids": ["sheet_file_0001"],
            "role_assignments": [
                {"object_id": "sheet_file_0001", "role": "paid_media", "provider": "google_ads"}
            ],
        },
    )
    ready = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-readiness",
        headers=auth_header(),
    ).json()
    assert ready["status"] == "NOT_IMPORT_READY"
    assert any(
        item["code"] == "FORMAT_UNSUPPORTED"
        for item in ready["check_results"]
        if not item["passed"]
    )


def test_drive_import_requires_version_identity() -> None:
    harness = google_harness()
    connection_id, _binding = _setup_drive(harness)
    harness["drive"].seed(
        DriveFile(
            file_id="csv_file_0001",
            name="geo.csv",
            mime_type="text/csv",
            parents=(),
            md5=None,
            head_revision_id=None,
            version=None,
            size_bytes=12,
        )
    )
    harness["client"].put(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-binding",
        headers=auth_header(),
        json={
            "source_type": "GOOGLE_DRIVE",
            "connection_id": connection_id,
            "selected_object_ids": ["csv_file_0001"],
            "role_assignments": [
                {"object_id": "csv_file_0001", "role": "paid_media", "provider": "google_ads"}
            ],
        },
    )
    ready = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-readiness",
        headers=auth_header(),
    ).json()
    assert ready["status"] == "NOT_IMPORT_READY"
    assert any(
        item["code"] == "SOURCE_VERSION_UNVERIFIABLE"
        for item in ready["check_results"]
        if not item["passed"]
    )


def test_drive_import_requires_role_mapping() -> None:
    harness = google_harness()
    connection_id, _binding = _setup_drive(harness)
    harness["drive"].seed(
        DriveFile(
            file_id="csv_file_0002",
            name="geo.csv",
            mime_type="text/csv",
            parents=(),
            md5="abc",
            head_revision_id="rev1",
            version="1",
            size_bytes=12,
        )
    )
    harness["client"].put(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-binding",
        headers=auth_header(),
        json={
            "source_type": "GOOGLE_DRIVE",
            "connection_id": connection_id,
            "selected_object_ids": ["csv_file_0002"],
            "role_assignments": [],
        },
    )
    ready = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-readiness",
        headers=auth_header(),
    ).json()
    assert ready["status"] == "NOT_IMPORT_READY"
    assert any(
        item["code"] == "SOURCE_ROLE_MISSING"
        for item in ready["check_results"]
        if not item["passed"]
    )


def test_drive_folder_exists_does_not_equal_import_ready() -> None:
    harness = google_harness()
    _setup_drive(harness)
    got = harness["client"].get(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/integrations/drive",
        headers=auth_header(),
    )
    assert got.status_code == 200
    assert got.json()["status"] == "ACTIVE"
    put = harness["client"].put(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-binding",
        headers=auth_header(),
        json={"source_type": "GOOGLE_DRIVE", "selected_object_ids": [], "role_assignments": []},
    )
    assert put.status_code == 200
    ready = harness["client"].post(
        f"/v1/workspaces/{harness['workspace']['workspace_id']}/datasets/"
        f"{harness['dataset']['dataset_id']}/import-readiness",
        headers=auth_header(),
    ).json()
    assert ready["status"] == "NOT_IMPORT_READY"
