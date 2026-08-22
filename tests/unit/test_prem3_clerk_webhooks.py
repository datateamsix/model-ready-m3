"""Clerk identity webhook verification and projection tests."""

from __future__ import annotations

import json

from app.control_plane.entitlements import PlanId
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import MembershipStatus, TenantStatus
from app.service.clerk_runtime import FakeClerkRuntime
from tests.unit.api_support import make_clerk_client, make_client, seed_tenant, signed_clerk_headers


def _tenant_id(repo: InMemoryControlPlaneRepository, org_id: str) -> str | None:
    return repo.get_tenant_id_for_provider_org(
        provider="clerk", provider_organization_id=org_id
    )


def _post_event(
    client,
    runtime: FakeClerkRuntime,
    event: dict,
    *,
    msg_id: str = "msg_1",
    secret: str | None = None,
    tamper_signature: bool = False,
    omit_headers: bool = False,
):
    body = json.dumps(event, separators=(",", ":")).encode("utf-8")
    headers = {}
    if not omit_headers:
        headers = signed_clerk_headers(
            body, secret=secret or runtime.webhook_secret, msg_id=msg_id
        )
        if tamper_signature:
            headers["svix-signature"] = "v1,AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    return client.post("/v1/webhooks/identity", content=body, headers=headers)


