"""Mission 08 subscription readback and entitlement projection tests."""

from __future__ import annotations

from app.control_plane.entitlements import PlanId
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import EntitlementStatus
from tests.unit.api_support import seed_tenant
from tests.unit.stripe_support import (
    PRICE_ENTERPRISE,
    PRICE_PROJECT,
    make_stripe_client,
    post_billing_event,
)


def _sub_obj(tenant_id: str, customer_id: str, subscription_id: str, status: str) -> dict:
    return {
        "id": subscription_id,
        "object": "subscription",
        "customer": customer_id,
        "status": status,
        "metadata": {"prem3_tenant_id": tenant_id, "prem3_plan_id": "project"},
    }


def test_checkout_completed_triggers_subscription_readback() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_co",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    obj = {
        "id": "cs_1",
        "object": "checkout.session",
        "mode": "subscription",
        "customer": mapping.provider_customer_id,
        "subscription": "sub_co",
        "payment_status": "paid",
        "metadata": {"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    }
    response = post_billing_event(
        client, event_id="evt_co", event_type="checkout.session.completed", obj=obj
    )
    assert response.status_code == 200
    assert response.json()["result"] == "projected"
    entitlement = repo.get_current_entitlement(tenant.tenant_id)
    assert entitlement.plan_id == PlanId.PROJECT
    assert entitlement.status == EntitlementStatus.ACTIVE


def test_subscription_created_projects_current_provider_state() -> None:
    _project_from_event("customer.subscription.created", "active", EntitlementStatus.ACTIVE)


def test_subscription_updated_projects_current_provider_state() -> None:
    _project_from_event("customer.subscription.updated", "past_due", EntitlementStatus.PAST_DUE)


def test_subscription_deleted_projects_non_active_entitlement() -> None:
    _project_from_event("customer.subscription.deleted", "canceled", EntitlementStatus.CANCELED)


def test_payment_failure_projects_degraded_state() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_pay",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="past_due",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    obj = {
        "id": "in_1",
        "object": "invoice",
        "customer": mapping.provider_customer_id,
        "subscription": "sub_pay",
        "status": "open",
        "metadata": {"prem3_tenant_id": tenant.tenant_id},
    }
    response = post_billing_event(
        client, event_id="evt_payfail", event_type="invoice.payment_failed", obj=obj
    )
    assert response.status_code == 200
    assert repo.get_current_entitlement(tenant.tenant_id).status == EntitlementStatus.PAST_DUE


def test_event_payload_status_is_not_direct_authority() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_auth",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    obj = _sub_obj(tenant.tenant_id, mapping.provider_customer_id, "sub_auth", "past_due")
    post_billing_event(
        client, event_id="evt_payload", event_type="customer.subscription.updated", obj=obj
    )
    assert repo.get_current_entitlement(tenant.tenant_id).status == EntitlementStatus.ACTIVE
    assert repo.get_subscription_projection(tenant.tenant_id).status == "active"


def test_unknown_price_fails_closed() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    before = tenant.current_entitlement_snapshot_id
    stripe.set_subscription(
        "sub_unk",
        customer_id=mapping.provider_customer_id,
        price_id="price_unknown_enterprise",
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "enterprise"},
    )
    obj = _sub_obj(tenant.tenant_id, mapping.provider_customer_id, "sub_unk", "active")
    response = post_billing_event(
        client, event_id="evt_unk", event_type="customer.subscription.updated", obj=obj
    )
    assert response.status_code == 200
    assert response.json()["result"] == "rejected_unknown_price"
    assert repo.get_tenant(tenant.tenant_id).current_entitlement_snapshot_id == before


def test_price_metadata_mismatch_fails_closed() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    before = tenant.current_entitlement_snapshot_id
    stripe.set_subscription(
        "sub_mm",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "enterprise"},
    )
    obj = _sub_obj(tenant.tenant_id, mapping.provider_customer_id, "sub_mm", "active")
    obj["metadata"]["prem3_plan_id"] = "enterprise"
    response = post_billing_event(
        client, event_id="evt_mm", event_type="customer.subscription.updated", obj=obj
    )
    assert response.status_code == 200
    assert response.json()["result"] == "rejected_price_metadata_mismatch"
    assert repo.get_tenant(tenant.tenant_id).current_entitlement_snapshot_id == before


def test_subscription_customer_must_match_tenant_mapping() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_other",
        customer_id="cus_other_tenant",
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    obj = _sub_obj(tenant.tenant_id, "cus_other_tenant", "sub_other", "active")
    response = post_billing_event(
        client, event_id="evt_cust", event_type="customer.subscription.updated", obj=obj
    )
    assert response.json()["result"] == "rejected_unmapped_customer"
    assert repo.get_current_entitlement(tenant.tenant_id).plan_id == PlanId.PLANNER


