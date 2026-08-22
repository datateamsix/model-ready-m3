"""Explicit developer/CLI bootstrap for legacy golden-path scripts.

Repositories, ADK tools, coordinators, and request handlers must not import this
module. Request-scoped code uses bind_tenant() / bind_workspace() from a verified
credential at the future service boundary.

MODELREADY_ORGANIZATION_ID and MODELREADY_WORKSPACE_ID remain developer inputs.
They never bind TenantContext unless a caller invokes these helpers.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.errors import TenantContextMissingError, WorkspaceContextMissingError
from app.core.tenancy import (
    AuthState,
    TenantContext,
    WorkspaceContext,
    bind_tenant,
    bind_workspace,
)

DEVELOPER_TENANT_ID_ENV = "MODELREADY_ORGANIZATION_ID"
DEVELOPER_WORKSPACE_ID_ENV = "MODELREADY_WORKSPACE_ID"
DEVELOPER_BOOTSTRAP_TENANT_ID = "music-center"
DEVELOPER_BOOTSTRAP_WORKSPACE_ID = "mmm-demo"


def load_developer_tenant_context() -> TenantContext:
    """Read the CLI org env var. Never called by require_tenant()."""
    if DEVELOPER_TENANT_ID_ENV in os.environ:
        raw = os.environ[DEVELOPER_TENANT_ID_ENV].strip()
        if not raw:
            raise TenantContextMissingError(
                "Developer bootstrap MODELREADY_ORGANIZATION_ID is empty."
            )
    else:
        raw = DEVELOPER_BOOTSTRAP_TENANT_ID
    return TenantContext(
        tenant_id=raw,
        user_id=None,
        auth_state=AuthState.SERVICE,
        entitlement_snapshot_id=None,
    )


def load_developer_workspace_context() -> WorkspaceContext:
    """Read the CLI workspace env var. Never called by require_workspace()."""
    if DEVELOPER_WORKSPACE_ID_ENV in os.environ:
        raw = os.environ[DEVELOPER_WORKSPACE_ID_ENV].strip()
        if not raw:
            raise WorkspaceContextMissingError(
                "Developer bootstrap MODELREADY_WORKSPACE_ID is empty."
            )
    else:
        raw = DEVELOPER_BOOTSTRAP_WORKSPACE_ID
    return WorkspaceContext(workspace_id=raw, dataset_id=None)


@contextmanager
def bind_developer_bootstrap() -> Iterator[tuple[TenantContext, WorkspaceContext]]:
    """Bind SERVICE tenant/workspace for a legacy CLI process. Scripts only."""
    tenant = load_developer_tenant_context()
    workspace = load_developer_workspace_context()
    with bind_tenant(tenant), bind_workspace(workspace):
        yield tenant, workspace
