from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.tenancy import TenantContext, require_tenant
from app.service.billing import BillingGateway, validate_return_path
from app.service.dependencies import authenticated_tenant, get_billing_gateway
from app.service.errors import billing_provider_not_configured
from app.service.models import (
    BillingSessionResponse,
    CheckoutSessionRequest,
    PortalSessionRequest,
)

router = APIRouter(prefix="/v1", tags=["billing"])


@router.post(
    "/billing/checkout-session",
    operation_id="createCheckoutSession",
    response_model=BillingSessionResponse,
)
async def create_checkout_session(
    body: CheckoutSessionRequest,
    tenant: Annotated[TenantContext, Depends(authenticated_tenant)],
    gateway: Annotated[BillingGateway, Depends(get_billing_gateway)],
) -> BillingSessionResponse:
    require_tenant()
    return_path = validate_return_path(body.return_path)
    session = gateway.create_checkout_session(
        tenant_id=tenant.tenant_id,
        plan_id=body.plan_id,
        return_path=return_path,
    )
    return BillingSessionResponse(url=session.url, expires_at=session.expires_at)


@router.post(
    "/billing/portal-session",
    operation_id="createPortalSession",
    response_model=BillingSessionResponse,
)
async def create_portal_session(
    body: PortalSessionRequest,
    tenant: Annotated[TenantContext, Depends(authenticated_tenant)],
    gateway: Annotated[BillingGateway, Depends(get_billing_gateway)],
) -> BillingSessionResponse:
    require_tenant()
    return_path = validate_return_path(body.return_path)
    session = gateway.create_portal_session(
        tenant_id=tenant.tenant_id, return_path=return_path
    )
    return BillingSessionResponse(url=session.url, expires_at=session.expires_at)


@router.post(
    "/webhooks/billing",
    operation_id="billingWebhook",
    tags=["webhooks"],
    include_in_schema=True,
)
def billing_webhook(request: Request) -> dict[str, str]:
    """Internal provider callback. Signature verification is not implemented."""
    del request
    raise billing_provider_not_configured()