def test_out_of_order_events_converge_to_current_provider_state() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_oo",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    updated = _sub_obj(tenant.tenant_id, mapping.provider_customer_id, "sub_oo", "incomplete")
    checkout = {
        "id": "cs_oo",
        "object": "checkout.session",
        "customer": mapping.provider_customer_id,
        "subscription": "sub_oo",
        "payment_status": "unpaid",
        "metadata": {"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    }
    post_billing_event(
        client, event_id="evt_upd_first", event_type="customer.subscription.updated", obj=updated
    )
    post_billing_event(
        client, event_id="evt_co_second", event_type="checkout.session.completed", obj=checkout
    )
    assert repo.get_current_entitlement(tenant.tenant_id).status == EntitlementStatus.ACTIVE
    failed = {
        "id": "in_late",
        "object": "invoice",
        "customer": mapping.provider_customer_id,
        "subscription": "sub_oo",
        "status": "open",
        "metadata": {"prem3_tenant_id": tenant.tenant_id},
    }
    post_billing_event(
        client, event_id="evt_fail_late", event_type="invoice.payment_failed", obj=failed
    )
    assert repo.get_current_entitlement(tenant.tenant_id).status == EntitlementStatus.ACTIVE


def test_identical_reconciliation_does_not_create_duplicate_snapshot() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_same",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    obj = _sub_obj(tenant.tenant_id, mapping.provider_customer_id, "sub_same", "canceled")
    first = post_billing_event(
        client, event_id="evt_same_1", event_type="customer.subscription.updated", obj=obj
    )
    snapshot_id = repo.get_tenant(tenant.tenant_id).current_entitlement_snapshot_id
    second = post_billing_event(
        client, event_id="evt_same_2", event_type="invoice.paid", obj={
            "id": "in_same",
            "customer": mapping.provider_customer_id,
            "subscription": "sub_same",
            "metadata": {"prem3_tenant_id": tenant.tenant_id},
        }
    )
    assert first.json()["result"] == "projected"
    assert second.json()["result"] == "unchanged"
    assert repo.get_tenant(tenant.tenant_id).current_entitlement_snapshot_id == snapshot_id


def test_material_change_creates_new_entitlement_snapshot() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_chg",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    obj = _sub_obj(tenant.tenant_id, mapping.provider_customer_id, "sub_chg", "ignored")
    post_billing_event(
        client, event_id="evt_chg_1", event_type="customer.subscription.updated", obj=obj
    )
    first_id = repo.get_tenant(tenant.tenant_id).current_entitlement_snapshot_id
    stripe.set_subscription(
        "sub_chg",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="past_due",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    post_billing_event(
        client, event_id="evt_chg_2", event_type="customer.subscription.updated", obj=obj
    )
    second_id = repo.get_tenant(tenant.tenant_id).current_entitlement_snapshot_id
    assert first_id != second_id
    assert repo.get_current_entitlement(tenant.tenant_id).status == EntitlementStatus.PAST_DUE


def test_old_entitlement_snapshot_remains_immutable() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_im",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    obj = _sub_obj(tenant.tenant_id, mapping.provider_customer_id, "sub_im", "active")
    post_billing_event(
        client, event_id="evt_im_1", event_type="customer.subscription.updated", obj=obj
    )
    first_id = repo.get_tenant(tenant.tenant_id).current_entitlement_snapshot_id
    first = repo.get_entitlement_snapshot(tenant_id=tenant.tenant_id, snapshot_id=first_id)
    stripe.set_subscription(
        "sub_im",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_ENTERPRISE,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "enterprise"},
    )
    obj["metadata"]["prem3_plan_id"] = "enterprise"
    post_billing_event(
        client, event_id="evt_im_2", event_type="customer.subscription.updated", obj=obj
    )
    stored = repo.get_entitlement_snapshot(tenant_id=tenant.tenant_id, snapshot_id=first_id)
    assert stored is not None
    assert stored.plan_id == PlanId.PROJECT
    assert stored.max_active_projects == 1
    assert stored.snapshot_id == first.snapshot_id
    assert repo.get_current_entitlement(tenant.tenant_id).plan_id == PlanId.ENTERPRISE


def _project_from_event(event_type: str, provider_status: str, expected: EntitlementStatus) -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_std",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status=provider_status,
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    obj = _sub_obj(tenant.tenant_id, mapping.provider_customer_id, "sub_std", "ignored-payload")
    response = post_billing_event(
        client,
        event_id=f"evt_{provider_status}",
        event_type=event_type,
        obj=obj,
    )
    assert response.status_code == 200
    assert repo.get_current_entitlement(tenant.tenant_id).status == expected
