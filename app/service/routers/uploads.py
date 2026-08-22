"""HTTP routes for Dataset uploads."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status

from app.control_plane.models import Dataset, DatasetUpload
from app.service.dependencies import (
    authenticated_tenant,
    authorized_dataset,
    get_upload_service,
)
from app.service.models import (
    CompleteUploadResponse,
    CreateUploadRequest,
    UploadFileInstruction,
    UploadFileResponse,
    UploadResponse,
)
from app.service.upload_service import UploadService
from app.service.upload_signing import SignedPutUrl

router = APIRouter(
    prefix="/v1/workspaces/{workspace_id}/datasets/{dataset_id}/uploads",
    tags=["uploads"],
)


def _file_response(item) -> UploadFileResponse:
    return UploadFileResponse(
        upload_file_id=item.upload_file_id,
        filename=item.original_filename,
        content_type=item.content_type,
        declared_size_bytes=item.declared_size_bytes,
        actual_size_bytes=item.actual_size_bytes,
        status="VERIFIED" if item.verified_at is not None else "PENDING",
    )


def _to_response(
    upload: DatasetUpload, signed: list[SignedPutUrl] | None = None
) -> UploadResponse:
    instructions: list[UploadFileInstruction] = []
    if signed:
        by_object = {item.object_name: item for item in signed}
        for file_rec in upload.files:
            put = by_object.get(file_rec.object_name)
            if put is None:
                continue
            instructions.append(
                UploadFileInstruction(
                    upload_file_id=file_rec.upload_file_id,
                    filename=file_rec.original_filename,
                    method=put.method,
                    url=put.url,
                    required_headers=put.headers,
                    expires_at=put.expires_at,
                )
            )
    return UploadResponse(
        upload_id=upload.upload_id,
        dataset_id=upload.dataset_id,
        status=upload.status.value,
        files=[_file_response(item) for item in upload.files],
        upload_instructions=instructions,
        expires_at=upload.expires_at,
        created_at=upload.created_at,
        updated_at=upload.updated_at,
        completed_at=upload.completed_at,
    )


@router.post(
    "",
    operation_id="createDatasetUpload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_upload(
    body: CreateUploadRequest,
    dataset: Annotated[Dataset, Depends(authorized_dataset)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    _tenant: Annotated[object, Depends(authenticated_tenant)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> UploadResponse:
    upload, signed = service.create_upload(
        workspace_id=dataset.workspace_id,
        dataset_id=dataset.dataset_id,
        files=[item.model_dump() for item in body.files],
        idempotency_key=idempotency_key,
    )
    return _to_response(upload, signed)


@router.get(
    "/{upload_id}",
    operation_id="getDatasetUpload",
    response_model=UploadResponse,
)
async def get_upload(
    upload_id: str,
    dataset: Annotated[Dataset, Depends(authorized_dataset)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    _tenant: Annotated[object, Depends(authenticated_tenant)],
) -> UploadResponse:
    upload = service.get_upload(
        workspace_id=dataset.workspace_id,
        dataset_id=dataset.dataset_id,
        upload_id=upload_id,
    )
    return _to_response(upload)


@router.post(
    "/{upload_id}/complete",
    operation_id="completeDatasetUpload",
    response_model=CompleteUploadResponse,
)
async def complete_upload(
    upload_id: str,
    dataset: Annotated[Dataset, Depends(authorized_dataset)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    _tenant: Annotated[object, Depends(authenticated_tenant)],
) -> CompleteUploadResponse:
    upload = service.complete_upload(
        workspace_id=dataset.workspace_id,
        dataset_id=dataset.dataset_id,
        upload_id=upload_id,
    )
    return CompleteUploadResponse(
        upload_id=upload.upload_id,
        dataset_id=upload.dataset_id,
        status=upload.status.value,
        files=[_file_response(item) for item in upload.files],
        package_fingerprint=upload.package_fingerprint,
        completed_at=upload.completed_at,
    )
