"""Clerk Organization → PreM3 tenant provisioning. Never creates an MMM Project."""

from __future__ import annotations

from datetime import UTC, datetime

from app.control_plane.models import (
    IdentityProvider,
    IdentityProviderOrganizationMapping,
    Tenant,
    TenantStatus,
)
from app.control_plane.repository import ControlPlaneRepository
from app.core.errors import ProviderMappingConflictError
from app.service.security_log import security_log


def ensure_tenant_for_clerk_org(
    repo: ControlPlaneRepository,
    *,
    provider_organization_id: str,
    display_name: str,
) -> Tenant:
    existing_id = repo.get_tenant_id_for_provider_org(
        provider=IdentityProvider.CLERK.value,
        provider_organization_id=provider_organization_id,
    )
    if existing_id is not None:
        tenant = repo.get_tenant(existing_id)
        if tenant is not None:
            return tenant
    now = datetime.now(UTC)
    mapping = IdentityProviderOrganizationMapping(
        provider=IdentityProvider.CLERK,
        provider_organization_id=provider_organization_id,
        tenant_id="placeholder",
        created_at=now,
        updated_at=now,
    )
    try:
        tenant = repo.create_tenant(
            display_name=display_name or "Organization",
            identity_mapping=mapping,
            with_planner_entitlement=True,
        )
    except ProviderMappingConflictError:
        mapped_id = repo.get_tenant_id_for_provider_org(
            provider=IdentityProvider.CLERK.value,
            provider_organization_id=provider_organization_id,
        )
        if mapped_id is None:
            raise
        tenant = repo.get_tenant(mapped_id)
        if tenant is None:
            raise
        security_log(
            "identity.mapping_conflict_resolved",
            tenant_id=tenant.tenant_id,
            provider_organization_present=True,
        )
        return tenant
    security_log(
        "identity.tenant_provisioned",
        tenant_id=tenant.tenant_id,
        provider="clerk",
    )
    return tenant


def disable_tenant_for_deleted_org(
    repo: ControlPlaneRepository,
    *,
    provider_organization_id: str,
) -> Tenant | None:
    tenant_id = repo.get_tenant_id_for_provider_org(
        provider=IdentityProvider.CLERK.value,
        provider_organization_id=provider_organization_id,
    )
    if tenant_id is None:
        return None
    tenant = repo.set_tenant_status(tenant_id=tenant_id, status=TenantStatus.DISABLED.value)
    security_log(
        "identity.organization_deleted_tenant_disabled",
        tenant_id=tenant.tenant_id,
    )
    return tenant
