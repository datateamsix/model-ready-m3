"""Verified Clerk identity webhook projection. Signature must already be checked."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.control_plane.models import (
    IdentityProvider,
    MembershipProjection,
    MembershipStatus,
    TenantStatus,
    WebhookClaimStatus,
    WebhookProvider,
)
from app.control_plane.repository import ControlPlaneRepository
from app.service.clerk_runtime import OrganizationDirectory
from app.service.provisioning import disable_tenant_for_deleted_org, ensure_tenant_for_clerk_org
from app.service.security_log import security_log

_HANDLED = frozenset(
    {
        "organization.created",
        "organization.deleted",
        "organizationMembership.created",
        "organizationMembership.updated",
        "organizationMembership.deleted",
    }
)


def process_verified_identity_event(
    event: dict[str, Any],
    *,
    repo: ControlPlaneRepository,
    organization_directory: OrganizationDirectory | None,
    provider_event_id: str,
) -> str:
    event_type = str(event.get("type") or "unknown")
    claim = repo.claim_webhook_event(
        provider=WebhookProvider.CLERK,
        provider_event_id=provider_event_id,
        event_type=event_type,
    )
    if claim.status == WebhookClaimStatus.ALREADY_PROCESSED:
        security_log("identity.webhook_duplicate", event_type=event_type)
        return "duplicate"
    if claim.status == WebhookClaimStatus.ALREADY_CLAIMED:
        security_log("identity.webhook_already_claimed", event_type=event_type)
        return "duplicate"
    try:
        result = _dispatch(event_type, event.get("data") or {}, repo, organization_directory)
    except Exception:
        repo.mark_webhook_event_failed(
            provider=WebhookProvider.CLERK,
            provider_event_id=provider_event_id,
            result="failed",
        )
        raise
    repo.mark_webhook_event_processed(
        provider=WebhookProvider.CLERK,
        provider_event_id=provider_event_id,
        result=result,
    )
    security_log("identity.webhook_accepted", event_type=event_type, result=result)
    return result


def _dispatch(
    event_type: str,
    data: object,
    repo: ControlPlaneRepository,
    organization_directory: OrganizationDirectory | None,
) -> str:
    payload = data if isinstance(data, dict) else {}
    if event_type == "organization.created":
        return _organization_created(payload, repo)
    if event_type == "organization.deleted":
        return _organization_deleted(payload, repo)
    if event_type in {"organizationMembership.created", "organizationMembership.updated"}:
        return _membership_upsert(payload, repo, organization_directory)
    if event_type == "organizationMembership.deleted":
        return _membership_deleted(payload, repo)
    if event_type not in _HANDLED:
        return "ignored"
    return "ignored"


def _organization_created(data: dict[str, Any], repo: ControlPlaneRepository) -> str:
    org_id = str(data.get("id") or "").strip()
    if not org_id:
        return "ignored"
    name = str(data.get("name") or "Organization")
    tenant = ensure_tenant_for_clerk_org(
        repo, provider_organization_id=org_id, display_name=name
    )
    entitlement = repo.get_current_entitlement(tenant.tenant_id)
    workspaces = repo.list_workspaces_for_tenant(tenant.tenant_id)
    if entitlement.max_active_projects != 0 or workspaces:
        security_log(
            "identity.mapping_conflict",
            tenant_id=tenant.tenant_id,
            unexpected_capacity=entitlement.max_active_projects,
            workspace_count=len(workspaces),
        )
    return "provisioned"


def _organization_deleted(data: dict[str, Any], repo: ControlPlaneRepository) -> str:
    org_id = str(data.get("id") or "").strip()
    if not org_id:
        return "ignored"
    tenant = disable_tenant_for_deleted_org(repo, provider_organization_id=org_id)
    if tenant is None:
        return "ignored"
    # Confirm we did not delete customer resources.
    remaining = repo.list_workspaces_for_tenant(tenant.tenant_id)
    del remaining
    return "deletion_pending"


def _membership_upsert(
    data: dict[str, Any],
    repo: ControlPlaneRepository,
    organization_directory: OrganizationDirectory | None,
) -> str:
    org_id, user_id, role = _membership_ids(data)
    if not org_id or not user_id:
        return "ignored"
    tenant_id = repo.get_tenant_id_for_provider_org(
        provider=IdentityProvider.CLERK.value, provider_organization_id=org_id
    )
    if tenant_id is None:
        if organization_directory is None:
            return "ignored_unmapped_organization"
        org = organization_directory.get_organization(org_id)
        if org is None:
            return "ignored_unmapped_organization"
        tenant = ensure_tenant_for_clerk_org(
            repo, provider_organization_id=org.organization_id, display_name=org.name
        )
        tenant_id = tenant.tenant_id
    tenant = repo.get_tenant(tenant_id)
    if tenant is None or tenant.status != TenantStatus.ACTIVE:
        return "ignored_inactive_tenant"
    repo.upsert_membership_projection(
        MembershipProjection(
            tenant_id=tenant_id,
            provider=IdentityProvider.CLERK,
            provider_user_id=user_id,
            provider_organization_id=org_id,
            role=role,
            status=MembershipStatus.ACTIVE,
            updated_at=datetime.now(UTC),
        )
    )
    return "membership_active"


def _membership_deleted(data: dict[str, Any], repo: ControlPlaneRepository) -> str:
    org_id, user_id, role = _membership_ids(data)
    if not org_id or not user_id:
        return "ignored"
    tenant_id = repo.get_tenant_id_for_provider_org(
        provider=IdentityProvider.CLERK.value, provider_organization_id=org_id
    )
    if tenant_id is None:
        return "ignored_unmapped_organization"
    repo.upsert_membership_projection(
        MembershipProjection(
            tenant_id=tenant_id,
            provider=IdentityProvider.CLERK,
            provider_user_id=user_id,
            provider_organization_id=org_id,
            role=role,
            status=MembershipStatus.REMOVED,
            updated_at=datetime.now(UTC),
        )
    )
    security_log("identity.membership_revoked", tenant_id=tenant_id, provider_user_id=user_id)
    return "membership_removed"


def _membership_ids(data: dict[str, Any]) -> tuple[str, str, str | None]:
    organization = data.get("organization")
    org_id = ""
    if isinstance(organization, dict):
        org_id = str(organization.get("id") or "").strip()
    if not org_id:
        org_id = str(data.get("organization_id") or "").strip()
    public_user = data.get("public_user_data")
    user_id = ""
    if isinstance(public_user, dict):
        user_id = str(public_user.get("user_id") or "").strip()
    if not user_id:
        user_id = str(data.get("user_id") or "").strip()
    role = str(data.get("role") or "").strip() or None
    return org_id, user_id, role
