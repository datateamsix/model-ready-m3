"""Request-scoped authority dependencies for prem3-api."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.control_plane.models import Dataset, MembershipStatus, Workspace
from app.control_plane.repository import ControlPlaneRepository
from app.core.tenancy import (
    AuthState,
    TenantContext,
    WorkspaceContext,
    bind_tenant,
    bind_workspace,
    require_tenant,
)
from app.service.auth import IdentityVerifier
from app.service.billing import BillingGateway
from app.service.errors import entitlement_denied, resource_not_found, tenant_not_found

bearer_scheme = HTTPBearer(
    auto_error=False,
    bearerFormat="JWT",
    description=(
        "Future Clerk session token forwarded by the Next.js BFF. "
        "Authentication adapter is pending; this scheme documents the contract only."
    ),
)

BearerAuth = Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)]


def get_control_plane(request: Request) -> ControlPlaneRepository:
    return request.app.state.control_plane


def get_identity_verifier(request: Request) -> IdentityVerifier:
    return request.app.state.identity_verifier


def get_billing_gateway(request: Request) -> BillingGateway:
    return request.app.state.billing_gateway


def _authorization_header(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials is None:
        return None
    return f"{credentials.scheme} {credentials.credentials}"


async def authenticated_tenant(
    request: Request,
    credentials: BearerAuth,
    repo: Annotated[ControlPlaneRepository, Depends(get_control_plane)],
    verifier: Annotated[IdentityVerifier, Depends(get_identity_verifier)],
) -> AsyncIterator[TenantContext]:
    identity = verifier.verify(_authorization_header(credentials))
    tenant_id = repo.get_tenant_id_for_provider_org(
        provider=identity.provider,
        provider_organization_id=identity.provider_organization_id,
    )
    if tenant_id is None:
        raise tenant_not_found()
    membership = repo.get_membership_projection(
        tenant_id=tenant_id,
        provider=identity.provider,
        provider_user_id=identity.provider_user_id,
    )
    if membership is None or membership.status != MembershipStatus.ACTIVE:
        raise entitlement_denied()
    tenant = repo.get_tenant(tenant_id)
    if tenant is None:
        raise tenant_not_found()
    entitlement = tenant.current_entitlement_snapshot_id
    ctx = TenantContext(
        tenant_id=tenant_id,
        user_id=identity.provider_user_id,
        auth_state=AuthState.AUTHENTICATED,
        entitlement_snapshot_id=entitlement,
    )
    request.state.verified_identity = identity
    with bind_tenant(ctx) as bound:
        yield bound


async def authorized_workspace(
    workspace_id: str,
    repo: Annotated[ControlPlaneRepository, Depends(get_control_plane)],
    tenant: Annotated[TenantContext, Depends(authenticated_tenant)],
) -> AsyncIterator[Workspace]:
    workspace = repo.get_workspace_for_tenant(
        tenant_id=tenant.tenant_id, workspace_id=workspace_id
    )
    if workspace is None:
        raise resource_not_found()
    with bind_workspace(WorkspaceContext(workspace_id=workspace.workspace_id)) as _:
        yield workspace


def authorized_dataset(
    dataset_id: str,
    workspace: Annotated[Workspace, Depends(authorized_workspace)],
    repo: Annotated[ControlPlaneRepository, Depends(get_control_plane)],
) -> Dataset:
    tenant = require_tenant()
    dataset = repo.get_dataset_for_workspace(
        tenant_id=tenant.tenant_id,
        workspace_id=workspace.workspace_id,
        dataset_id=dataset_id,
    )
    if dataset is None:
        raise resource_not_found()
    return dataset
