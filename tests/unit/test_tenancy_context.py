"""Request-scoped TenantContext binding and fail-closed resolution."""

from __future__ import annotations

import asyncio
import inspect

import pytest

from app.config import load_settings
from app.core.developer_bootstrap import bind_developer_bootstrap
from app.core.errors import TenantContextMissingError, WorkspaceContextMissingError
from app.core.tenancy import (
    AuthState,
    TenantContext,
    WorkspaceContext,
    bind_tenant,
    bind_workspace,
    current_tenant,
    require_tenant,
    require_workspace,
)


def _tenant(tenant_id: str = "tenant-a") -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id,
        user_id="user-a",
        auth_state=AuthState.AUTHENTICATED,
        entitlement_snapshot_id=None,
    )


def test_tenant_context_required() -> None:
    with pytest.raises(TenantContextMissingError):
        require_tenant()


def test_no_default_tenant_fallback() -> None:
    settings = load_settings()
    assert settings.organization_id
    with pytest.raises(TenantContextMissingError):
        require_tenant()
    assert current_tenant() is None


def test_tenant_context_restored_after_scope() -> None:
    outer = _tenant("tenant-outer")
    inner = _tenant("tenant-inner")
    with bind_tenant(outer):
        assert require_tenant().tenant_id == "tenant-outer"
        with bind_tenant(inner):
            assert require_tenant().tenant_id == "tenant-inner"
        assert require_tenant().tenant_id == "tenant-outer"
    with pytest.raises(TenantContextMissingError):
        require_tenant()


def test_nested_context_restores_parent() -> None:
    parent = _tenant("tenant-parent")
    child = _tenant("tenant-child")
    with bind_tenant(parent):
        with bind_tenant(child):
            assert require_tenant().tenant_id == "tenant-child"
        assert require_tenant().tenant_id == "tenant-parent"


def test_context_cleared_after_exception() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with bind_tenant(_tenant()):
            raise RuntimeError("boom")
    with pytest.raises(TenantContextMissingError):
        require_tenant()


def test_sequential_contexts_do_not_leak() -> None:
    with bind_tenant(_tenant("tenant-one")):
        assert require_tenant().tenant_id == "tenant-one"
    with pytest.raises(TenantContextMissingError):
        require_tenant()
    with bind_tenant(_tenant("tenant-two")):
        assert require_tenant().tenant_id == "tenant-two"
    with pytest.raises(TenantContextMissingError):
        require_tenant()


def test_tenant_and_workspace_contexts_are_independent() -> None:
    with bind_tenant(_tenant()):
        with pytest.raises(WorkspaceContextMissingError):
            require_workspace()
    with bind_workspace(WorkspaceContext(workspace_id="project-a")):
        with pytest.raises(TenantContextMissingError):
            require_tenant()


def test_developer_bootstrap_requires_explicit_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODELREADY_ORGANIZATION_ID", "music-center")
    monkeypatch.setenv("MODELREADY_WORKSPACE_ID", "mmm-demo")
    with pytest.raises(TenantContextMissingError):
        require_tenant()
    with pytest.raises(WorkspaceContextMissingError):
        require_workspace()
    with bind_developer_bootstrap() as (tenant, workspace):
        assert require_tenant().tenant_id == "music-center"
        assert require_workspace().workspace_id == "mmm-demo"
        assert tenant.auth_state is AuthState.SERVICE
        assert workspace.dataset_id is None
    with pytest.raises(TenantContextMissingError):
        require_tenant()


def test_concurrent_tasks_do_not_leak_tenant_context() -> None:
    async def _bound(tenant_id: str, hold: asyncio.Event, release: asyncio.Event) -> str:
        with bind_tenant(_tenant(tenant_id)):
            hold.set()
            await release.wait()
            return require_tenant().tenant_id

    async def _run() -> None:
        hold_a = asyncio.Event()
        hold_b = asyncio.Event()
        release = asyncio.Event()
        task_a = asyncio.create_task(_bound("tenant-a", hold_a, release))
        task_b = asyncio.create_task(_bound("tenant-b", hold_b, release))
        await asyncio.gather(hold_a.wait(), hold_b.wait())
        with pytest.raises(TenantContextMissingError):
            require_tenant()
        release.set()
        seen_a, seen_b = await asyncio.gather(task_a, task_b)
        assert seen_a == "tenant-a"
        assert seen_b == "tenant-b"
        with pytest.raises(TenantContextMissingError):
            require_tenant()

    asyncio.run(_run())


def test_anonymous_auth_state_does_not_exist() -> None:
    assert not hasattr(AuthState, "ANONYMOUS")
    assert {item.value for item in AuthState} == {"AUTHENTICATED", "SERVICE"}


def test_runtime_modules_do_not_import_developer_bootstrap() -> None:
    import app.core.run_coordinator as run_coordinator
    import app.core.run_repository as run_repository
    import app.tools.run_tools as run_tools

    for module in (run_coordinator, run_repository, run_tools):
        assert "developer_bootstrap" not in inspect.getsource(module)