def test_identity_webhook_signature_required() -> None:
    client, _, runtime = make_clerk_client()
    response = _post_event(
        client,
        runtime,
        {"type": "organization.created", "data": {"id": "org_x", "name": "X"}},
        omit_headers=True,
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_identity_webhook_invalid_signature_rejected() -> None:
    client, repo, runtime = make_clerk_client()
    response = _post_event(
        client,
        runtime,
        {"type": "organization.created", "data": {"id": "org_x", "name": "X"}},
        tamper_signature=True,
    )
    assert response.status_code == 401
    assert _tenant_id(repo, "org_x") is None


def test_identity_webhook_raw_body_verified_before_parse() -> None:
    client, _, runtime = make_clerk_client()
    raw = b'{"type":"organization.created","data":{"id":"org_raw","name":"Raw"  }}'
    headers = signed_clerk_headers(raw, secret=runtime.webhook_secret, msg_id="msg_raw")
    response = client.post("/v1/webhooks/identity", content=raw, headers=headers)
    assert response.status_code == 200
    assert response.json()["result"] == "provisioned"


def test_identity_webhook_duplicate_event_idempotent() -> None:
    client, repo, runtime = make_clerk_client()
    event = {
        "id": "evt_dup",
        "type": "organization.created",
        "data": {"id": "org_dup", "name": "Dup"},
    }
    first = _post_event(client, runtime, event, msg_id="msg_dup")
    second = _post_event(client, runtime, event, msg_id="msg_dup")
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["result"] == "duplicate"
    tenants = [
        _tenant_id(repo, "org_dup")
    ]
    assert tenants[0] is not None
    assert repo.list_workspaces_for_tenant(tenants[0]) == []


def test_org_created_creates_one_prem3_tenant() -> None:
    client, repo, runtime = make_clerk_client()
    response = _post_event(
        client,
        runtime,
        {
            "id": "evt_org",
            "type": "organization.created",
            "data": {"id": "org_new", "name": "New Co"},
        },
    )
    assert response.status_code == 200
    tenant_id = _tenant_id(repo, "org_new")
    assert tenant_id is not None
    assert tenant_id != "org_new"
    tenant = repo.get_tenant(tenant_id)
    assert tenant is not None
    assert tenant.display_name == "New Co"


def test_org_created_adds_planner_entitlement_zero_capacity() -> None:
    client, repo, runtime = make_clerk_client()
    _post_event(
        client,
        runtime,
        {"id": "evt_plan", "type": "organization.created", "data": {"id": "org_p", "name": "P"}},
    )
    tenant_id = _tenant_id(repo, "org_p")
    assert tenant_id is not None
    entitlement = repo.get_current_entitlement(tenant_id)
    assert entitlement.max_active_projects == 0
    assert entitlement.plan_id == "planner"


def test_org_created_does_not_create_workspace() -> None:
    client, repo, runtime = make_clerk_client()
    _post_event(
        client,
        runtime,
        {"id": "evt_ws", "type": "organization.created", "data": {"id": "org_w", "name": "W"}},
    )
    tenant_id = _tenant_id(repo, "org_w")
    assert tenant_id is not None
    assert repo.list_workspaces_for_tenant(tenant_id) == []
    assert repo.get_stripe_customer_mapping(tenant_id) is None


def test_membership_created_projects_active_membership() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, _ = seed_tenant(repo, provider_org="org_m", provider_user="user_other")
    runtime = FakeClerkRuntime()
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    response = _post_event(
        client,
        runtime,
        {
            "id": "evt_mem",
            "type": "organizationMembership.created",
            "data": {
                "organization": {"id": "org_m"},
                "public_user_data": {"user_id": "user_new"},
                "role": "org:member",
            },
        },
    )
    assert response.status_code == 200
    membership = repo.get_membership_projection(
        tenant_id=tenant.tenant_id, provider="clerk", provider_user_id="user_new"
    )
    assert membership is not None
    assert membership.status == MembershipStatus.ACTIVE


def test_membership_deleted_revokes_future_access() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, _ = seed_tenant(repo, provider_org="org_m", provider_user="user_acme")
    runtime = FakeClerkRuntime()
    runtime.grant("sess_ok", user_id="user_acme", organization_id="org_m")
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    assert client.get("/v1/me", headers={"Authorization": "Bearer sess_ok"}).status_code == 200
    _post_event(
        client,
        runtime,
        {
            "id": "evt_delmem",
            "type": "organizationMembership.deleted",
            "data": {
                "organization": {"id": "org_m"},
                "public_user_data": {"user_id": "user_acme"},
            },
        },
    )
    del runtime.memberships[("user_acme", "org_m")]
    denied = client.get("/v1/me", headers={"Authorization": "Bearer sess_ok"})
    assert denied.status_code == 403
    membership = repo.get_membership_projection(
        tenant_id=tenant.tenant_id, provider="clerk", provider_user_id="user_acme"
    )
    assert membership is not None
    assert membership.status == MembershipStatus.REMOVED


def test_out_of_order_membership_event_fails_or_retries_safely() -> None:
    client, repo, runtime = make_clerk_client()
    response = _post_event(
        client,
        runtime,
        {
            "id": "evt_ooo",
            "type": "organizationMembership.created",
            "data": {
                "organization": {"id": "org_missing"},
                "public_user_data": {"user_id": "user_x"},
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["result"] == "ignored_unmapped_organization"
    assert (
        _tenant_id(repo, "org_missing")
        is None
    )


def test_org_deleted_does_not_inline_delete_customer_data() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(
        repo, provider_org="org_d", provider_user="user_d", plan_id=PlanId.PROJECT
    )
    seeded_client, _ = make_client(repo=repo, identity=identity)
    created = seeded_client.post(
        "/v1/workspaces",
        json={"name": "Keep"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert created.status_code == 201
    workspace_id = created.json()["workspace_id"]
    runtime = FakeClerkRuntime()
    client, _, _ = make_clerk_client(runtime=runtime, repo=repo)
    response = _post_event(
        client,
        runtime,
        {"id": "evt_delorg", "type": "organization.deleted", "data": {"id": "org_d"}},
    )
    assert response.status_code == 200
    assert response.json()["result"] == "deletion_pending"
    stored = repo.get_tenant(tenant.tenant_id)
    assert stored is not None
    assert stored.status == TenantStatus.DISABLED
    assert (
        repo.get_workspace_for_tenant(tenant_id=tenant.tenant_id, workspace_id=workspace_id)
        is not None
    )


def test_unknown_verified_event_safe() -> None:
    client, repo, runtime = make_clerk_client()
    response = _post_event(
        client,
        runtime,
        {"id": "evt_unk", "type": "email.created", "data": {"id": "idn_x"}},
    )
    assert response.status_code == 200
    assert response.json()["result"] == "ignored"
    assert (
        _tenant_id(repo, "idn_x")
        is None
    )
