"""Trusted server-only Evaluation → ExecutionContext construction."""

from __future__ import annotations

from app.control_plane.models import DatasetEvaluationRef, DatasetUpload, UploadStatus
from app.control_plane.repository import ControlPlaneRepository
from app.core.errors import AuthorityMismatchError, SafetyViolationError
from app.core.execution_context import (
    ExecutionContext,
    ExecutionInputRef,
    ExecutionLayout,
)
from app.core.tenancy import (
    TenantContext,
    WorkspaceContext,
    require_tenant,
)


def execution_input_from_verified_upload(upload: DatasetUpload) -> ExecutionInputRef:
    """Derive ExecutionInputRef from a VERIFIED DatasetUpload. Fail closed otherwise."""
    if upload.status is not UploadStatus.VERIFIED:
        raise SafetyViolationError("Execution input requires a VERIFIED upload.")
    if not upload.package_uri:
        raise SafetyViolationError("Verified upload is missing package_uri.")
    for file_rec in upload.files:
        if not file_rec.generation:
            raise SafetyViolationError("Verified upload is missing frozen object generations.")
        if not file_rec.object_name.startswith(upload.object_prefix):
            raise SafetyViolationError("Upload object escaped its server-owned prefix.")
    return ExecutionInputRef(
        package_uri=upload.package_uri,
        package_fingerprint=upload.package_fingerprint,
    )


def execution_context_from_evaluation(
    *,
    repo: ControlPlaneRepository,
    evaluation: DatasetEvaluationRef,
    tenant: TenantContext | None = None,
) -> tuple[TenantContext, WorkspaceContext, ExecutionContext]:
    """Build authorized contexts for one Evaluation. Caller cannot supply package_uri."""
    bound_tenant = tenant or require_tenant()
    if evaluation.tenant_id != bound_tenant.tenant_id:
        raise AuthorityMismatchError("Evaluation tenant does not match TenantContext.")

    upload = repo.get_upload(
        tenant_id=evaluation.tenant_id,
        workspace_id=evaluation.workspace_id,
        dataset_id=evaluation.dataset_id,
        upload_id=evaluation.upload_id,
    )
    if upload is None:
        raise SafetyViolationError("Evaluation upload linkage is missing.")
    if (
        upload.tenant_id != evaluation.tenant_id
        or upload.workspace_id != evaluation.workspace_id
        or upload.dataset_id != evaluation.dataset_id
    ):
        raise AuthorityMismatchError("Upload/Evaluation linkage mismatch.")
    if upload.package_uri != evaluation.package_uri:
        raise AuthorityMismatchError("Evaluation package_uri does not match verified upload.")

    input_ref = execution_input_from_verified_upload(upload)
    workspace = WorkspaceContext(
        workspace_id=evaluation.workspace_id,
        dataset_id=evaluation.dataset_id,
    )
    execution = ExecutionContext(
        tenant_id=evaluation.tenant_id,
        workspace_id=evaluation.workspace_id,
        dataset_id=evaluation.dataset_id,
        run_id=evaluation.run_id,
        input=input_ref,
        layout=ExecutionLayout.MISSION_2,
    )
    service_tenant = TenantContext(
        tenant_id=evaluation.tenant_id,
        user_id=bound_tenant.user_id,
        auth_state=bound_tenant.auth_state,
        entitlement_snapshot_id=evaluation.entitlement_snapshot_id,
    )
    return service_tenant, workspace, execution
