"""Request-scoped WorkspaceContext binding and fail-closed resolution."""

from __future__ import annotations

import pytest

from app.config import load_settings
from app.core.errors import TenantContextMissingError, WorkspaceContextMissingError
from app.core.tenancy import (
    AuthState,
    TenantContext,
    WorkspaceContext,
    bind_tenant,
    bind_workspace,
    require_tenant,
    require_workspace,
)


def test_workspace_context_required() -> None:
    with pytest.raises(WorkspaceContextMissingError):
        require_workspace()


def test_workspace_context_restored_after_scope() -> None:
    outer = WorkspaceContext(workspace_id="project-outer")
    inner = WorkspaceContext(workspace_id="project-inner", dataset_id="dataset-inner")
    with bind_workspace(outer):
        assert require_workspace().workspace_id == "project-outer"
        assert require_workspace().dataset_id is None
        with bind_workspace(inner):
            assert require_workspace().workspace_id == "project-inner"
            assert require_workspace().dataset_id == "dataset-inner"
        assert require_workspace().workspace_id == "project-outer"
        assert require_workspace().dataset_id is None
    with pytest.raises(WorkspaceContextMissingError):
        require_workspace()


def test_workspace_context_cleared_after_exception() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with bind_workspace(WorkspaceContext(workspace_id="project-a")):
            raise RuntimeError("boom")
    with pytest.raises(WorkspaceContextMissingError):
        require_workspace()


def test_sequential_workspace_contexts_do_not_leak() -> None:
    with bind_workspace(WorkspaceContext(workspace_id="project-one")):
        assert require_workspace().workspace_id == "project-one"
    with pytest.raises(WorkspaceContextMissingError):
        require_workspace()
    with bind_workspace(WorkspaceContext(workspace_id="project-two")):
        assert require_workspace().workspace_id == "project-two"


def test_workspace_and_tenant_contexts_compose() -> None:
    tenant = TenantContext(
        tenant_id="tenant-a",
        auth_state=AuthState.AUTHENTICATED,
    )
    workspace = WorkspaceContext(workspace_id="project-a", dataset_id="dataset-a")
    with bind_tenant(tenant), bind_workspace(workspace):
        assert require_tenant().tenant_id == "tenant-a"
        assert require_workspace().workspace_id == "project-a"
        assert require_workspace().dataset_id == "dataset-a"


def test_env_workspace_does_not_bind_require_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODELREADY_ORGANIZATION_ID", "music-center")
    monkeypatch.setenv("MODELREADY_WORKSPACE_ID", "mmm-demo")
    settings = load_settings()
    assert settings.workspace_id == "mmm-demo"
    with pytest.raises(WorkspaceContextMissingError):
        require_workspace()
    with pytest.raises(TenantContextMissingError):
        require_tenant()
