"""Clerk session verification and tenant-authority tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import MembershipStatus, TenantStatus
from app.core.tenancy import current_tenant
from app.service.clerk_runtime import FakeClerkRuntime
from tests.unit.api_support import auth_header, make_clerk_client, seed_tenant


def test_missing_bearer_token_denied() -> None:
    client, _, runtime = make_clerk_client()
    runtime.grant("sess_ok", user_id="user_a", organization_id="org_a")
    response = client.get("/v1/me")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_invalid_clerk_token_denied() -> None:
    client, _, _ = make_clerk_client()
    response = client.get("/v1/me", headers=auth_header("not-a-session"))
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_expired_token_denied() -> None:
    runtime = FakeClerkRuntime()
    runtime.expired_tokens.add("expired")
    client, _, _ = make_clerk_client(runtime=runtime)
    response = client.get("/v1/me", headers=auth_header("expired"))
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_wrong_authorized_party_denied() -> None:
    runtime = FakeClerkRuntime()
    runtime.wrong_azp_tokens.add("bad-azp")
    client, _, _ = make_clerk_client(runtime=runtime)
    response = client.get("/v1/me", headers=auth_header("bad-azp"))
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_machine_token_not_accepted_as_user_session() -> None:
    runtime = FakeClerkRuntime()
    runtime.machine_tokens.add("m2m_machine")
    client, _, _ = make_clerk_client(runtime=runtime)
    response = client.get("/v1/me", headers=auth_header("m2m_machine"))
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_clerk_org_required_for_tenant_access() -> None:
    runtime = FakeClerkRuntime()
    runtime.no_org_tokens.add("no-org")
    client, _, _ = make_clerk_client(runtime=runtime)
    response = client.get("/v1/me", headers=auth_header("no-org"))
    assert response.status_code == 403
    assert response.json()["code"] == "ORGANIZATION_CONTEXT_REQUIRED"


def test_clerk_org_maps_to_prem3_tenant() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, _ = seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    response = client.get("/v1/me", headers=auth_header("sess_ok"))
    assert response.status_code == 200
    assert response.json()["organization"]["tenant_id"] == tenant.tenant_id


def test_clerk_org_id_is_not_tenant_id() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, _ = seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    body = client.get("/v1/me", headers=auth_header("sess_ok")).json()
    assert body["organization"]["tenant_id"] != "org_acme"
    assert body["organization"]["tenant_id"] == tenant.tenant_id
    assert body["user"]["user_id"] == "user_acme"


def test_current_membership_required() -> None:
    repo = InMemoryControlPlaneRepository()
    seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    del runtime.memberships[("user_acme", "org_acme")]
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    response = client.get("/v1/me", headers=auth_header("sess_ok"))
    assert response.status_code == 403
    assert response.json()["code"] == "ENTITLEMENT_DENIED"


def test_removed_membership_denied_even_if_token_has_old_org_claim() -> None:
    repo = InMemoryControlPlaneRepository()
    seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    identity = runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    del runtime.memberships[(identity.provider_user_id, identity.provider_organization_id)]
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    response = client.get("/v1/me", headers=auth_header("sess_ok"))
    assert response.status_code == 403
    membership = repo.get_membership_projection(
        tenant_id=repo.get_tenant_id_for_provider_org(
            provider="clerk", provider_organization_id="org_acme"
        )
        or "",
        provider="clerk",
        provider_user_id="user_acme",
    )
    assert membership is not None
    assert membership.status == MembershipStatus.REMOVED


def test_provider_membership_failure_fails_closed() -> None:
    repo = InMemoryControlPlaneRepository()
    seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    runtime.membership_unavailable = True
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    response = client.get("/v1/me", headers=auth_header("sess_ok"))
    assert response.status_code == 503
    assert response.json()["code"] == "AUTH_PROVIDER_UNAVAILABLE"


def test_client_cannot_override_tenant() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, _ = seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    response = client.get(
        "/v1/me",
        headers={**auth_header("sess_ok"), "X-Tenant-ID": "ten_attacker000000000"},
        params={"tenant_id": "ten_attacker000000000"},
    )
    assert response.status_code == 200
    assert response.json()["organization"]["tenant_id"] == tenant.tenant_id


def test_client_cannot_override_org() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, _ = seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    created = client.post(
        "/v1/workspaces",
        headers=auth_header("sess_ok"),
        json={"name": "Nope", "organization_id": "org_other"},
    )
    assert created.status_code == 422
    me = client.get("/v1/me", headers=auth_header("sess_ok"))
    assert me.json()["organization"]["tenant_id"] == tenant.tenant_id


def test_tenant_context_bound_from_verified_identity() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, _ = seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    body = client.get("/v1/me", headers=auth_header("sess_ok")).json()
    assert body["organization"]["tenant_id"] == tenant.tenant_id
    assert body["user"]["user_id"] == "user_acme"


def test_tenant_context_cleared_after_request() -> None:
    repo = InMemoryControlPlaneRepository()
    seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    client.get("/v1/me", headers=auth_header("sess_ok"))
    assert current_tenant() is None


def test_parallel_authenticated_requests_do_not_cross_tenants() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant_a, _ = seed_tenant(repo, provider_org="org_a", provider_user="user_a")
    tenant_b, _ = seed_tenant(
        repo, display_name="B", provider_org="org_b", provider_user="user_b"
    )
    runtime = FakeClerkRuntime()
    runtime.grant("token-a", user_id="user_a", organization_id="org_a")
    runtime.grant("token-b", user_id="user_b", organization_id="org_b")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)

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


def test_disabled_tenant_is_not_accessible() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, _ = seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    repo.set_tenant_status(tenant_id=tenant.tenant_id, status=TenantStatus.DISABLED.value)
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    response = client.get("/v1/me", headers=auth_header("sess_ok"))
    assert response.status_code == 404
    assert response.json()["code"] == "TENANT_NOT_FOUND"


def test_authenticated_checkout_still_fails_closed_without_stripe() -> None:
    repo = InMemoryControlPlaneRepository()
    seed_tenant(repo, provider_org="org_acme", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_acme")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    response = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header("sess_ok"),
        json={"plan_id": "project"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "BILLING_PROVIDER_NOT_CONFIGURED"
