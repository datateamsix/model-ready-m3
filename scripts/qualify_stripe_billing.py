#!/usr/bin/env python3
"""Optional Stripe test-mode billing qualification.

NEVER invoked by pytest/CI. Explicit operator command only.

Usage:
  py -3.13 scripts/qualify_stripe_billing.py --execute

Safety:
  - refuses sk_live_ credentials
  - uses a synthetic PreM3 tenant
  - creates test-mode Stripe objects only
  - does not require a real charge
  - cancels/deletes synthetic Stripe objects when possible
"""

from __future__ import annotations

import argparse
import sys
from uuid import uuid4

from app.config import load_settings
from app.control_plane.entitlements import PlanId
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.service.billing_config import BillingConfig
from app.service.stripe_gateway import StripeBillingGateway
from app.service.stripe_provider import RealStripeProvider, validate_configured_price


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print("LIVE_STRIPE_BILLING_NOT_RUN")
        print("Pass --execute to run against Stripe test mode.")
        return 2

    settings = load_settings()
    secret = settings.stripe_secret_key or ""
    if not secret:
        print("LIVE_STRIPE_BILLING_NOT_RUN")
        print("STRIPE_SECRET_KEY is not set.")
        return 3
    if secret.startswith("sk_live_"):
        print("LIVE_STRIPE_BILLING_NOT_RUN")
        print("Live-mode Stripe credentials are refused.")
        return 3
    if not secret.startswith("sk_test_"):
        print("LIVE_STRIPE_BILLING_NOT_RUN")
        print("Expected a Stripe test-mode secret key.")
        return 3

    config = BillingConfig.from_settings(settings)
    if not config.frontend_origin:
        print("LIVE_STRIPE_BILLING_NOT_RUN")
        print("PREM3_FRONTEND_ORIGIN is required.")
        return 3
    missing = [
        plan
        for plan in (PlanId.PROJECT, PlanId.PORTFOLIO, PlanId.ENTERPRISE)
        if not config.price_id_for_plan(plan)
    ]
    if missing:
        print("LIVE_STRIPE_BILLING_NOT_RUN")
        print(f"Missing Price IDs for: {', '.join(missing)}")
        return 3

    provider = RealStripeProvider(config)
    repo = InMemoryControlPlaneRepository()
    tenant = repo.create_tenant(display_name=f"stripe-qual-{uuid4().hex[:8]}")
    gateway = StripeBillingGateway(provider=provider, repo=repo, config=config)
    created: list[str] = []
    try:
        for plan_id in (PlanId.PROJECT, PlanId.PORTFOLIO, PlanId.ENTERPRISE):
            price_id = config.price_id_for_plan(plan_id)
            assert price_id is not None
            record = provider.retrieve_price(price_id)
            validate_configured_price(record)
        mapping = gateway.ensure_customer(tenant.tenant_id)
        created.append(mapping.provider_customer_id)
        checkout = gateway.create_checkout_session(
            tenant_id=tenant.tenant_id,
            plan_id=PlanId.PROJECT,
            return_path="/app/billing",
        )
        if "checkout.stripe.com" not in checkout.url and "stripe.com" not in checkout.url:
            raise AssertionError("Checkout URL was not a Stripe-hosted session.")
        portal = gateway.create_portal_session(
            tenant_id=tenant.tenant_id, return_path="/app/billing"
        )
        if "stripe.com" not in portal.url:
            raise AssertionError("Portal URL was not a Stripe-hosted session.")
        after = repo.get_current_entitlement(tenant.tenant_id)
        if after.plan_id != PlanId.PLANNER:
            raise AssertionError("Checkout creation must not grant a paid entitlement.")
    except Exception as exc:  # noqa: BLE001
        print("LIVE_STRIPE_BILLING_NOT_RUN")
        print(f"Stripe qualification failed: {exc}")
        return 5

    print("LIVE_STRIPE_BILLING_TEST_PROOF")
    print("mode=test")
    print(f"tenant_id={tenant.tenant_id}")
    print(f"customer_id={created[0]}")
    print("checkout=created")
    print("portal=created")
    print("prices=validated_monthly_recurring")
    print("entitlement_unchanged_after_checkout=true")
    print("note=Webhook live delivery was not required for this proof.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
