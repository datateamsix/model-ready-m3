"""prem3-api workspace and Dataset resource tests."""

from __future__ import annotations

from app.control_plane.entitlements import PlanId
from app.control_plane.memory import InMemoryControlPlaneRepository
from tests.unit.api_support import auth_header, make_client, seed_tenant


def test_list_workspaces_is_tenant_scoped() -> None:
    repo = InMemoryControlPlaneRepository()
    _a, identity_a = seed_tenant(
        repo, provider_org="org_a", provider_user="user_a", plan_id=PlanId.PROJECT
    )
    _b, identity_b = seed_tenant(
        repo,
        display_name="B",
        provider_org="org_b",
        provider_user="user_b",
        plan_id=PlanId.PROJECT,
    )
    client_b, _ = make_client(repo=repo, identity=identity_b)
    client_b.post("/v1/workspaces", headers=auth_header(), json={"name": "Only B"})
    client_a, _ = make_client(repo=repo, identity=identity_a)
    listed = client_a.get("/v1/workspaces", headers=auth_header()).json()
    assert listed["items"] == []


def test_create_workspace_generates_server_id() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, _ = make_client(repo=repo, identity=identity)
    response = client.post(
        "/v1/workspaces",
        headers=auth_header(),
        json={"name": "Campaign", "workspace_id": "wsp_clientchosen00000"},
    )
    assert response.status_code == 422
    created = client.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "Campaign"}
    )
    assert created.status_code == 201
    assert created.json()["workspace_id"].startswith("wsp_")
    assert created.json()["workspace_id"] != "wsp_clientchosen00000"


def test_create_workspace_enforces_project_capacity() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, _ = make_client(repo=repo, identity=identity)
    first = client.post("/v1/workspaces", headers=auth_header(), json={"name": "One"})
    second = client.post("/v1/workspaces", headers=auth_header(), json={"name": "Two"})
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "PROJECT_LIMIT_REACHED"


def test_project_limit_returns_stable_problem_code() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, _ = make_client(repo=repo, identity=identity)
    response = client.post("/v1/workspaces", headers=auth_header(), json={"name": "No"})
    assert response.status_code == 409
    assert response.json()["code"] == "PROJECT_LIMIT_REACHED"


def test_get_workspace_authorized() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, _ = make_client(repo=repo, identity=identity)
    created = client.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "Home"}
    ).json()
    fetched = client.get(
        f"/v1/workspaces/{created['workspace_id']}", headers=auth_header()
    )
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Home"


def test_list_datasets_workspace_scoped() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PORTFOLIO)
    client, _ = make_client(repo=repo, identity=identity)
    a = client.post("/v1/workspaces", headers=auth_header(), json={"name": "A"}).json()
    b = client.post("/v1/workspaces", headers=auth_header(), json={"name": "B"}).json()
    client.post(
        f"/v1/workspaces/{a['workspace_id']}/datasets",
        headers=auth_header(),
        json={"name": "Only A"},
    )
    listed = client.get(
        f"/v1/workspaces/{b['workspace_id']}/datasets", headers=auth_header()
    ).json()
    assert listed["items"] == []


def test_create_dataset_generates_server_id() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, _ = make_client(repo=repo, identity=identity)
    workspace = client.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "W"}
    ).json()
    rejected = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets",
        headers=auth_header(),
        json={"name": "Input", "dataset_id": "dset_client0000000000"},
    )
    assert rejected.status_code == 422
    created = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets",
        headers=auth_header(),
        json={"name": "Input"},
    )
    assert created.status_code == 201
    assert created.json()["dataset_id"].startswith("dset_")


def test_dataset_does_not_consume_project_capacity() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, _ = make_client(repo=repo, identity=identity)
    workspace = client.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "Only"}
    ).json()
    for index in range(3):
        created = client.post(
            f"/v1/workspaces/{workspace['workspace_id']}/datasets",
            headers=auth_header(),
            json={"name": f"D{index}"},
        )
        assert created.status_code == 201
    second_project = client.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "Two"}
    )
    assert second_project.status_code == 409
    assert second_project.json()["code"] == "PROJECT_LIMIT_REACHED"


def test_get_dataset_authorized() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, _ = make_client(repo=repo, identity=identity)
    workspace = client.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "W"}
    ).json()
    dataset = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets",
        headers=auth_header(),
        json={"name": "Input"},
    ).json()
    fetched = client.get(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets/{dataset['dataset_id']}",
        headers=auth_header(),
    )
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Input"


def test_cross_workspace_dataset_returns_not_found() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PORTFOLIO)
    client, _ = make_client(repo=repo, identity=identity)
    a = client.post("/v1/workspaces", headers=auth_header(), json={"name": "A"}).json()
    b = client.post("/v1/workspaces", headers=auth_header(), json={"name": "B"}).json()
    dataset = client.post(
        f"/v1/workspaces/{a['workspace_id']}/datasets",
        headers=auth_header(),
        json={"name": "Pinned"},
    ).json()
    response = client.get(
        f"/v1/workspaces/{b['workspace_id']}/datasets/{dataset['dataset_id']}",
        headers=auth_header(),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"
