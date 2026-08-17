"""Server-owned Dataset/Evaluation execution identity.

TenantContext is customer authority. WorkspaceContext is MMM Project authority.
ExecutionContext is the already-authorized Evaluation plus its input reference.
A repository handle is persistence only and is not customer authority.

The registered ADK model never constructs this object. Trusted CLI/API code does.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.errors import (
    AuthorityMismatchError,
    ExecutionContextMissingError,
    TenantContextMissingError,
    WorkspaceContextMissingError,
)
from app.core.identifiers import validate_resource_identifier
from app.core.tenancy import (
    AuthState,
    TenantContext,
    WorkspaceContext,
    bind_tenant,
    bind_workspace,
    current_tenant,
    current_workspace,
    require_tenant,
    require_workspace,
)


class ExecutionLayout(StrEnum):
    """Explicit storage layout. Never inferred from object existence."""

    LEGACY = "LEGACY"
    MISSION_2 = "MISSION_2"


class ExecutionInputRef(BaseModel):
    """Server-owned package/upload reference. Not a model-supplied argument."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    package_uri: str
    package_fingerprint: str | None = None

    @field_validator("package_uri")
    @classmethod
    def _validate_package_uri(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("package_uri must not be empty.")
        return text


class ExecutionContext(BaseModel):
    """Immutable Evaluation execution identity for one bound operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str
    workspace_id: str
    dataset_id: str
    run_id: str
    input: ExecutionInputRef
    layout: ExecutionLayout
    dataset_role: str | None = None
    qualification_mode: str | None = None

    @field_validator("tenant_id")
    @classmethod
    def _tenant_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="tenant_id")

    @field_validator("workspace_id")
    @classmethod
    def _workspace_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="workspace_id")

    @field_validator("dataset_id")
    @classmethod
    def _dataset_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="dataset_id")

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="run_id")


_current_execution: ContextVar[ExecutionContext | None] = ContextVar(
    "prem3_execution_context", default=None
)


def require_execution_context() -> ExecutionContext:
    """Fail closed. There is no default execution."""
    ctx = _current_execution.get()
    if ctx is None:
        raise ExecutionContextMissingError(
            "No execution context bound. Refusing Dataset evaluation operation."
        )
    return ctx


def bound_run_id() -> str:
    return require_execution_context().run_id


def current_execution_context() -> ExecutionContext | None:
    return _current_execution.get()


def assert_execution_matches_authority(ctx: ExecutionContext) -> None:
    """Reject mismatched tenant/workspace/dataset. Do not repair."""
    tenant = require_tenant()
    workspace = require_workspace()
    if ctx.tenant_id != tenant.tenant_id:
        raise AuthorityMismatchError("Execution tenant_id does not match bound TenantContext.")
    if ctx.workspace_id != workspace.workspace_id:
        raise AuthorityMismatchError(
            "Execution workspace_id does not match bound WorkspaceContext."
        )
    if workspace.dataset_id is not None and ctx.dataset_id != workspace.dataset_id:
        raise AuthorityMismatchError(
            "Execution dataset_id does not match bound WorkspaceContext.dataset_id."
        )


def owner_tenant_workspace() -> tuple[str, str]:
    """Tenant/workspace for persistence. Execution wins when bound."""
    execution = current_execution_context()
    if execution is not None:
        assert_execution_matches_authority(execution)
        return execution.tenant_id, execution.workspace_id
    tenant = current_tenant()
    workspace = current_workspace()
    if tenant is None:
        raise TenantContextMissingError(
            "No tenant context bound. Refusing authenticated tenant operation."
        )
    if workspace is None:
        raise WorkspaceContextMissingError(
            "No authorized MMM Project context bound. Refusing project operation."
        )
    return tenant.tenant_id, workspace.workspace_id


@contextmanager
def bind_execution(ctx: ExecutionContext) -> Iterator[ExecutionContext]:
    assert_execution_matches_authority(ctx)
    token = _current_execution.set(ctx)
    try:
        yield ctx
    finally:
        _current_execution.reset(token)


@contextmanager
def bind_service_execution(
    *,
    tenant_id: str,
    workspace_id: str,
    run_id: str,
    dataset_id: str = "internal-dataset",
    package_uri: str = "gs://raw/internal/package/",
    layout: ExecutionLayout = ExecutionLayout.LEGACY,
) -> Iterator[ExecutionContext]:
    """Trusted internal/test binder for tenant + workspace + execution.

    Not a registered ADK tool. Used by MEL fixtures and intelligence assignment.
    """
    tenant = TenantContext(
        tenant_id=tenant_id,
        user_id=None,
        auth_state=AuthState.SERVICE,
        entitlement_snapshot_id=None,
    )
    workspace = WorkspaceContext(workspace_id=workspace_id, dataset_id=None)
    ctx = ExecutionContext(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        dataset_id=dataset_id,
        run_id=run_id,
        input=ExecutionInputRef(package_uri=package_uri),
        layout=layout,
    )
    with bind_tenant(tenant), bind_workspace(workspace), bind_execution(ctx) as bound:
        yield bound

