"""Signature-verified Stripe webhook reconciliation.

Webhook payloads are a reason to read the current Subscription. They are not
entitlement authority.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.control_plane.entitlements import (
    UnsupportedSubscriptionStatusError,
    entitlements_materially_equal,
    project_subscription_to_entitlement,
    projections_materially_equal,
)
from app.control_plane.models import (
    BillingProvider,
    StripeCustomerMapping,
    SubscriptionProjection,
    WebhookClaimStatus,
    WebhookProvider,
)
from app.control_plane.repository import ControlPlaneRepository
from app.control_plane.webhook_claim import DEFAULT_WEBHOOK_CLAIM_LEASE_SECONDS
from app.core.errors import EntitlementUnavailableError
from app.service.billing_config import ALLOWED_METADATA_KEYS, BillingConfig
from app.service.errors import APIError, auth_required, billing_provider_unavailable
from app.service.security_log import security_log
from app.service.stripe_provider import (
    HANDLED_BILLING_EVENTS,
    StripeProvider,
    StripeProviderUnavailableError,
    StripeSubscriptionNotFoundError,
    StripeWebhookSignatureError,
    extract_customer_id,
    extract_subscription_id,
)


class BillingWebhookProcessor:
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

    def process(self, *, payload: bytes, signature: str | None) -> str:
        secret = self._config.webhook_secret
        if not secret:
            raise auth_required()
        if not signature:
            security_log("billing.webhook_rejected", reason="missing_signature")
            raise auth_required()
        try:
            event = self._provider.verify_webhook(
                payload=payload, signature=signature, secret=secret
            )
        except StripeWebhookSignatureError:
            security_log("billing.webhook_rejected", reason="invalid_signature")
            raise auth_required() from None
        if not event.event_id:
            security_log("billing.webhook_rejected", reason="missing_event_id")
            raise auth_required()
        claim = self._repo.claim_webhook_event(
            provider=WebhookProvider.STRIPE,
            provider_event_id=event.event_id,
            event_type=event.event_type,
            lease_seconds=self._config.webhook_claim_lease_seconds
            or DEFAULT_WEBHOOK_CLAIM_LEASE_SECONDS,
        )
        if claim.status == WebhookClaimStatus.ALREADY_PROCESSED:
            security_log("billing.webhook_duplicate", event_type=event.event_type)
            return "duplicate"
        if claim.status == WebhookClaimStatus.ALREADY_CLAIMED:
            security_log("billing.webhook_already_claimed", event_type=event.event_type)
            raise billing_provider_unavailable()
        try:
            result = self._dispatch(event.event_type, event.data_object)
        except APIError:
            self._repo.mark_webhook_event_failed(
                provider=WebhookProvider.STRIPE,
                provider_event_id=event.event_id,
                result="provider_unavailable",
            )
            raise
        except Exception:
            self._repo.mark_webhook_event_failed(
                provider=WebhookProvider.STRIPE,
                provider_event_id=event.event_id,
                result="failed",
            )
            raise
        self._repo.mark_webhook_event_processed(
            provider=WebhookProvider.STRIPE,
            provider_event_id=event.event_id,
            result=result,
        )
        security_log("billing.webhook_accepted", event_type=event.event_type, result=result)
        return result

    def _dispatch(self, event_type: str, obj: dict[str, Any]) -> str:
        if event_type not in HANDLED_BILLING_EVENTS:
            return "ignored"
        if event_type == "checkout.session.completed":
            self._reconcile_checkout_customer(obj)
        subscription_id = extract_subscription_id(event_type, obj)
        if subscription_id is None:
            return "ignored_no_subscription"
        return self.reconcile_subscription(
            subscription_id=subscription_id,
            event_object=obj,
        )

    def _reconcile_checkout_customer(self, obj: dict[str, Any]) -> None:
        tenant_id = _metadata_tenant_id(obj)
        customer_id = extract_customer_id(obj)
        if not tenant_id or not customer_id:
            return
        if self._repo.get_tenant(tenant_id) is None:
            security_log("billing.checkout_unknown_tenant")
            return
        existing = self._repo.get_stripe_customer_mapping(tenant_id)
        if existing is None:
            now = datetime.now(UTC)
            self._repo.put_stripe_customer_mapping(
                StripeCustomerMapping(
                    tenant_id=tenant_id,
                    billing_provider=BillingProvider.STRIPE,
                    provider_customer_id=customer_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            return
        if existing.provider_customer_id != customer_id:
            security_log("billing.checkout_customer_mismatch", tenant_id=tenant_id)

    def reconcile_subscription(
        self,
        *,
        subscription_id: str,
        event_object: dict[str, Any],
    ) -> str:
        try:
            current = self._provider.retrieve_subscription(subscription_id)
        except StripeProviderUnavailableError as exc:
            raise billing_provider_unavailable() from exc
        except StripeSubscriptionNotFoundError:
            return self._project_missing_subscription(subscription_id, event_object)
        mapping = resolve_tenant_mapping(
            self._repo,
            customer_id=current.customer_id,
            event_object=event_object,
            subscription_metadata=current.metadata,
        )
        if mapping is None:
            security_log("billing.subscription_unmapped_customer")
            return "rejected_unmapped_customer"
        plan_from_price = self._config.plan_id_for_price(current.price_id)
        if plan_from_price is None:
            security_log("billing.unknown_price", tenant_id=mapping.tenant_id)
            return "rejected_unknown_price"
        claimed_plan = str(
            current.metadata.get("prem3_plan_id")
            or _object_metadata(event_object).get("prem3_plan_id")
            or ""
        ).strip()
        if claimed_plan and claimed_plan != plan_from_price:
            security_log("billing.price_metadata_mismatch", tenant_id=mapping.tenant_id)
            return "rejected_price_metadata_mismatch"
        extra_meta = set(current.metadata) - ALLOWED_METADATA_KEYS
        if extra_meta:
            security_log("billing.disallowed_metadata", tenant_id=mapping.tenant_id)
            return "rejected_metadata"
        now = datetime.now(UTC)
        incoming = SubscriptionProjection(
            tenant_id=mapping.tenant_id,
            billing_provider=BillingProvider.STRIPE,
            provider_customer_id=current.customer_id,
            provider_subscription_id=current.subscription_id,
            plan_id=plan_from_price,
            status=current.status,
            provider_updated_at=now,
            projected_at=now,
            current_period_end=current.current_period_end,
            cancel_at_period_end=current.cancel_at_period_end,
        )
        return self._persist_projection(incoming)

    def _project_missing_subscription(
        self, subscription_id: str, event_object: dict[str, Any]
    ) -> str:
        customer_id = extract_customer_id(event_object)
        if customer_id is None:
            return "ignored_missing_subscription"
        mapping = resolve_tenant_mapping(
            self._repo,
            customer_id=customer_id,
            event_object=event_object,
            subscription_metadata=_object_metadata(event_object),
        )
        if mapping is None:
            return "ignored_missing_subscription"
        existing = self._repo.get_subscription_projection(mapping.tenant_id)
        if existing is None or existing.provider_subscription_id != subscription_id:
            return "ignored_missing_subscription"
        now = datetime.now(UTC)
        incoming = existing.model_copy(
            update={
                "status": "canceled",
                "provider_updated_at": now,
                "projected_at": now,
                "cancel_at_period_end": False,
            }
        )
        return self._persist_projection(incoming)

    def _persist_projection(self, incoming: SubscriptionProjection) -> str:
        current = self._repo.get_subscription_projection(incoming.tenant_id)
        try:
            snapshot = project_subscription_to_entitlement(incoming)
        except UnsupportedSubscriptionStatusError:
            security_log(
                "billing.unsupported_subscription_status",
                tenant_id=incoming.tenant_id,
            )
            return "rejected_unsupported_status"
        try:
            existing_entitlement = self._repo.get_current_entitlement(incoming.tenant_id)
        except EntitlementUnavailableError:
            existing_entitlement = None
        if projections_materially_equal(current, incoming) and entitlements_materially_equal(
            existing_entitlement, snapshot
        ):
            return "unchanged"
        self._repo.put_subscription_projection(incoming)
        self._repo.put_entitlement_snapshot(snapshot, make_current=True)
        return "projected"


def resolve_tenant_mapping(
    repo: ControlPlaneRepository,
    *,
    customer_id: str,
    event_object: dict[str, Any],
    subscription_metadata: dict[str, str],
) -> StripeCustomerMapping | None:
    tenant_id = str(
        subscription_metadata.get("prem3_tenant_id")
        or _object_metadata(event_object).get("prem3_tenant_id")
        or ""
    ).strip()
    if not tenant_id:
        return None
    mapping = repo.get_stripe_customer_mapping(tenant_id)
    if mapping is None:
        return None
    if mapping.provider_customer_id != customer_id:
        security_log("billing.subscription_customer_mismatch", tenant_id=tenant_id)
        return None
    return mapping


def _object_metadata(obj: dict[str, Any]) -> dict[str, str]:
    raw = obj.get("metadata")
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items() if value is not None}


def _metadata_tenant_id(obj: dict[str, Any]) -> str:
    return str(_object_metadata(obj).get("prem3_tenant_id") or "").strip()
