"""prem3-api identity and isolation tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.control_plane.entitlements import PlanId
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import MembershipStatus
from app.core.tenancy import current_tenant, current_workspace
from app.service.app import create_app
from tests.unit.api_support import auth_header, make_client, seed_tenant


def test_authenticated_route_fails_when_identity_provider_unconfigured() -> None:
    client, _ = make_client(unconfigured_auth=True)
    response = client.get("/v1/me", headers=auth_header())
    assert response.status_code == 503
    assert response.json()["code"] == "AUTH_PROVIDER_NOT_CONFIGURED"


def test_identity_org_maps_to_server_tenant() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, _ = make_client(repo=repo, identity=identity)
    response = client.get("/v1/me", headers=auth_header())
    assert response.status_code == 200
    body = response.json()
    assert body["organization"]["tenant_id"] == tenant.tenant_id
    assert body["organization"]["tenant_id"] != "org_acme"


def test_client_cannot_supply_tenant_authority() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, _ = make_client(repo=repo, identity=identity)
    created = client.post(
        "/v1/workspaces",
        headers=auth_header(),
        json={"name": "Mine", "tenant_id": "ten_attacker000000000"},
    )
    assert created.status_code == 422
    assert created.json()["code"] == "VALIDATION_ERROR"
    me = client.get(
        "/v1/me",
        headers={**auth_header(), "X-Tenant-ID": "ten_attacker000000000"},
        params={"tenant_id": "ten_attacker000000000"},
    )
    assert me.status_code == 200
    assert me.json()["organization"]["tenant_id"] == tenant.tenant_id


def test_inactive_membership_denied() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, membership_status=MembershipStatus.REMOVED)
    client, _ = make_client(repo=repo, identity=identity)
    response = client.get("/v1/me", headers=auth_header())
    assert response.status_code == 403
    assert response.json()["code"] == "ENTITLEMENT_DENIED"


def test_foreign_workspace_returns_not_found() -> None:
    repo = InMemoryControlPlaneRepository()
    _a, identity_a = seed_tenant(repo, provider_org="org_a", provider_user="user_a")
    b, identity_b = seed_tenant(
        repo,
        display_name="B",
        provider_org="org_b",
        provider_user="user_b",
        plan_id=PlanId.PROJECT,
    )
    client_b, _ = make_client(repo=repo, identity=identity_b)
    workspace = client_b.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "B Project"}
    ).json()
    client_a, _ = make_client(repo=repo, identity=identity_a)
    response = client_a.get(
        f"/v1/workspaces/{workspace['workspace_id']}", headers=auth_header()
    )
    assert response.status_code == 404
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"
    assert "another tenant" not in response.json()["detail"].lower()


def test_foreign_dataset_returns_not_found() -> None:
    repo = InMemoryControlPlaneRepository()
    a, identity_a = seed_tenant(
        repo, provider_org="org_a", provider_user="user_a", plan_id=PlanId.PROJECT
    )
    b, identity_b = seed_tenant(
        repo,
        display_name="B",
        provider_org="org_b",
        provider_user="user_b",
        plan_id=PlanId.PROJECT,
    )
    client_b, _ = make_client(repo=repo, identity=identity_b)
    workspace = client_b.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "B"}
    ).json()
    dataset = client_b.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets",
        headers=auth_header(),
        json={"name": "Secret"},
    ).json()
    client_a, _ = make_client(repo=repo, identity=identity_a)
    # Authorized workspace for A, then foreign dataset id.
    own = client_a.post("/v1/workspaces", headers=auth_header(), json={"name": "A"}).json()
    response = client_a.get(
        f"/v1/workspaces/{own['workspace_id']}/datasets/{dataset['dataset_id']}",
        headers=auth_header(),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"
    del a, b


def test_workspace_context_cleared_after_request() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, _ = make_client(repo=repo, identity=identity)
    workspace = client.post(
        "/v1/workspaces", headers=auth_header(), json={"name": "One"}
    ).json()
    client.get(f"/v1/workspaces/{workspace['workspace_id']}", headers=auth_header())
    assert current_workspace() is None


def test_tenant_context_cleared_after_request() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, _ = make_client(repo=repo, identity=identity)
    client.get("/v1/me", headers=auth_header())
    assert current_tenant() is None


def test_sequential_requests_do_not_leak_identity() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant_a, identity_a = seed_tenant(repo, provider_org="org_a", provider_user="user_a")
    tenant_b, identity_b = seed_tenant(
        repo, display_name="B", provider_org="org_b", provider_user="user_b"
    )
    client, _ = make_client(
        repo=repo,
        identities={"token-a": identity_a, "token-b": identity_b},
    )
    first = client.get("/v1/me", headers=auth_header("token-a"))
    second = client.get("/v1/me", headers=auth_header("token-b"))
    assert first.json()["organization"]["tenant_id"] == tenant_a.tenant_id
    assert second.json()["organization"]["tenant_id"] == tenant_b.tenant_id


def test_parallel_requests_keep_distinct_tenants() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant_a, identity_a = seed_tenant(repo, provider_org="org_a", provider_user="user_a")
    tenant_b, identity_b = seed_tenant(
        repo, display_name="B", provider_org="org_b", provider_user="user_b"
    )
    client, _ = make_client(
        repo=repo,
        identities={"token-a": identity_a, "token-b": identity_b},
    )

    def fetch(token: str) -> str:
        return client.get("/v1/me", headers=auth_header(token)).json()["organization"][
            "tenant_id"
        ]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch, "token-a") for _ in range(4)]
        futures += [pool.submit(fetch, "token-b") for _ in range(4)]
        results = [future.result() for future in as_completed(futures)]
    assert results.count(tenant_a.tenant_id) == 4
    assert results.count(tenant_b.tenant_id) == 4


def test_default_app_does_not_call_root_agent() -> None:
    app = create_app()
    assert not hasattr(app.state, "root_agent")
