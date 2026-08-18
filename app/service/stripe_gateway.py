"""Stripe-backed BillingGateway. Checkout creation never writes entitlements."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from app.control_plane.entitlements import PAID_PLAN_IDS, PlanId
from app.control_plane.models import BillingProvider, StripeCustomerMapping
from app.control_plane.repository import ControlPlaneRepository
from app.service.billing import BillingSession
from app.service.billing_config import BillingConfig, build_redirect_url
from app.service.errors import (
    ProblemFieldError,
    billing_configuration_error,
    billing_customer_unavailable,
    billing_provider_unavailable,
    validation_error,
)
from app.service.security_log import security_log
from app.service.stripe_provider import (
    StripeProvider,
    StripeProviderConfigurationError,
    StripeProviderUnavailableError,
)


class StripeBillingGateway:
    def __init__(
        self,
        *,
        provider: StripeProvider,
        repo: ControlPlaneRepository,
        config: BillingConfig,
    ) -> None:
        self._provider = provider
        self._repo = repo
        self._config = config

    def create_checkout_session(
        self,
        *,
        tenant_id: str,
        plan_id: str,
        return_path: str | None,
        idempotency_key: str | None = None,
    ) -> BillingSession:
        if plan_id == PlanId.PLANNER or plan_id not in PAID_PLAN_IDS:
            raise validation_error(
                [ProblemFieldError(field="plan_id", message="Checkout requires a paid plan.")]
            )
        price_id = self._config.price_id_for_plan(plan_id)
        if not price_id:
            raise billing_configuration_error()
        if not self._config.frontend_origin:
            raise billing_configuration_error()
        mapping = self.ensure_customer(tenant_id)
        success_url = build_redirect_url(
            origin=self._config.frontend_origin,
            return_path=return_path,
            billing_result="success",
        )
        cancel_url = build_redirect_url(
            origin=self._config.frontend_origin,
            return_path=return_path,
            billing_result="cancel",
        )
        provider_key = scoped_idempotency_key(
            tenant_id=tenant_id,
            operation="checkout",
            client_key=idempotency_key,
        )
        try:
            session = self._provider.create_checkout_session(
                customer_id=mapping.provider_customer_id,
                price_id=price_id,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"prem3_tenant_id": tenant_id, "prem3_plan_id": plan_id},
                idempotency_key=provider_key,
            )
        except StripeProviderUnavailableError as exc:
            raise billing_provider_unavailable() from exc
        except StripeProviderConfigurationError as exc:
            raise billing_configuration_error() from exc
        return BillingSession(url=session.url, expires_at=session.expires_at)

    def create_portal_session(
        self, *, tenant_id: str, return_path: str | None
    ) -> BillingSession:
        mapping = self._repo.get_stripe_customer_mapping(tenant_id)
        if mapping is None:
            raise billing_customer_unavailable()
        if not self._config.frontend_origin:
            raise billing_configuration_error()
        return_url = build_redirect_url(
            origin=self._config.frontend_origin,
            return_path=return_path,
            billing_result="portal",
        )
        try:
            session = self._provider.create_portal_session(
                customer_id=mapping.provider_customer_id,
                return_url=return_url,
                configuration_id=self._config.portal_configuration_id,
            )
        except StripeProviderUnavailableError as exc:
            raise billing_provider_unavailable() from exc
        except StripeProviderConfigurationError as exc:
            raise billing_provider_unavailable() from exc
        return BillingSession(url=session.url, expires_at=None)

    def ensure_customer(self, tenant_id: str) -> StripeCustomerMapping:
        existing = self._repo.get_stripe_customer_mapping(tenant_id)
        if existing is not None:
            return existing
        try:
            record = self._provider.create_customer(
                tenant_id=tenant_id,
                idempotency_key=f"prem3_cust_{tenant_id}",
            )
        except StripeProviderUnavailableError as exc:
            raise billing_provider_unavailable() from exc
        except StripeProviderConfigurationError as exc:
            raise billing_configuration_error() from exc
        raced = self._repo.get_stripe_customer_mapping(tenant_id)
        if raced is not None:
            if raced.provider_customer_id != record.customer_id:
                security_log(
                    "billing.customer_mapping_conflict",
                    tenant_id=tenant_id,
                )
            return raced
        now = datetime.now(UTC)
        mapping = StripeCustomerMapping(
            tenant_id=tenant_id,
            billing_provider=BillingProvider.STRIPE,
            provider_customer_id=record.customer_id,
            created_at=now,
            updated_at=now,
        )
        return self._repo.put_stripe_customer_mapping(mapping)


def scoped_idempotency_key(*, tenant_id: str, operation: str, client_key: str | None) -> str:
    if client_key and client_key.strip():
        digest = sha256(client_key.strip().encode("utf-8")).hexdigest()[:32]
        return f"prem3:{operation}:{tenant_id}:{digest}"
    return f"prem3:{operation}:{tenant_id}:{uuid4().hex}"
