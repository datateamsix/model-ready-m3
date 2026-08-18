"""Billing gateway seam. Stripe SDK is injected through the application factory."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.service.errors import ProblemFieldError, billing_provider_not_configured, validation_error


class BillingSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    expires_at: datetime | None = None


class BillingGateway(Protocol):
    def create_checkout_session(
        self,
        *,
        tenant_id: str,
        plan_id: str,
        return_path: str | None,
        idempotency_key: str | None = None,
    ) -> BillingSession: ...

    def create_portal_session(
        self, *, tenant_id: str, return_path: str | None
    ) -> BillingSession: ...


class UnavailableBillingGateway:
    """Production default when Stripe is not configured. No fake URLs."""

    def create_checkout_session(
        self,
        *,
        tenant_id: str,
        plan_id: str,
        return_path: str | None,
        idempotency_key: str | None = None,
    ) -> BillingSession:
        del tenant_id, plan_id, return_path, idempotency_key
        raise billing_provider_not_configured()

    def create_portal_session(
        self, *, tenant_id: str, return_path: str | None
    ) -> BillingSession:
        del tenant_id, return_path
        raise billing_provider_not_configured()


class FakeBillingGateway:
    """Test-only. Injected through the application factory."""

    def create_checkout_session(
        self,
        *,
        tenant_id: str,
        plan_id: str,
        return_path: str | None,
        idempotency_key: str | None = None,
    ) -> BillingSession:
        del tenant_id, idempotency_key
        suffix = f"?plan={plan_id}"
        if return_path:
            suffix += f"&return={return_path}"
        return BillingSession(url=f"https://billing.test/checkout{suffix}", expires_at=None)

    def create_portal_session(
        self, *, tenant_id: str, return_path: str | None
    ) -> BillingSession:
        del tenant_id, return_path
        return BillingSession(url="https://billing.test/portal", expires_at=None)


def validate_return_path(return_path: str | None) -> str | None:
    if return_path is None or return_path == "":
        return None
    if not return_path.startswith("/") or return_path.startswith("//"):
        raise validation_error(
            [ProblemFieldError(field="return_path", message="Must be a relative path.")]
        )
    if "://" in return_path or "\\" in return_path or ".." in return_path:
        raise validation_error(
            [ProblemFieldError(field="return_path", message="Must be a relative path.")]
        )
    return return_path
