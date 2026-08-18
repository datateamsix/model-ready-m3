"""Stripe provider protocol, fake, and official SDK adapter.

No Stripe network call happens at import time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from stripe import StripeClient
from stripe._error import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    InvalidRequestError,
    RateLimitError,
    SignatureVerificationError,
)
from stripe._http_client import new_default_http_client
from stripe._webhook import WebhookSignature

from app.service.billing_config import ALLOWED_METADATA_KEYS, BillingConfig

HANDLED_BILLING_EVENTS: frozenset[str] = frozenset(
    {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    }
)


class StripeProviderError(Exception):
    """Internal Stripe adapter failure. Do not expose to HTTP clients."""


class StripeProviderUnavailableError(StripeProviderError):
    pass


class StripeProviderConfigurationError(StripeProviderError):
    pass


class StripeSubscriptionNotFoundError(StripeProviderError):
    pass


class StripeWebhookSignatureError(StripeProviderError):
    pass


@dataclass(frozen=True, slots=True)
class StripeCustomerRecord:
    customer_id: str
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class StripeCheckoutRecord:
    session_id: str
    url: str
    expires_at: datetime | None
    mode: str
    customer_id: str
    price_id: str
    metadata: dict[str, str]
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class StripePortalRecord:
    url: str
    customer_id: str


@dataclass(frozen=True, slots=True)
class StripeSubscriptionRecord:
    subscription_id: str
    customer_id: str
    price_id: str
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class StripePriceRecord:
    price_id: str
    active: bool
    recurring: bool
    interval: str | None
    currency: str | None
    unit_amount: int | None


@dataclass(frozen=True, slots=True)
class VerifiedStripeEvent:
    event_id: str
    event_type: str
    data_object: dict[str, Any]


class StripeProvider(Protocol):
    def create_customer(
        self, *, tenant_id: str, idempotency_key: str
    ) -> StripeCustomerRecord: ...

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
        idempotency_key: str,
    ) -> StripeCheckoutRecord: ...

    def create_portal_session(
        self,
        *,
        customer_id: str,
        return_url: str,
        configuration_id: str | None,
    ) -> StripePortalRecord: ...

    def retrieve_subscription(self, subscription_id: str) -> StripeSubscriptionRecord: ...

    def retrieve_price(self, price_id: str) -> StripePriceRecord: ...

    def verify_webhook(self, *, payload: bytes, signature: str, secret: str) -> VerifiedStripeEvent:
        ...


def _require_allowed_metadata(metadata: dict[str, str]) -> dict[str, str]:
    extra = set(metadata) - ALLOWED_METADATA_KEYS
    if extra:
        raise StripeProviderConfigurationError("Stripe metadata contains disallowed keys.")
    return dict(metadata)


@dataclass
class FakeStripeProvider:
    """Deterministic in-process Stripe stand-in. No network."""

    prices: dict[str, StripePriceRecord] = field(default_factory=dict)
    customers: dict[str, StripeCustomerRecord] = field(default_factory=dict)
    customer_by_idempotency: dict[str, str] = field(default_factory=dict)
    checkout_by_idempotency: dict[str, StripeCheckoutRecord] = field(default_factory=dict)
    subscriptions: dict[str, StripeSubscriptionRecord] = field(default_factory=dict)
    portal_sessions: list[StripePortalRecord] = field(default_factory=list)
    checkout_sessions: list[StripeCheckoutRecord] = field(default_factory=list)
    fail_checkout: bool = False
    fail_portal: bool = False
    fail_retrieve: bool = False
    webhook_secret: str = "whsec_test"
    _lock: Lock = field(default_factory=Lock)
    create_customer_calls: int = 0
    last_checkout_idempotency_key: str | None = None

    def seed_price(
        self,
        price_id: str,
        *,
        active: bool = True,
        interval: str = "month",
        currency: str = "usd",
        unit_amount: int = 9900,
    ) -> None:
        self.prices[price_id] = StripePriceRecord(
            price_id=price_id,
            active=active,
            recurring=True,
            interval=interval,
            currency=currency,
            unit_amount=unit_amount,
        )

    def set_subscription(
        self,
        subscription_id: str,
        *,
        customer_id: str,
        price_id: str,
        status: str,
        current_period_end: datetime | None = None,
        cancel_at_period_end: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> StripeSubscriptionRecord:
        record = StripeSubscriptionRecord(
            subscription_id=subscription_id,
            customer_id=customer_id,
            price_id=price_id,
            status=status,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
            metadata=_require_allowed_metadata(metadata or {}),
        )
        self.subscriptions[subscription_id] = record
        return record

    def create_customer(self, *, tenant_id: str, idempotency_key: str) -> StripeCustomerRecord:
        with self._lock:
            self.create_customer_calls += 1
            existing_id = self.customer_by_idempotency.get(idempotency_key)
            if existing_id is not None:
                return self.customers[existing_id]
            customer_id = f"cus_{uuid4().hex[:16]}"
            record = StripeCustomerRecord(
                customer_id=customer_id,
                metadata={"prem3_tenant_id": tenant_id},
            )
            self.customers[customer_id] = record
            self.customer_by_idempotency[idempotency_key] = customer_id
            return record

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
        idempotency_key: str,
    ) -> StripeCheckoutRecord:
        del success_url, cancel_url
        if self.fail_checkout:
            raise StripeProviderUnavailableError("checkout unavailable")
        safe_meta = _require_allowed_metadata(metadata)
        with self._lock:
            cached = self.checkout_by_idempotency.get(idempotency_key)
            if cached is not None:
                self.last_checkout_idempotency_key = idempotency_key
                return cached
            session_id = f"cs_{uuid4().hex[:16]}"
            record = StripeCheckoutRecord(
                session_id=session_id,
                url=f"https://checkout.stripe.test/c/pay/{session_id}",
                expires_at=None,
                mode="subscription",
                customer_id=customer_id,
                price_id=price_id,
                metadata=safe_meta,
                idempotency_key=idempotency_key,
            )
            self.checkout_by_idempotency[idempotency_key] = record
            self.checkout_sessions.append(record)
            self.last_checkout_idempotency_key = idempotency_key
            return record

    def create_portal_session(
        self,
        *,
        customer_id: str,
        return_url: str,
        configuration_id: str | None,
    ) -> StripePortalRecord:
        del return_url, configuration_id
        if self.fail_portal:
            raise StripeProviderUnavailableError("portal unavailable")
        record = StripePortalRecord(
            url=f"https://billing.stripe.test/p/{customer_id}",
            customer_id=customer_id,
        )
        self.portal_sessions.append(record)
        return record

    def retrieve_subscription(self, subscription_id: str) -> StripeSubscriptionRecord:
        if self.fail_retrieve:
            raise StripeProviderUnavailableError("retrieve unavailable")
        record = self.subscriptions.get(subscription_id)
        if record is None:
            raise StripeSubscriptionNotFoundError(subscription_id)
        return record

    def retrieve_price(self, price_id: str) -> StripePriceRecord:
        record = self.prices.get(price_id)
        if record is None:
            raise StripeProviderConfigurationError(f"unknown price {price_id}")
        return record

    def verify_webhook(
        self, *, payload: bytes, signature: str, secret: str
    ) -> VerifiedStripeEvent:
        try:
            body_text = (
                payload.decode("utf-8") if isinstance(payload, bytes | bytearray) else payload
            )
            WebhookSignature.verify_header(body_text, signature, secret)
        except SignatureVerificationError as exc:
            raise StripeWebhookSignatureError("invalid signature") from exc
        body = json.loads(payload.decode("utf-8"))
        if not isinstance(body, dict):
            raise StripeWebhookSignatureError("invalid event")
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        obj = data.get("object") if isinstance(data, dict) else {}
        if not isinstance(obj, dict):
            obj = {}
        return VerifiedStripeEvent(
            event_id=str(body.get("id") or ""),
            event_type=str(body.get("type") or ""),
            data_object=obj,
        )


class RealStripeProvider:
    """Official stripe.StripeClient adapter. Constructed only when a secret is configured."""

    def __init__(self, config: BillingConfig) -> None:
        if not config.secret_key:
            raise StripeProviderConfigurationError("missing stripe secret")
        http_client = new_default_http_client(timeout=config.stripe_timeout_seconds)
        self._client = StripeClient(
            config.secret_key,
            http_client=http_client,
            max_network_retries=config.stripe_max_network_retries,
        )

    def create_customer(self, *, tenant_id: str, idempotency_key: str) -> StripeCustomerRecord:
        try:
            customer = self._client.v1.customers.create(
                params={"metadata": {"prem3_tenant_id": tenant_id}},
                options={"idempotency_key": idempotency_key},
            )
        except (APIConnectionError, RateLimitError) as exc:
            raise StripeProviderUnavailableError("customer create unavailable") from exc
        except (AuthenticationError, InvalidRequestError) as exc:
            raise StripeProviderConfigurationError("customer create rejected") from exc
        except APIError as exc:
            raise StripeProviderUnavailableError("customer create failed") from exc
        return StripeCustomerRecord(
            customer_id=str(customer["id"]),
            metadata=_string_metadata(customer.get("metadata")),
        )

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
        idempotency_key: str,
    ) -> StripeCheckoutRecord:
        safe_meta = _require_allowed_metadata(metadata)
        try:
            session = self._client.v1.checkout.sessions.create(
                params={
                    "mode": "subscription",
                    "customer": customer_id,
                    "line_items": [{"price": price_id, "quantity": 1}],
                    "success_url": success_url,
                    "cancel_url": cancel_url,
                    "metadata": safe_meta,
                    "subscription_data": {"metadata": safe_meta},
                },
                options={"idempotency_key": idempotency_key},
            )
        except (APIConnectionError, RateLimitError) as exc:
            raise StripeProviderUnavailableError("checkout unavailable") from exc
        except (AuthenticationError, InvalidRequestError) as exc:
            raise StripeProviderConfigurationError("checkout rejected") from exc
        except APIError as exc:
            raise StripeProviderUnavailableError("checkout failed") from exc
        expires_at = _unix_to_datetime(session.get("expires_at"))
        return StripeCheckoutRecord(
            session_id=str(session["id"]),
            url=str(session["url"]),
            expires_at=expires_at,
            mode=str(session.get("mode") or "subscription"),
            customer_id=customer_id,
            price_id=price_id,
            metadata=safe_meta,
            idempotency_key=idempotency_key,
        )

    def create_portal_session(
        self,
        *,
        customer_id: str,
        return_url: str,
        configuration_id: str | None,
    ) -> StripePortalRecord:
        params: dict[str, str] = {"customer": customer_id, "return_url": return_url}
        if configuration_id:
            params["configuration"] = configuration_id
        try:
            session = self._client.v1.billing_portal.sessions.create(params=params)
        except (APIConnectionError, RateLimitError) as exc:
            raise StripeProviderUnavailableError("portal unavailable") from exc
        except InvalidRequestError as exc:
            raise StripeProviderConfigurationError("portal rejected") from exc
        except APIError as exc:
            raise StripeProviderUnavailableError("portal failed") from exc
        return StripePortalRecord(url=str(session["url"]), customer_id=customer_id)

    def retrieve_subscription(self, subscription_id: str) -> StripeSubscriptionRecord:
        try:
            subscription = self._client.v1.subscriptions.retrieve(
                subscription_id,
                params={"expand": ["items.data.price"]},
            )
        except InvalidRequestError as exc:
            raise StripeSubscriptionNotFoundError(subscription_id) from exc
        except (APIConnectionError, RateLimitError, APIError) as exc:
            raise StripeProviderUnavailableError("subscription retrieve unavailable") from exc
        payload = _stripe_to_dict(subscription)
        return subscription_record_from_object(payload)

    def retrieve_price(self, price_id: str) -> StripePriceRecord:
        try:
            price = self._client.v1.prices.retrieve(price_id)
        except InvalidRequestError as exc:
            raise StripeProviderConfigurationError("price missing") from exc
        except (APIConnectionError, RateLimitError, APIError) as exc:
            raise StripeProviderUnavailableError("price retrieve unavailable") from exc
        payload = _stripe_to_dict(price)
        recurring = payload.get("recurring") if isinstance(payload.get("recurring"), dict) else {}
        return StripePriceRecord(
            price_id=str(payload.get("id") or price_id),
            active=bool(payload.get("active")),
            recurring=payload.get("type") == "recurring" or bool(recurring),
            interval=str(recurring.get("interval")) if recurring else None,
            currency=str(payload.get("currency")) if payload.get("currency") else None,
            unit_amount=(
                int(payload["unit_amount"]) if payload.get("unit_amount") is not None else None
            ),
        )

    def verify_webhook(
        self, *, payload: bytes, signature: str, secret: str
    ) -> VerifiedStripeEvent:
        try:
            event = self._client.construct_event(payload, signature, secret)
        except SignatureVerificationError as exc:
            raise StripeWebhookSignatureError("invalid signature") from exc
        except ValueError as exc:
            raise StripeWebhookSignatureError("invalid payload") from exc
        payload_dict = _stripe_to_dict(event)
        data = payload_dict.get("data") if isinstance(payload_dict.get("data"), dict) else {}
        obj = data.get("object") if isinstance(data, dict) else {}
        if not isinstance(obj, dict):
            obj = {}
        return VerifiedStripeEvent(
            event_id=str(payload_dict.get("id") or ""),
            event_type=str(payload_dict.get("type") or ""),
            data_object=obj,
        )


def subscription_record_from_object(payload: dict[str, Any]) -> StripeSubscriptionRecord:
    items = payload.get("items") if isinstance(payload.get("items"), dict) else {}
    data = items.get("data") if isinstance(items, dict) else []
    first = data[0] if isinstance(data, list) and data else {}
    price = first.get("price") if isinstance(first, dict) else None
    price_id = _id_of(price) or _id_of(first.get("plan") if isinstance(first, dict) else None)
    period_end = None
    if isinstance(first, dict) and first.get("current_period_end") is not None:
        period_end = _unix_to_datetime(first.get("current_period_end"))
    elif payload.get("current_period_end") is not None:
        period_end = _unix_to_datetime(payload.get("current_period_end"))
    if not price_id:
        raise StripeProviderConfigurationError("subscription has no price")
    return StripeSubscriptionRecord(
        subscription_id=str(payload.get("id") or ""),
        customer_id=str(_id_of(payload.get("customer")) or ""),
        price_id=price_id,
        status=str(payload.get("status") or ""),
        current_period_end=period_end,
        cancel_at_period_end=bool(payload.get("cancel_at_period_end")),
        metadata=_string_metadata(payload.get("metadata")),
    )


def extract_subscription_id(event_type: str, obj: dict[str, Any]) -> str | None:
    if event_type.startswith("customer.subscription."):
        return _id_of(obj.get("id"))
    if event_type == "checkout.session.completed":
        return _id_of(obj.get("subscription"))
    if event_type in {"invoice.paid", "invoice.payment_failed"}:
        parent = obj.get("parent") if isinstance(obj.get("parent"), dict) else {}
        details = (
            parent.get("subscription_details") if isinstance(parent, dict) else None
        )
        nested = details.get("subscription") if isinstance(details, dict) else None
        return _id_of(obj.get("subscription")) or _id_of(nested)
    return None


def extract_customer_id(obj: dict[str, Any]) -> str | None:
    return _id_of(obj.get("customer"))


def sign_stripe_payload(payload: bytes | str, secret: str) -> str:
    body = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    return WebhookSignature.generate_signature_header(payload=body, secret=secret)


def _id_of(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        ident = value.get("id")
        if isinstance(ident, str) and ident.strip():
            return ident.strip()
    return None


def _string_metadata(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if item is not None}


def _unix_to_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _stripe_to_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    for name in ("to_dict_recursive", "to_dict"):
        method = getattr(value, name, None)
        if callable(method):
            converted = method()
            if isinstance(converted, dict):
                return converted
    return dict(value) if value is not None else {}


def validate_configured_price(record: StripePriceRecord) -> None:
    if not record.active:
        raise StripeProviderConfigurationError("price inactive")
    if not record.recurring or record.interval != "month":
        raise StripeProviderConfigurationError("price is not monthly recurring")
