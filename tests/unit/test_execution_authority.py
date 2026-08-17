"""Server-owned execution authority, repository isolation, and ADK schema tests."""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

import pytest

from app.agent import root_agent
from app.config import settings
from app.core.contracts import DurableRunState
from app.core.errors import (
    AuthorityMismatchError,
    ExecutionContextMissingError,
    SafetyViolationError,
    ValidationBlockedError,
)
from app.core.execution_context import (
    ExecutionContext,
    ExecutionInputRef,
    ExecutionLayout,
    bind_execution,
    bind_service_execution,
    require_execution_context,
)
from app.core.legacy_execution import prepare_legacy_dataset_execution
from app.core.run_repository import (
    LocalFilesystemRunRepository,
    bind_run_repository,
    reset_run_repository,
)
from app.core.state import RunStage
from app.core.tenancy import (
    AuthState,
    TenantContext,
    WorkspaceContext,
    bind_tenant,
    bind_workspace,
    is_forbidden_model_supplied_authority_parameter,
)
from app.tools.precloud import agent_tool_names
from app.tools.run_tools import initialize_dataset_run, inspect_dataset_run


def _tenant(tenant_id: str = "tenant-a") -> TenantContext:
    return TenantContext(tenant_id=tenant_id, auth_state=AuthState.AUTHENTICATED)


def _workspace(workspace_id: str = "project-a", dataset_id: str | None = None) -> WorkspaceContext:
    return WorkspaceContext(workspace_id=workspace_id, dataset_id=dataset_id)


def _execution(
    *,
    tenant_id: str = "tenant-a",
    workspace_id: str = "project-a",
    dataset_id: str = "dataset-a",
    run_id: str = "run-x",
    layout: ExecutionLayout = ExecutionLayout.MISSION_2,
) -> ExecutionContext:
    return ExecutionContext(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        dataset_id=dataset_id,
        run_id=run_id,
        input=ExecutionInputRef(package_uri="gs://raw/tenant-a/package/"),
        layout=layout,
    )


def _tool_callable(tool: object):
    func = getattr(tool, "func", None) or getattr(tool, "_func", None)
    if callable(func):
        return func
    if callable(tool):
        return tool
    return None


def _registered_tool_signatures() -> dict[str, inspect.Signature]:
    signatures: dict[str, inspect.Signature] = {}
    for tool in getattr(root_agent, "tools", None) or []:
        fn = _tool_callable(tool)
        if fn is None:
            continue
        name = getattr(fn, "__name__", "") or getattr(tool, "name", "")
        if name:
            signatures[name] = inspect.signature(fn)
    return signatures


def test_execution_context_required() -> None:
    with pytest.raises(ExecutionContextMissingError):
        require_execution_context()


def test_execution_context_restored_after_scope() -> None:
    outer = _execution(run_id="run-outer")
    inner = _execution(run_id="run-inner")
    with bind_tenant(_tenant()), bind_workspace(_workspace()):
        with bind_execution(outer):
            assert require_execution_context().run_id == "run-outer"
            with bind_execution(inner):
                assert require_execution_context().run_id == "run-inner"
            assert require_execution_context().run_id == "run-outer"
    with pytest.raises(ExecutionContextMissingError):
        require_execution_context()


def test_execution_context_must_match_tenant() -> None:
    with bind_tenant(_tenant("tenant-a")), bind_workspace(_workspace()):
        with pytest.raises(AuthorityMismatchError, match="tenant_id"):
            with bind_execution(_execution(tenant_id="tenant-b")):
                pass


def test_execution_context_must_match_workspace() -> None:
    with bind_tenant(_tenant()), bind_workspace(_workspace("project-a")):
        with pytest.raises(AuthorityMismatchError, match="workspace_id"):
            with bind_execution(_execution(workspace_id="project-b")):
                pass


def test_execution_context_dataset_mismatch_denied() -> None:
    with bind_tenant(_tenant()), bind_workspace(_workspace(dataset_id="dataset-a")):
        with pytest.raises(AuthorityMismatchError, match="dataset_id"):
            with bind_execution(_execution(dataset_id="dataset-b")):
                pass


