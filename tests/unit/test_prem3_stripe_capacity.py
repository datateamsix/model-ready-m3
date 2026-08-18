"""Capacity after Stripe entitlement projection. No run-credit metering."""

from __future__ import annotations

from app.control_plane.entitlements import PLAN_MAX_ACTIVE_PROJECTS, PlanId, entitlement_for_plan
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import EntitlementSource, EntitlementStatus
from tests.unit.api_support import auth_header, seed_tenant
from tests.unit.stripe_support import (
    PRICE_ENTERPRISE,
    PRICE_PORTFOLIO,
    PRICE_PROJECT,
    make_stripe_client,
    post_billing_event,
)


def _activate(plan_id: str, price_id: str, expected_max: int) -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        f"sub_{plan_id}",
        customer_id=mapping.provider_customer_id,
        price_id=price_id,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": plan_id},
    )
    post_billing_event(
        client,
        event_id=f"evt_{plan_id}",
        event_type="customer.subscription.updated",
        obj={
            "id": f"sub_{plan_id}",
            "customer": mapping.provider_customer_id,
            "status": "canceled",
            "metadata": {"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": plan_id},
        },
    )
    entitlement = repo.get_current_entitlement(tenant.tenant_id)
    assert entitlement.max_active_projects == expected_max
    me = client.get("/v1/me", headers=auth_header())
    assert me.json()["project_capacity"]["max_active_projects"] == expected_max
    created = client.post("/v1/workspaces", headers=auth_header(), json={"name": "P0"})
    assert created.status_code == 201
    if expected_max == 1:
        denied = client.post("/v1/workspaces", headers=auth_header(), json={"name": "P1"})
        assert denied.status_code == 409
        assert denied.json()["code"] == "PROJECT_LIMIT_REACHED"


def test_project_capacity_after_projection() -> None:
    _activate("project", PRICE_PROJECT, PLAN_MAX_ACTIVE_PROJECTS[PlanId.PROJECT])


def test_portfolio_capacity_after_projection() -> None:
    _activate("portfolio", PRICE_PORTFOLIO, PLAN_MAX_ACTIVE_PROJECTS[PlanId.PORTFOLIO])


def test_enterprise_capacity_after_projection() -> None:
    _activate("enterprise", PRICE_ENTERPRISE, PLAN_MAX_ACTIVE_PROJECTS[PlanId.ENTERPRISE])


def test_downgrade_does_not_delete_projects() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo, plan_id=PlanId.PORTFOLIO)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    first = client.post("/v1/workspaces", headers=auth_header(), json={"name": "A"})
    second = client.post("/v1/workspaces", headers=auth_header(), json={"name": "B"})
    assert first.status_code == 201
    assert second.status_code == 201
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_down",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    post_billing_event(
        client,
        event_id="evt_down",
        event_type="customer.subscription.updated",
        obj={
            "id": "sub_down",
            "customer": mapping.provider_customer_id,
            "metadata": {"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
        },
    )
    listed = client.get("/v1/workspaces", headers=auth_header())
    assert len(listed.json()["items"]) == 2
    denied = client.post("/v1/workspaces", headers=auth_header(), json={"name": "C"})
    assert denied.status_code == 409
    me = client.get("/v1/me", headers=auth_header())
    assert me.json()["plan"]["plan_id"] == "project"
    assert me.json()["project_capacity"]["active_projects"] == 2
    assert me.json()["project_capacity"]["max_active_projects"] == 1


def test_canceled_status_blocks_new_projects_without_deleting() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, *_ = make_stripe_client(repo, identity)
    created = client.post("/v1/workspaces", headers=auth_header(), json={"name": "Keep"})
    assert created.status_code == 201
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=tenant.tenant_id,
            plan_id=PlanId.PROJECT,
            source=EntitlementSource.BILLING_PROVIDER,
            status=EntitlementStatus.CANCELED,
        )
    )
    denied = client.post("/v1/workspaces", headers=auth_header(), json={"name": "New"})
    assert denied.status_code == 403
    assert denied.json()["code"] == "ENTITLEMENT_DENIED"
    listed = client.get("/v1/workspaces", headers=auth_header())
    assert len(listed.json()["items"]) == 1


def test_evaluations_remain_unmetered() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo, plan_id=PlanId.PROJECT)
    client, *_ = make_stripe_client(repo, identity)
    workspace = client.post("/v1/workspaces", headers=auth_header(), json={"name": "Run"}).json()
    dataset = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets",
        headers=auth_header(),
        json={"name": "D1"},
    )
    assert dataset.status_code == 201
    again = client.post(
        f"/v1/workspaces/{workspace['workspace_id']}/datasets",
        headers=auth_header(),
        json={"name": "D2"},
    )
    assert again.status_code == 201
