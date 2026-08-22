"""Shared Stripe billing test helpers. No live Stripe network."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.control_plane.entitlements import PlanId
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.service.billing_config import BillingConfig, CatalogPricePresentation
from app.service.billing_events import BillingWebhookProcessor
from app.service.catalog import build_plan_catalog
from app.service.stripe_gateway import StripeBillingGateway
from app.service.stripe_provider import FakeStripeProvider, sign_stripe_payload
from tests.unit.api_support import make_client

PRICE_PROJECT = "price_test_project"
PRICE_PORTFOLIO = "price_test_portfolio"
PRICE_ENTERPRISE = "price_test_enterprise"
WEBHOOK_SECRET = "whsec_test_secret"


def billing_config_for_tests() -> BillingConfig:
    return BillingConfig(
        secret_key="sk_test_fake",
        webhook_secret=WEBHOOK_SECRET,
        frontend_origin="https://app.prem3.test",
        portal_configuration_id=None,
        price_by_plan={
            PlanId.PROJECT: PRICE_PROJECT,
            PlanId.PORTFOLIO: PRICE_PORTFOLIO,
            PlanId.ENTERPRISE: PRICE_ENTERPRISE,
        },
        catalog_presentation={
            PlanId.PROJECT: CatalogPricePresentation(
                amount=9900, currency="usd", display_price="$99/mo"
            ),
            PlanId.PORTFOLIO: CatalogPricePresentation(
                amount=24900, currency="usd", display_price="$249/mo"
            ),
            PlanId.ENTERPRISE: CatalogPricePresentation(
                amount=99900, currency="usd", display_price="$999/mo"
            ),
        },
        webhook_claim_lease_seconds=120,
        stripe_timeout_seconds=10,
        stripe_max_network_retries=2,
    )


def make_stripe_stack(
    repo: InMemoryControlPlaneRepository,
    *,
    provider: FakeStripeProvider | None = None,
    config: BillingConfig | None = None,
):
    billing_config = config or billing_config_for_tests()
    stripe = provider or FakeStripeProvider(webhook_secret=billing_config.webhook_secret or "")
    stripe.seed_price(PRICE_PROJECT)
    stripe.seed_price(PRICE_PORTFOLIO, unit_amount=24900)
    stripe.seed_price(PRICE_ENTERPRISE, unit_amount=99900)
    gateway = StripeBillingGateway(provider=stripe, repo=repo, config=billing_config)
    processor = BillingWebhookProcessor(provider=stripe, repo=repo, config=billing_config)
    return stripe, gateway, processor, billing_config


def make_stripe_client(
    repo: InMemoryControlPlaneRepository,
    identity,
    *,
    provider: FakeStripeProvider | None = None,
):
    stripe, gateway, processor, config = make_stripe_stack(repo, provider=provider)
    client, _ = make_client(
        repo=repo,
        identity=identity,
        billing=gateway,
        billing_webhook_processor=processor,
        catalog=build_plan_catalog(config=config),
    )
    return client, stripe, gateway, processor


def signed_billing_headers(body: bytes, *, secret: str = WEBHOOK_SECRET) -> dict[str, str]:
    return {
        "Stripe-Signature": sign_stripe_payload(body, secret),
        "Content-Type": "application/json",
    }


def billing_event_body(
    *,
    event_id: str,
    event_type: str,
    obj: dict,
) -> bytes:
    payload = {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "data": {"object": obj},
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def post_billing_event(
    client: TestClient,
    *,
    event_id: str,
    event_type: str,
    obj: dict,
    secret: str = WEBHOOK_SECRET,
):
    body = billing_event_body(event_id=event_id, event_type=event_type, obj=obj)
    return client.post(
        "/v1/webhooks/billing",
        content=body,
        headers=signed_billing_headers(body, secret=secret),
    )


def now() -> datetime:
    return datetime.now(UTC)