def test_context_cleared_between_sequential_runs() -> None:
    with bind_tenant(_tenant()), bind_workspace(_workspace()):
        with bind_execution(_execution(run_id="run-one")):
            assert require_execution_context().run_id == "run-one"
        with pytest.raises(ExecutionContextMissingError):
            require_execution_context()
        with bind_execution(_execution(run_id="run-two")):
            assert require_execution_context().run_id == "run-two"
    with pytest.raises(ExecutionContextMissingError):
        require_execution_context()


def test_concurrent_execution_context_isolation() -> None:
    async def _bound(run_id: str, hold: asyncio.Event, release: asyncio.Event) -> str:
        with bind_tenant(_tenant()), bind_workspace(_workspace()):
            with bind_execution(_execution(run_id=run_id)):
                hold.set()
                await release.wait()
                return require_execution_context().run_id

    async def _run() -> None:
        hold_a = asyncio.Event()
        hold_b = asyncio.Event()
        release = asyncio.Event()
        task_a = asyncio.create_task(_bound("run-a", hold_a, release))
        task_b = asyncio.create_task(_bound("run-b", hold_b, release))
        await asyncio.gather(hold_a.wait(), hold_b.wait())
        with pytest.raises(ExecutionContextMissingError):
            require_execution_context()
        release.set()
        seen_a, seen_b = await asyncio.gather(task_a, task_b)
        assert seen_a == "run-a"
        assert seen_b == "run-b"

    asyncio.run(_run())


def test_execution_rebind_mismatch_denied() -> None:
    with bind_tenant(_tenant()), bind_workspace(_workspace()):
        with bind_execution(_execution(run_id="run-x", dataset_id="dataset-a")):
            assert require_execution_context().dataset_id == "dataset-a"
            with pytest.raises(AuthorityMismatchError):
                with bind_execution(_execution(tenant_id="tenant-b", run_id="run-x")):
                    pass
            assert require_execution_context().run_id == "run-x"


def test_run_repository_requires_authority_for_mission2_layout(tmp_path: Path) -> None:
    repo = LocalFilesystemRunRepository(
        root=tmp_path, raw_bucket="raw", artifact_bucket="artifacts"
    )
    with pytest.raises(ExecutionContextMissingError):
        repo.artifact_prefix("run-x")


def test_run_repository_does_not_use_settings_tenant_fallback() -> None:
    assert not hasattr(settings, "organization_id")
    assert not hasattr(settings, "workspace_id")
    import app.core.run_repository as run_repository

    source = inspect.getsource(run_repository)
    assert "settings.organization_id" not in source
    assert "settings.workspace_id" not in source


def _state(*, tenant_id: str, workspace_id: str, run_id: str) -> DurableRunState:
    return DurableRunState(
        run_id=run_id,
        organization_id=tenant_id,
        workspace_id=workspace_id,
        package_uri="gs://raw/internal/package/",
        package_fingerprint="fp",
        stage=RunStage.ASSESSING,
        artifact_prefix=f"gs://artifacts/{tenant_id}/{workspace_id}/datasets/dataset-a/runs/{run_id}/",
        status="IN_PROGRESS",
    )


def test_cross_tenant_run_id_is_not_global_authority(tmp_path: Path) -> None:
    repo = LocalFilesystemRunRepository(
        root=tmp_path, raw_bucket="raw", artifact_bucket="artifacts"
    )
    state = _state(tenant_id="tenant-a", workspace_id="project-a", run_id="run-x")
    with bind_service_execution(
        tenant_id="tenant-a",
        workspace_id="project-a",
        dataset_id="dataset-a",
        run_id="run-x",
        layout=ExecutionLayout.MISSION_2,
    ):
        repo.save_run(state)
        assert repo.run_exists("run-x")
    with bind_service_execution(
        tenant_id="tenant-b",
        workspace_id="project-b",
        dataset_id="dataset-a",
        run_id="run-x",
        layout=ExecutionLayout.MISSION_2,
    ):
        with pytest.raises(ValidationBlockedError, match="does not exist"):
            repo.load_run("run-x")
        assert repo.run_exists("run-x") is False


