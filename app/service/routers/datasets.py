from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.control_plane.models import Dataset, Workspace
from app.control_plane.repository import ControlPlaneRepository
from app.core.tenancy import require_tenant
from app.service.dependencies import (
    authenticated_tenant,
    authorized_dataset,
    authorized_workspace,
    get_control_plane,
)
from app.service.models import CreateDatasetRequest, DatasetListResponse, DatasetResponse
from app.service.pagination import paginate_by_id

router = APIRouter(prefix="/v1/workspaces/{workspace_id}/datasets", tags=["datasets"])


def _to_response(dataset: Dataset) -> DatasetResponse:
    return DatasetResponse(
        dataset_id=dataset.dataset_id,
        workspace_id=dataset.workspace_id,
        name=dataset.name,
        status=dataset.status.value,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@router.get("", operation_id="listDatasets", response_model=DatasetListResponse)
async def list_datasets(
    workspace: Annotated[Workspace, Depends(authorized_workspace)],
    repo: Annotated[ControlPlaneRepository, Depends(get_control_plane)],
    _tenant: Annotated[object, Depends(authenticated_tenant)],
    limit: Annotated[int | None, Query(ge=1, le=50)] = None,
    cursor: str | None = None,
) -> DatasetListResponse:
    tenant = require_tenant()
    rows = repo.list_datasets_for_workspace(
        tenant_id=tenant.tenant_id, workspace_id=workspace.workspace_id
    )
    page, next_cursor = paginate_by_id(
        rows, cursor=cursor, limit=limit, id_of=lambda item: item.dataset_id
    )
    return DatasetListResponse(items=[_to_response(item) for item in page], next_cursor=next_cursor)


@router.post(
    "",
    operation_id="createDataset",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dataset(
    body: CreateDatasetRequest,
    workspace: Annotated[Workspace, Depends(authorized_workspace)],
    repo: Annotated[ControlPlaneRepository, Depends(get_control_plane)],
) -> DatasetResponse:
    tenant = require_tenant()
    dataset = repo.create_dataset(
        tenant_id=tenant.tenant_id,
        workspace_id=workspace.workspace_id,
        name=body.name,
    )
    return _to_response(dataset)


@router.get(
    "/{dataset_id}",
    operation_id="getDataset",
    response_model=DatasetResponse,
)
async def get_dataset(
    dataset: Annotated[Dataset, Depends(authorized_dataset)],
) -> DatasetResponse:
    return _to_response(dataset)
