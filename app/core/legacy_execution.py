"""Trusted developer/CLI adapter for historical Dataset proof execution.

CLI and cloud-proof scripts may still accept a package URI. Registered ADK
tools on root_agent must never import or expose this module. The model cannot
construct ExecutionContext or ExecutionInputRef from free-form arguments.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlparse

from app.core.errors import SafetyViolationError
from app.core.execution_context import (
    ExecutionContext,
    ExecutionInputRef,
    ExecutionLayout,
    bind_execution,
)
from app.core.identifiers import validate_resource_identifier
from app.core.run_repository import get_run_repository, validate_package_uri
from app.core.tenancy import require_tenant, require_workspace
from app.mel.assignment import resolve_assignment_identity


def validate_legacy_package_uri(package_uri: str, *, tenant_id: str) -> str:
    """Validate a trusted CLI package URI against configured infrastructure.

    Rejects traversal, unexpected schemes/buckets, and first-segment tenant
    mismatch. Does not grant the model authority to choose a package.
    """
    repo = get_run_repository()
    normalized = validate_package_uri(package_uri, repo)
    parsed = urlparse(normalized)
    blob = parsed.path.lstrip("/")
    first = blob.split("/", 1)[0]
    expected = validate_resource_identifier(tenant_id, field="tenant_id")
    if first != expected:
        raise SafetyViolationError(
            "package_uri tenant prefix does not match bound developer tenant."
        )
    return normalized


@contextmanager
def prepare_legacy_dataset_execution(
    *,
    package_uri: str,
    run_id: str,
    dataset_id: str,
    dataset_role: str | None = None,
    qualification_mode: str | None = None,
    layout: ExecutionLayout = ExecutionLayout.LEGACY,
) -> Iterator[ExecutionContext]:
    """Bind server-owned execution for a trusted developer/CLI caller.

    Caller must already have TenantContext and WorkspaceContext bound
    (typically via bind_developer_bootstrap).
    """
    tenant = require_tenant()
    workspace = require_workspace()
    normalized = validate_legacy_package_uri(package_uri, tenant_id=tenant.tenant_id)
    assigned_dataset_id, assigned_role, assigned_mode = resolve_assignment_identity(
        dataset_id=dataset_id,
        dataset_role=dataset_role,
        qualification_mode=qualification_mode,
    )
    ctx = ExecutionContext(
        tenant_id=tenant.tenant_id,
        workspace_id=workspace.workspace_id,
        dataset_id=assigned_dataset_id,
        run_id=run_id,
        input=ExecutionInputRef(package_uri=normalized),
        layout=layout,
        dataset_role=assigned_role,
        qualification_mode=assigned_mode,
    )
    with bind_execution(ctx) as bound:
        yield bound
