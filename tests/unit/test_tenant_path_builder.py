"""Canonical Mission 2 path builders and identifier rejection."""

from __future__ import annotations

import inspect

import pytest

from app.core.errors import (
    InvalidResourceIdentifierError,
    TenantContextMissingError,
    WorkspaceContextMissingError,
)
from app.core.identifiers import validate_resource_identifier
from app.core.resource_paths import (
    current_dataset_run_artifact_prefix,
    current_planning_artifact_prefix,
    current_raw_upload_prefix,
    current_registry_overlay_prefix,
    dataset_run_artifact_prefix,
    legacy_run_artifact_prefix,
    planning_artifact_prefix,
    raw_upload_prefix,
    registry_overlay_prefix,
)
from app.core.tenancy import (
    AuthState,
    TenantContext,
    WorkspaceContext,
    bind_tenant,
    bind_workspace,
    is_forbidden_model_supplied_authority_parameter,
)


def test_path_builder_rejects_empty_segments() -> None:
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier("", field="tenant_id")
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier("   ", field="tenant_id")


def test_path_builder_rejects_dot_segments() -> None:
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier(".", field="workspace_id")
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier("..", field="workspace_id")


def test_path_builder_rejects_traversal() -> None:
    with pytest.raises(InvalidResourceIdentifierError):
        dataset_run_artifact_prefix("tenant-a", "project-a", "../other", "run-1")
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier("../tenant-a", field="tenant_id")


def test_path_builder_rejects_forward_slash() -> None:
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier("tenant/a", field="tenant_id")


def test_path_builder_rejects_backslash() -> None:
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier("tenant\\a", field="tenant_id")


def test_path_builder_rejects_uri_shaped_identifier() -> None:
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier("gs://bucket/obj", field="tenant_id")
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier("https://example.invalid/x", field="run_id")
    with pytest.raises(InvalidResourceIdentifierError):
        validate_resource_identifier("file://tmp", field="upload_id")


def test_dataset_run_path_shape() -> None:
    prefix = dataset_run_artifact_prefix("tenant-a", "project-a", "dataset-a", "run-1")
    assert prefix == "tenant-a/project-a/datasets/dataset-a/runs/run-1/"
    assert not prefix.startswith("gs://")


def test_raw_upload_path_shape() -> None:
    prefix = raw_upload_prefix("tenant-a", "project-a", "dataset-a", "upload-1")
    assert prefix == "tenant-a/project-a/datasets/dataset-a/uploads/upload-1/"


def test_planning_path_shape() -> None:
    prefix = planning_artifact_prefix("tenant-a", "project-a", "plan-1")
    assert prefix == "tenant-a/project-a/planning/plan-1/"


def test_registry_overlay_path_shape() -> None:
    prefix = registry_overlay_prefix("tenant-a")
    assert prefix == "tenant-a/registry/overlay/"


def test_legacy_path_is_explicit() -> None:
    legacy = legacy_run_artifact_prefix("music-center", "mmm-demo", "run-1")
    modern = dataset_run_artifact_prefix("music-center", "mmm-demo", "dataset-a", "run-1")
    assert legacy == "music-center/mmm-demo/runs/run-1/"
    assert "/datasets/" not in legacy
    assert modern == "music-center/mmm-demo/datasets/dataset-a/runs/run-1/"
    assert inspect.signature(legacy_run_artifact_prefix).parameters["organization_id"]
    source = inspect.getsource(legacy_run_artifact_prefix)
    assert "datasets" not in source


def test_context_owned_helpers_require_bound_authority() -> None:
    with pytest.raises(TenantContextMissingError):
        current_dataset_run_artifact_prefix("dataset-a", "run-1")
    with bind_tenant(
        TenantContext(tenant_id="tenant-a", auth_state=AuthState.SERVICE)
    ):
        with pytest.raises(WorkspaceContextMissingError):
            current_planning_artifact_prefix("plan-1")


def test_context_owned_dataset_run_prefix_uses_bound_ids() -> None:
    tenant = TenantContext(tenant_id="tenant-a", auth_state=AuthState.AUTHENTICATED)
    workspace = WorkspaceContext(workspace_id="project-a")
    with bind_tenant(tenant), bind_workspace(workspace):
        assert (
            current_dataset_run_artifact_prefix("dataset-a", "run-1")
            == "tenant-a/project-a/datasets/dataset-a/runs/run-1/"
        )
        assert current_planning_artifact_prefix("plan-1") == "tenant-a/project-a/planning/plan-1/"
        assert current_raw_upload_prefix("dataset-a", "upload-1") == (
            "tenant-a/project-a/datasets/dataset-a/uploads/upload-1/"
        )
        assert current_registry_overlay_prefix() == "tenant-a/registry/overlay/"


def test_forbidden_authority_parameter_vocabulary() -> None:
    assert is_forbidden_model_supplied_authority_parameter("tenant_id")
    assert is_forbidden_model_supplied_authority_parameter("workspace_id")
    assert is_forbidden_model_supplied_authority_parameter("package_uri")
    assert is_forbidden_model_supplied_authority_parameter("plan")
    assert is_forbidden_model_supplied_authority_parameter("run_id")
    assert is_forbidden_model_supplied_authority_parameter("requested_run_id")
    assert is_forbidden_model_supplied_authority_parameter("bucket")
    assert is_forbidden_model_supplied_authority_parameter("google_refresh_token")
    assert is_forbidden_model_supplied_authority_parameter("connection_id")
    assert is_forbidden_model_supplied_authority_parameter("root_folder_id")
    assert not is_forbidden_model_supplied_authority_parameter("issue_ids")
    assert not is_forbidden_model_supplied_authority_parameter("response_kind")
