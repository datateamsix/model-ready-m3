"""Dataset upload create/complete and Evaluation resource API tests."""

from __future__ import annotations

from app.control_plane.entitlements import PlanId
from app.service.object_store import FakeObjectStore
from app.service.upload_config import UploadConfig
from app.service.upload_service import UploadService
from app.service.upload_signing import FakeUploadSigner
from tests.unit.api_support import auth_header, make_client, seed_tenant


def _paid_client():
    client, repo = make_client()
    tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, repo = make_client(repo=repo, identity=identity)
    store = FakeObjectStore()
    signer = FakeUploadSigner()
    upload_service = UploadService(
        repo=repo,
        config=UploadConfig(
            raw_bucket="prem3-test-raw",
            signed_url_ttl_seconds=900,
            max_files=5,
            max_file_bytes=1024 * 1024,
            max_total_bytes=2 * 1024 * 1024,
            runtime_sa=None,
        ),
        signer=signer,
        object_store=store,
    )
    client.app.state.upload_service = upload_service
    client.app.state.object_store = store
    client.app.state.upload_signer = signer
    workspace = client.post(
        "/v1/workspaces",
        headers=auth_header(),
        json={"name": "MMM One"},
    ).json()
    dataset = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets",
        headers=auth_header(),
        json={"name": "Sales"},
    ).json()
    return client, repo, tenant, workspace, dataset, store, signer


def test_create_upload_issues_signed_put_without_gcs_authority() -> None:
    client, _repo, _tenant, workspace, dataset, _store, signer = _paid_client()
    response = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/uploads",
        headers=auth_header(),
        json={
            "files": [
                {
                    "filename": "geo.csv",
                    "content_type": "text/csv",
                    "size_bytes": 12,
                }
            ]
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["upload_id"].startswith("upl_")
    assert "gs://" not in response.text.lower()
    assert "bucket" not in body
    instruction = body["upload_instructions"][0]
    assert instruction["method"] == "PUT"
    assert instruction["required_headers"]["x-goog-if-generation-match"] == "0"
    assert signer.calls
    assert "objects/" in str(signer.calls[0]["object_name"]) or "files/" in str(
        signer.calls[0]["object_name"]
    )


def test_client_cannot_submit_path_traversal_filename() -> None:
    client, _repo, _tenant, workspace, dataset, _store, _signer = _paid_client()
    response = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/uploads",
        headers=auth_header(),
        json={
            "files": [
                {
                    "filename": "../escape.csv",
                    "content_type": "text/csv",
                    "size_bytes": 12,
                }
            ]
        },
    )
    assert response.status_code == 422


def test_complete_upload_verifies_and_freezes_generation() -> None:
    client, repo, tenant, workspace, dataset, store, _signer = _paid_client()
    created = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/uploads",
        headers=auth_header(),
        json={
            "files": [
                {
                    "filename": "geo.csv",
                    "content_type": "text/csv",
                    "size_bytes": 12,
                }
            ]
        },
    ).json()
    upload = repo.get_upload(
        tenant_id=tenant.tenant_id,
        workspace_id=workspace["workspace_id"],
        dataset_id=dataset["dataset_id"],
        upload_id=created["upload_id"],
    )
    assert upload is not None
    store.put_bytes(
        bucket="prem3-test-raw",
        object_name=upload.files[0].object_name,
        data=b"hello,world\n",
        content_type="text/csv",
    )
    complete = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}"
        f"/uploads/{created['upload_id']}/complete",
        headers=auth_header(),
    )
    assert complete.status_code == 200, complete.text
    body = complete.json()
    assert body["status"] == "VERIFIED"
    assert body["package_fingerprint"]
    verified = repo.get_upload(
        tenant_id=tenant.tenant_id,
        workspace_id=workspace["workspace_id"],
        dataset_id=dataset["dataset_id"],
        upload_id=created["upload_id"],
    )
    assert verified is not None
    frozen = verified.files[0].generation
    assert frozen
    # Mutate storage after verification — Evaluation input identity stays frozen.
    store.put_bytes(
        bucket="prem3-test-raw",
        object_name=upload.files[0].object_name,
        data=b"mutated!!!!!",
        content_type="text/csv",
    )
    again = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}"
        f"/uploads/{created['upload_id']}/complete",
        headers=auth_header(),
    )
    assert again.status_code == 200
    assert again.json()["status"] == "VERIFIED"
    still = repo.get_upload(
        tenant_id=tenant.tenant_id,
        workspace_id=workspace["workspace_id"],
        dataset_id=dataset["dataset_id"],
        upload_id=created["upload_id"],
    )
    assert still is not None
    assert still.files[0].generation == frozen


