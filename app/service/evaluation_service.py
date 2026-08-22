"""Create first-class Evaluation resources from VERIFIED uploads."""

from __future__ import annotations

from datetime import UTC, datetime

from app.control_plane.ids import new_run_id
from app.control_plane.models import (
    DatasetEvaluationRef,
    EvaluationStatus,
    Feature,
    UploadStatus,
)
from app.control_plane.repository import ControlPlaneRepository
from app.core.tenancy import require_tenant
from app.service.entitlements import require_feature
from app.service.errors import (
    ProblemFieldError,
    resource_not_found,
    validation_error,
)


class EvaluationService:
    def __init__(self, *, repo: ControlPlaneRepository) -> None:
        self._repo = repo

    def create_evaluation(
        self,
        *,
        workspace_id: str,
        dataset_id: str,
        upload_id: str,
        idempotency_key: str | None = None,
    ) -> DatasetEvaluationRef:
        tenant = require_tenant()
        snapshot = require_feature(self._repo, Feature.DATASET_ASSESSMENT)
        dataset = self._repo.get_dataset_for_workspace(
            tenant_id=tenant.tenant_id, workspace_id=workspace_id, dataset_id=dataset_id
        )
        if dataset is None:
            raise resource_not_found()

        if idempotency_key:
            existing = self._repo.get_idempotent_result(
                tenant_id=tenant.tenant_id,
                operation="create_evaluation",
                key=idempotency_key,
            )
            if existing is not None:
                ref = self._repo.get_evaluation_ref(
                    tenant_id=tenant.tenant_id, run_id=str(existing["run_id"])
                )
                if ref is None:
                    raise resource_not_found()
                return ref

        upload = self._repo.get_upload(
            tenant_id=tenant.tenant_id,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            upload_id=upload_id,
        )
        if upload is None:
            raise resource_not_found()
        if upload.status is not UploadStatus.VERIFIED:
            raise validation_error(
                [
                    ProblemFieldError(
                        field="upload_id",
                        message="Upload must be VERIFIED before Evaluation creation.",
                    )
                ]
            )
        if not upload.package_uri:
            raise validation_error(
                [
                    ProblemFieldError(
                        field="upload_id",
                        message="Verified upload is missing package_uri.",
                    )
                ]
            )

        now = datetime.now(UTC)
        run_id = new_run_id()
        evaluation = DatasetEvaluationRef(
            tenant_id=tenant.tenant_id,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            upload_id=upload.upload_id,
            run_id=run_id,
            entitlement_snapshot_id=snapshot.snapshot_id,
            status=EvaluationStatus.ACCEPTED,
            package_uri=upload.package_uri,
            package_fingerprint=upload.package_fingerprint,
            created_at=now,
            updated_at=now,
        )
        stored = self._repo.put_evaluation_ref(evaluation)
        if idempotency_key:
            self._repo.put_idempotent_result(
                tenant_id=tenant.tenant_id,
                operation="create_evaluation",
                key=idempotency_key,
                result={"run_id": stored.run_id},
            )
        return stored

    def list_evaluations(
        self, *, workspace_id: str, dataset_id: str
    ) -> list[DatasetEvaluationRef]:
        tenant = require_tenant()
        dataset = self._repo.get_dataset_for_workspace(
            tenant_id=tenant.tenant_id, workspace_id=workspace_id, dataset_id=dataset_id
        )
        if dataset is None:
            raise resource_not_found()
        return self._repo.list_evaluations_for_dataset(
            tenant_id=tenant.tenant_id,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
        )

    def get_evaluation(self, *, run_id: str) -> DatasetEvaluationRef:
        tenant = require_tenant()
        ref = self._repo.get_evaluation_ref(tenant_id=tenant.tenant_id, run_id=run_id)
        if ref is None:
            raise resource_not_found()
        return ref
