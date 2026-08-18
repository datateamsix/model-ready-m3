"""Google OAuth start (Clerk) and callback (no Clerk)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.core.tenancy import TenantContext
from app.service.billing import validate_return_path
from app.service.dependencies import authenticated_tenant
from app.service.google_oauth import GoogleConnectionService
from app.service.models import (
    GoogleConnectionListResponse,
    GoogleConnectionResponse,
    GoogleOAuthStartRequest,
    GoogleOAuthStartResponse,
)

router = APIRouter(tags=["google"])


def get_google_connections(request: Request) -> GoogleConnectionService:
    service = getattr(request.app.state, "google_connections", None)
    if service is None:
        raise RuntimeError("Google connection service is not configured.")
    return service


def _connection_response(item) -> GoogleConnectionResponse:
    return GoogleConnectionResponse(
        connection_id=item.connection_id,
        display_email=item.display_email,
        status=item.status,
        capabilities=list(item.capabilities),
        created_at=item.created_at,
        updated_at=item.updated_at,
        last_verified_at=item.last_verified_at,
    )


@router.post(
    "/v1/integrations/google/oauth/start",
    operation_id="startGoogleOAuth",
    response_model=GoogleOAuthStartResponse,
)
async def start_google_oauth(
    body: GoogleOAuthStartRequest,
    tenant: Annotated[TenantContext, Depends(authenticated_tenant)],
    service: Annotated[GoogleConnectionService, Depends(get_google_connections)],
) -> GoogleOAuthStartResponse:
    return_path = validate_return_path(body.return_path) or "/app/settings"
    authorization_url, expires_at = service.start_oauth(
        capabilities=body.capabilities,
        workspace_id=body.workspace_id,
        dataset_id=body.dataset_id,
        return_path=return_path,
        initiating_user_id=tenant.user_id or "unknown",
    )
    return GoogleOAuthStartResponse(authorization_url=authorization_url, expires_at=expires_at)


@router.get(
    "/v1/integrations/google/oauth/callback",
    operation_id="googleOAuthCallback",
    include_in_schema=True,
)
async def google_oauth_callback(
    request: Request,
    service: Annotated[GoogleConnectionService, Depends(get_google_connections)],
) -> RedirectResponse:
    params = request.query_params
    location = service.complete_oauth(
        state=params.get("state"),
        code=params.get("code"),
        error=params.get("error"),
    )
    return RedirectResponse(url=location, status_code=302)


@router.get(
    "/v1/integrations/google/connections",
    operation_id="listGoogleConnections",
    response_model=GoogleConnectionListResponse,
)
async def list_google_connections(
    _tenant: Annotated[TenantContext, Depends(authenticated_tenant)],
    service: Annotated[GoogleConnectionService, Depends(get_google_connections)],
) -> GoogleConnectionListResponse:
    rows = service.list_connections()
    return GoogleConnectionListResponse(items=[_connection_response(item) for item in rows])


@router.post(
    "/v1/integrations/google/connections/{connection_id}/disconnect",
    operation_id="disconnectGoogleConnection",
    response_model=GoogleConnectionResponse,
)
async def disconnect_google_connection(
    connection_id: str,
    _tenant: Annotated[TenantContext, Depends(authenticated_tenant)],
    service: Annotated[GoogleConnectionService, Depends(get_google_connections)],
) -> GoogleConnectionResponse:
    return _connection_response(service.disconnect(connection_id=connection_id))
