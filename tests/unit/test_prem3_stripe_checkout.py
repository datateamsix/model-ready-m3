"""Mission 08 Stripe Checkout tests. Fake provider only."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.control_plane.entitlements import PlanId
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import EntitlementSource
from app.service.stripe_gateway import StripeBillingGateway
from tests.unit.api_support import auth_header, make_client, seed_tenant
from tests.unit.stripe_support import (
    PRICE_PROJECT,
    make_stripe_client,
    make_stripe_stack,
)


def test_checkout_requires_verified_tenant() -> None:
    from app.service.auth import VerifiedIdentity

    repo = InMemoryControlPlaneRepository()
    identity = VerifiedIdentity(
        provider="clerk",
        provider_user_id="user_nomap",
        provider_organization_id="org_nomap",
    )
    client, _stripe, _gateway, _processor = make_stripe_client(repo, identity)
    response = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "project"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "TENANT_NOT_FOUND"


def test_checkout_rejects_planner_plan() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo, plan_id=PlanId.PLANNER)
    client, *_ = make_stripe_client(repo, identity)
    response = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "planner"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_checkout_unknown_plan_rejected() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, *_ = make_stripe_client(repo, identity)
    response = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "platinum"},
    )
    assert response.status_code == 422


def test_checkout_uses_server_price_mapping() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, stripe, *_ = make_stripe_client(repo, identity)
    response = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "project"},
    )
    assert response.status_code == 200
    assert stripe.checkout_sessions[-1].price_id == PRICE_PROJECT
    assert stripe.checkout_sessions[-1].mode == "subscription"


def test_checkout_does_not_accept_price_id() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, *_ = make_stripe_client(repo, identity)
    rejected = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "project", "stripe_price_id": "price_evil"},
    )
    assert rejected.status_code == 422


def test_checkout_creates_or_reuses_tenant_customer() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, *_ = make_stripe_client(repo, identity)
    first = client.post(
        "/v1/billing/checkout-session", headers=auth_header(), json={"plan_id": "project"}
    )
    second = client.post(
        "/v1/billing/checkout-session", headers=auth_header(), json={"plan_id": "project"}
    )
    assert first.status_code == 200
    assert second.status_code == 200
    mapping = repo.get_stripe_customer_mapping(tenant.tenant_id)
    assert mapping is not None
    assert mapping.provider_customer_id == stripe.checkout_sessions[0].customer_id
    assert mapping.provider_customer_id == stripe.checkout_sessions[1].customer_id
    assert mapping.tenant_id != mapping.provider_customer_id


def test_concurrent_customer_provisioning_is_idempotent() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, _identity = seed_tenant(repo)
    stripe, gateway, _processor, _config = make_stripe_stack(repo)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: gateway.ensure_customer(tenant.tenant_id), range(8)))
    customer_ids = {item.provider_customer_id for item in results}
    assert len(customer_ids) == 1
    assert stripe.create_customer_calls >= 1
    stored = repo.get_stripe_customer_mapping(tenant.tenant_id)
    assert stored is not None
    assert stored.provider_customer_id == results[0].provider_customer_id


def test_checkout_uses_subscription_mode() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, stripe, *_ = make_stripe_client(repo, identity)
    client.post(
        "/v1/billing/checkout-session", headers=auth_header(), json={"plan_id": "project"}
    )
    assert stripe.checkout_sessions[-1].mode == "subscription"


def test_checkout_redirect_is_server_owned() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, stripe, gateway, _ = make_stripe_client(repo, identity)
    response = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "project", "return_path": "/app"},
    )
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://checkout.stripe.test/")
    assert isinstance(gateway, StripeBillingGateway)
    del stripe


def test_checkout_absolute_return_url_rejected() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, *_ = make_stripe_client(repo, identity)
    rejected = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "project", "return_path": "https://evil.example/phish"},
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "VALIDATION_ERROR"


def test_checkout_session_creation_does_not_grant_entitlement() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo, plan_id=PlanId.PLANNER)
    before = tenant.current_entitlement_snapshot_id
    client, *_ = make_stripe_client(repo, identity)
    response = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "project", "return_path": "/app?billing=success"},
    )
    assert response.status_code == 200
    me = client.get("/v1/me", headers=auth_header())
    assert me.status_code == 200
    assert me.json()["plan"]["plan_id"] == "planner"
    refreshed = repo.get_tenant(tenant.tenant_id)
    assert refreshed is not None
    assert refreshed.current_entitlement_snapshot_id == before
    entitlement = repo.get_current_entitlement(tenant.tenant_id)
    assert entitlement.source == EntitlementSource.DEFAULT


def test_checkout_success_return_is_not_authorization() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    before = tenant.current_entitlement_snapshot_id
    client, *_ = make_stripe_client(repo, identity)
    checkout = client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "project", "return_path": "/app"},
    )
    assert checkout.status_code == 200
    # Frontend would land on the success URL. prem3-api has no success handler.
    me = client.get("/v1/me", headers=auth_header())
    assert me.json()["plan"]["plan_id"] == "planner"
    assert repo.get_tenant(tenant.tenant_id).current_entitlement_snapshot_id == before


def test_checkout_provider_failure_returns_stable_problem() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, stripe, *_ = make_stripe_client(repo, identity)
    stripe.fail_checkout = True
    response = client.post(
        "/v1/billing/checkout-session", headers=auth_header(), json={"plan_id": "project"}
    )
    assert response.status_code == 503
    assert response.json()["code"] == "BILLING_PROVIDER_UNAVAILABLE"
    assert "stripe" not in response.json()["detail"].lower()


def test_checkout_uses_provider_idempotency() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    client, stripe, *_ = make_stripe_client(repo, identity)
    headers = {**auth_header(), "Idempotency-Key": "client-key-1"}
    first = client.post(
        "/v1/billing/checkout-session", headers=headers, json={"plan_id": "project"}
    )
    second = client.post(
        "/v1/billing/checkout-session", headers=headers, json={"plan_id": "project"}
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["url"] == second.json()["url"]
    assert stripe.last_checkout_idempotency_key is not None
    assert "client-key-1" not in stripe.last_checkout_idempotency_key
    assert stripe.checkout_sessions[0].idempotency_key == stripe.last_checkout_idempotency_key


def test_checkout_missing_price_is_configuration_error() -> None:
    repo = InMemoryControlPlaneRepository()
    _tenant, identity = seed_tenant(repo)
    stripe, _gateway, processor, config = make_stripe_stack(repo)
    empty = config.__class__(
        secret_key=config.secret_key,
        webhook_secret=config.webhook_secret,
        frontend_origin=config.frontend_origin,
        portal_configuration_id=config.portal_configuration_id,
        price_by_plan={},
        catalog_presentation=config.catalog_presentation,
        webhook_claim_lease_seconds=config.webhook_claim_lease_seconds,
        stripe_timeout_seconds=config.stripe_timeout_seconds,
        stripe_max_network_retries=config.stripe_max_network_retries,
    )
    gateway = StripeBillingGateway(provider=stripe, repo=repo, config=empty)
    client, _ = make_client(
        repo=repo,
        identity=identity,
        billing=gateway,
        billing_webhook_processor=processor,
    )
    response = client.post(
        "/v1/billing/checkout-session", headers=auth_header(), json={"plan_id": "project"}
    )
    assert response.status_code == 503
    assert response.json()["code"] == "BILLING_CONFIGURATION_ERROR"
