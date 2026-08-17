"""Canonical Mission 2 resource path construction.

This module is the only place new Mission 2 object prefixes are assembled.
Builders return bucket-relative prefixes. Bucket names stay in Settings.
Callers wrap with gs:// only at an infrastructure boundary.

Low-level functions take explicit identifiers for tests and migrations.
Context-owned helpers read bound TenantContext / WorkspaceContext.

Passing dataset_id here does not prove Dataset ownership. Ownership validation
arrives with the product resource repository.

Legacy golden-path objects remain under organization/workspace/runs/<run_id>/.
Callers must use legacy_run_artifact_prefix() deliberately. This module never
silently selects legacy vs Mission 2 layout.
"""

from __future__ import annotations

from app.core.identifiers import validate_resource_identifier
from app.core.tenancy import require_tenant, require_workspace


def _join_prefix(*parts: tuple[str, str]) -> str:
    segments = [validate_resource_identifier(value, field=field) for field, value in parts]
    return "/".join(segments) + "/"


def planning_artifact_prefix(tenant_id: str, workspace_id: str, planning_run_id: str) -> str:
    return _join_prefix(
        ("tenant_id", tenant_id),
        ("workspace_id", workspace_id),
        ("literal", "planning"),
        ("planning_run_id", planning_run_id),
    )


def dataset_run_artifact_prefix(
    tenant_id: str,
    workspace_id: str,
    dataset_id: str,
    run_id: str,
) -> str:
    return _join_prefix(
        ("tenant_id", tenant_id),
        ("workspace_id", workspace_id),
        ("literal", "datasets"),
        ("dataset_id", dataset_id),
        ("literal", "runs"),
        ("run_id", run_id),
    )


def registry_overlay_prefix(tenant_id: str) -> str:
    return _join_prefix(
        ("tenant_id", tenant_id),
        ("literal", "registry"),
        ("literal", "overlay"),
    )


def raw_upload_prefix(
    tenant_id: str,
    workspace_id: str,
    dataset_id: str,
    upload_id: str,
) -> str:
    return _join_prefix(
        ("tenant_id", tenant_id),
        ("workspace_id", workspace_id),
        ("literal", "datasets"),
        ("dataset_id", dataset_id),
        ("literal", "uploads"),
        ("upload_id", upload_id),
    )


def legacy_run_artifact_prefix(organization_id: str, workspace_id: str, run_id: str) -> str:
    """Explicit pre-Mission-2 golden layout: <org>/<workspace>/runs/<run_id>/."""
    return _join_prefix(
        ("organization_id", organization_id),
        ("workspace_id", workspace_id),
        ("literal", "runs"),
        ("run_id", run_id),
    )


def current_planning_artifact_prefix(planning_run_id: str) -> str:
    tenant = require_tenant()
    workspace = require_workspace()
    return planning_artifact_prefix(tenant.tenant_id, workspace.workspace_id, planning_run_id)


def current_dataset_run_artifact_prefix(dataset_id: str, run_id: str) -> str:
    """Build a Mission 2 evaluation prefix from bound context.

    dataset_id is not authorization. The product resource repository must later
    prove the Dataset belongs to the bound workspace.
    """
    tenant = require_tenant()
    workspace = require_workspace()
    return dataset_run_artifact_prefix(
        tenant.tenant_id,
        workspace.workspace_id,
        dataset_id,
        run_id,
    )


def current_registry_overlay_prefix() -> str:
    return registry_overlay_prefix(require_tenant().tenant_id)


def current_raw_upload_prefix(dataset_id: str, upload_id: str) -> str:
    tenant = require_tenant()
    workspace = require_workspace()
    return raw_upload_prefix(
        tenant.tenant_id,
        workspace.workspace_id,
        dataset_id,
        upload_id,
    )