def test_create_evaluation_requires_verified_upload_and_server_run_id() -> None:
    client, repo, tenant, workspace, dataset, store, _signer = _paid_client()
    created = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/uploads",
        headers=auth_header(),
        json={
            "files": [
                {
                    "filename": "geo.csv",
                    "content_type": "text/csv",
                    "size_bytes": 12,
                }
            ]
        },
    ).json()
    pending = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/evaluations",
        headers=auth_header(),
        json={"upload_id": created["upload_id"]},
    )
    assert pending.status_code == 422

    upload = repo.get_upload(
        tenant_id=tenant.tenant_id,
        workspace_id=workspace["workspace_id"],
        dataset_id=dataset["dataset_id"],
        upload_id=created["upload_id"],
    )
    assert upload is not None
    store.put_bytes(
        bucket="prem3-test-raw",
        object_name=upload.files[0].object_name,
        data=b"hello,world\n",
        content_type="text/csv",
    )
    assert (
        client.post(
            f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}"
            f"/uploads/{created['upload_id']}/complete",
            headers=auth_header(),
        ).status_code
        == 200
    )
    accepted = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/evaluations",
        headers=auth_header(),
        json={"upload_id": created["upload_id"], "run_id": "run_attacker000001"},
    )
    assert accepted.status_code == 422

    created_eval = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/evaluations",
        headers=auth_header(),
        json={"upload_id": created["upload_id"]},
    )
    assert created_eval.status_code == 202, created_eval.text
    body = created_eval.json()
    assert body["run_id"].startswith("run_")
    assert body["status"] == "ACCEPTED"
    assert "gs://" not in created_eval.text.lower()
    assert body["upload_id"] == created["upload_id"]

    listed = client.get(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/evaluations",
        headers=auth_header(),
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["run_id"] == body["run_id"]

    got = client.get(f"/v1/runs/{body['run_id']}", headers=auth_header())
    assert got.status_code == 200
    assert got.json()["run_id"] == body["run_id"]

    foreign_repo_seed = seed_tenant(
        repo, provider_org="org_other", provider_user="user_other", plan_id=PlanId.PROJECT
    )
    other_tenant, other_identity = foreign_repo_seed
    foreign_client, _ = make_client(repo=repo, identity=other_identity)
    assert other_tenant.tenant_id != tenant.tenant_id
    missing = foreign_client.get(f"/v1/runs/{body['run_id']}", headers=auth_header())
    assert missing.status_code == 404


def test_upload_idempotency_key_reuses_upload() -> None:
    client, _repo, _tenant, workspace, dataset, _store, _signer = _paid_client()
    headers = {**auth_header(), "Idempotency-Key": "upload-1"}
    first = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/uploads",
        headers=headers,
        json={
            "files": [
                {"filename": "geo.csv", "content_type": "text/csv", "size_bytes": 12}
            ]
        },
    )
    second = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}/uploads",
        headers=headers,
        json={
            "files": [
                {"filename": "geo.csv", "content_type": "text/csv", "size_bytes": 12}
            ]
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["upload_id"] == second.json()["upload_id"]
