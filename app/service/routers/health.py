from __future__ import annotations

from fastapi import APIRouter, Request

from app.service.auth import UnconfiguredIdentityVerifier
from app.service.billing import UnavailableBillingGateway
from app.service.models import HealthResponse, ReadyProviderStatus, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", operation_id="getHealth", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", operation_id="getReady", response_model=ReadyResponse)
def get_ready(request: Request) -> ReadyResponse:
    auth = request.app.state.identity_verifier
    billing = request.app.state.billing_gateway
    auth_status = (
        "not_configured" if isinstance(auth, UnconfiguredIdentityVerifier) else "configured"
    )
    billing_status = (
        "not_configured"
        if isinstance(billing, UnavailableBillingGateway)
        else "configured"
    )
    return ReadyResponse(
        status="ready",
        dependencies=ReadyProviderStatus(
            control_plane="configured",
            auth_provider=auth_status,
            billing_provider=billing_status,
        ),
    )
