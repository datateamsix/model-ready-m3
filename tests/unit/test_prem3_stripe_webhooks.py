"""Mission 08 billing webhook security and claim-lease tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import WebhookClaimStatus, WebhookEventStatus, WebhookProvider
from app.control_plane.webhook_claim import decide_webhook_claim
from tests.unit.api_support import seed_tenant
from tests.unit.stripe_support import (
    PRICE_PROJECT,
    WEBHOOK_SECRET,
    billing_event_body,
    make_stripe_client,
    post_billing_event,
    signed_billing_headers,
)


def _checkout_object(*, tenant_id: str, customer_id: str, subscription_id: str) -> dict:
    return {
        "id": "cs_test",
        "object": "checkout.session",
        "mode": "subscription",
        "customer": customer_id,
        "subscription": subscription_id,
        "metadata": {"prem3_tenant_id": tenant_id, "prem3_plan_id": "project"},
        "payment_status": "paid",
    }


def test_billing_webhook_requires_stripe_signature() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, *_ = make_stripe_client(repo, identity)
    body = billing_event_body(
        event_id="evt_nosig",
        event_type="customer.subscription.updated",
        obj=_checkout_object(
            tenant_id=tenant.tenant_id, customer_id="cus_x", subscription_id="sub_x"
        ),
    )
    response = client.post(
        "/v1/webhooks/billing",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401
    stored = repo.get_webhook_event(
        provider=WebhookProvider.STRIPE, provider_event_id="evt_nosig"
    )
    assert stored is None


def test_invalid_stripe_signature_rejected_before_parse() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, *_ = make_stripe_client(repo, identity)
    body = billing_event_body(
        event_id="evt_bad",
        event_type="customer.subscription.updated",
        obj=_checkout_object(
            tenant_id=tenant.tenant_id, customer_id="cus_x", subscription_id="sub_x"
        ),
    )
    response = client.post(
        "/v1/webhooks/billing",
        content=body,
        headers={"Stripe-Signature": "t=1,v1=deadbeef", "Content-Type": "application/json"},
    )
    assert response.status_code == 401
    stored = repo.get_webhook_event(
        provider=WebhookProvider.STRIPE, provider_event_id="evt_bad"
    )
    assert stored is None


def test_raw_body_used_for_verification() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, *_ = make_stripe_client(repo, identity)
    signed = billing_event_body(
        event_id="evt_raw",
        event_type="customer.subscription.updated",
        obj=_checkout_object(
            tenant_id=tenant.tenant_id, customer_id="cus_x", subscription_id="sub_x"
        ),
    )
    other = billing_event_body(
        event_id="evt_raw",
        event_type="customer.subscription.deleted",
        obj=_checkout_object(
            tenant_id=tenant.tenant_id, customer_id="cus_x", subscription_id="sub_x"
        ),
    )
    headers = signed_billing_headers(signed, secret=WEBHOOK_SECRET)
    response = client.post("/v1/webhooks/billing", content=other, headers=headers)
    assert response.status_code == 401
    stored = repo.get_webhook_event(
        provider=WebhookProvider.STRIPE, provider_event_id="evt_raw"
    )
    assert stored is None


def test_invalid_webhook_causes_no_firestore_mutation() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, *_ = make_stripe_client(repo, identity)
    before = tenant.current_entitlement_snapshot_id
    client.post(
        "/v1/webhooks/billing",
        json={"id": "evt_unsigned", "type": "customer.subscription.updated"},
    )
    assert repo.get_tenant(tenant.tenant_id).current_entitlement_snapshot_id == before
    assert repo.get_subscription_projection(tenant.tenant_id) is None
    stored = repo.get_webhook_event(
        provider=WebhookProvider.STRIPE, provider_event_id="evt_unsigned"
    )
    assert stored is None


def test_duplicate_event_processed_once() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_dup",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    obj = {
        "id": "sub_dup",
        "object": "subscription",
        "customer": mapping.provider_customer_id,
        "status": "active",
        "metadata": {"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    }
    first = post_billing_event(
        client, event_id="evt_dup", event_type="customer.subscription.created", obj=obj
    )
    second = post_billing_event(
        client, event_id="evt_dup", event_type="customer.subscription.created", obj=obj
    )
    assert first.status_code == 200
    assert first.json()["result"] == "projected"
    assert second.status_code == 200
    assert second.json()["result"] == "duplicate"


def test_concurrent_event_claim_single_winner() -> None:
    repo = InMemoryControlPlaneRepository()
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(
                repo.claim_webhook_event,
                provider=WebhookProvider.STRIPE,
                provider_event_id="evt_race_billing",
                event_type="invoice.paid",
            )
            for _ in range(8)
        ]
        results = [future.result() for future in as_completed(futures)]
    winners = [item for item in results if item.status == WebhookClaimStatus.WON]
    assert len(winners) == 1


def test_stale_claim_can_be_reclaimed_after_lease() -> None:
    repo = InMemoryControlPlaneRepository()
    first = repo.claim_webhook_event(
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_lease",
        event_type="invoice.paid",
        lease_seconds=60,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert first.status == WebhookClaimStatus.WON
    stale = repo.claim_webhook_event(
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_lease",
        event_type="invoice.paid",
        lease_seconds=60,
        now=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=61),
    )
    assert stale.status == WebhookClaimStatus.WON


def test_fresh_claim_cannot_be_reclaimed() -> None:
    repo = InMemoryControlPlaneRepository()
    first = repo.claim_webhook_event(
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_fresh",
        event_type="invoice.paid",
        lease_seconds=120,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert first.status == WebhookClaimStatus.WON
    second = repo.claim_webhook_event(
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_fresh",
        event_type="invoice.paid",
        lease_seconds=120,
        now=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=30),
    )
    assert second.status == WebhookClaimStatus.ALREADY_CLAIMED


def test_failed_event_is_retryable() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    mapping = gateway.ensure_customer(tenant.tenant_id)
    stripe.set_subscription(
        "sub_fail",
        customer_id=mapping.provider_customer_id,
        price_id=PRICE_PROJECT,
        status="active",
        metadata={"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    )
    stripe.fail_retrieve = True
    obj = {
        "id": "sub_fail",
        "object": "subscription",
        "customer": mapping.provider_customer_id,
        "status": "active",
        "metadata": {"prem3_tenant_id": tenant.tenant_id, "prem3_plan_id": "project"},
    }
    first = post_billing_event(
        client, event_id="evt_retry", event_type="customer.subscription.updated", obj=obj
    )
    assert first.status_code == 503
    stored = repo.get_webhook_event(provider=WebhookProvider.STRIPE, provider_event_id="evt_retry")
    assert stored is not None
    assert stored.status == WebhookEventStatus.FAILED
    stripe.fail_retrieve = False
    second = post_billing_event(
        client, event_id="evt_retry", event_type="customer.subscription.updated", obj=obj
    )
    assert second.status_code == 200
    assert second.json()["result"] == "projected"


def test_firestore_claim_helper_matches_lease_semantics() -> None:
    """FirestoreControlPlaneRepository uses decide_webhook_claim inside a transaction."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = decide_webhook_claim(
        None,
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_fs",
        event_type="invoice.paid",
        now=now,
        lease_seconds=30,
    )
    fresh = decide_webhook_claim(
        first.event,
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_fs",
        event_type="invoice.paid",
        now=now + timedelta(seconds=10),
        lease_seconds=30,
    )
    stale = decide_webhook_claim(
        first.event,
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_fs",
        event_type="invoice.paid",
        now=now + timedelta(seconds=31),
        lease_seconds=30,
    )
    assert first.status == WebhookClaimStatus.WON
    assert fresh.status == WebhookClaimStatus.ALREADY_CLAIMED
    assert stale.status == WebhookClaimStatus.WON
