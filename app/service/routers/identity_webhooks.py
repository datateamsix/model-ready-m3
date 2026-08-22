from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.control_plane.repository import ControlPlaneRepository
from app.service.clerk_runtime import OrganizationDirectory, WebhookVerifier
from app.service.clerk_webhooks import WebhookSignatureError
from app.service.dependencies import (
    get_control_plane,
    get_organization_directory,
    get_webhook_verifier,
)
from app.service.errors import auth_provider_not_configured, auth_required
from app.service.identity_events import process_verified_identity_event
from app.service.models import WebhookAckResponse
from app.service.security_log import security_log

router = APIRouter(prefix="/v1", tags=["webhooks"])


@router.post(
    "/webhooks/identity",
    operation_id="identityWebhook",
    response_model=WebhookAckResponse,
)
async def identity_webhook(
    request: Request,
    repo: Annotated[ControlPlaneRepository, Depends(get_control_plane)],
    verifier: Annotated[WebhookVerifier | None, Depends(get_webhook_verifier)],
    organization_directory: Annotated[
        OrganizationDirectory | None, Depends(get_organization_directory)
    ],
) -> WebhookAckResponse:
    """Internal Clerk callback. Signature is verified before the body is trusted."""
    if verifier is None:
        raise auth_provider_not_configured()
    raw = await request.body()
    try:
        event = verifier.verify_webhook(body=raw, headers=request.headers)
    except WebhookSignatureError:
        security_log("identity.webhook_rejected", reason="invalid_signature")
        raise auth_required() from None
    event_id = _event_id(event, request.headers)
    result = process_verified_identity_event(
        event,
        repo=repo,
        organization_directory=organization_directory,
        provider_event_id=event_id,
    )
    return WebhookAckResponse(status="accepted", result=result)


def _event_id(event: dict[str, Any], headers: Any) -> str:
    event_id = str(event.get("id") or "").strip()
    if event_id:
        return event_id
    for key, value in headers.items():
        if str(key).lower() == "svix-id" and str(value).strip():
            return str(value).strip()
    return "unknown"