def test_cross_workspace_same_tenant_denied(tmp_path: Path) -> None:
    repo = LocalFilesystemRunRepository(
        root=tmp_path, raw_bucket="raw", artifact_bucket="artifacts"
    )
    state = _state(tenant_id="tenant-a", workspace_id="project-a", run_id="run-d")
    with bind_service_execution(
        tenant_id="tenant-a",
        workspace_id="project-a",
        dataset_id="dataset-d",
        run_id="run-d",
        layout=ExecutionLayout.MISSION_2,
    ):
        repo.save_run(state)
    with bind_service_execution(
        tenant_id="tenant-a",
        workspace_id="project-b",
        dataset_id="dataset-d",
        run_id="run-d",
        layout=ExecutionLayout.MISSION_2,
    ):
        with pytest.raises(ValidationBlockedError, match="does not exist"):
            repo.load_run("run-d")


def test_registered_tool_schemas_have_no_tenant_authority() -> None:
    signatures = _registered_tool_signatures()
    assert signatures
    leaked: list[str] = []
    for name, signature in signatures.items():
        for param in signature.parameters:
            if is_forbidden_model_supplied_authority_parameter(param):
                leaked.append(f"{name}.{param}")
    assert not leaked, leaked


def test_registered_tool_schemas_have_no_storage_authority() -> None:
    signatures = _registered_tool_signatures()
    storage_names = {
        "package_uri",
        "gcs_uri",
        "gcs_path",
        "bucket",
        "artifact_path",
        "raw_path",
        "filesystem_path",
        "file_path",
        "path",
        "local_path",
        "storage_uri",
        "object_uri",
        "bq_dataset",
        "bq_table",
        "bq_project",
        "bigquery_destination",
        "destination_table",
        "destination_dataset",
    }
    leaked: list[str] = []
    for name, signature in signatures.items():
        for param in signature.parameters:
            if param.strip().lower().replace("-", "_") in storage_names:
                leaked.append(f"{name}.{param}")
    assert not leaked, leaked


def test_initialize_dataset_run_has_no_package_uri_argument() -> None:
    params = inspect.signature(initialize_dataset_run).parameters
    assert "package_uri" not in params
    assert list(params) == []


def test_agent_cannot_select_run_id_if_run_is_server_owned() -> None:
    signatures = _registered_tool_signatures()
    for name, signature in signatures.items():
        assert "run_id" not in signature.parameters, name
        assert "requested_run_id" not in signature.parameters, name


def test_legacy_adapter_not_registered_as_agent_tool() -> None:
    names = agent_tool_names(root_agent)
    assert "prepare_legacy_dataset_execution" not in names
    assert "validate_legacy_package_uri" not in names
    assert "bind_service_execution" not in names


def test_legacy_package_uri_cross_authority_rejected(tmp_path: Path) -> None:
    repo = LocalFilesystemRunRepository(
        root=tmp_path, raw_bucket="raw", artifact_bucket="artifacts"
    )
    token = bind_run_repository(repo)
    try:
        with bind_service_execution(
            tenant_id="tenant-b",
            workspace_id="project-b",
            run_id="run-x",
            dataset_id="dataset-a",
        ):
            with pytest.raises(SafetyViolationError, match="tenant prefix"):
                with prepare_legacy_dataset_execution(
                    package_uri="gs://raw/tenant-a/packages/dataset-a/",
                    run_id="run-x",
                    dataset_id="dataset-a",
                ):
                    pass
    finally:
        reset_run_repository(token)


def test_bigquery_destination_not_model_supplied() -> None:
    signatures = _registered_tool_signatures()
    publish = signatures["validate_and_publish_run"]
    assert list(publish.parameters) == []
    eda = signatures["run_meridian_eda"]
    assert list(eda.parameters) == []


def test_inspect_dataset_run_has_no_run_id_argument() -> None:
    assert list(inspect.signature(inspect_dataset_run).parameters) == []
