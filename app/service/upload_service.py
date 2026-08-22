"""Server-owned Dataset upload create / complete / verify."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath

from app.control_plane.ids import new_upload_file_id, new_upload_id
from app.control_plane.models import (
    DatasetUpload,
    DatasetUploadFile,
    Feature,
    UploadStatus,
)
from app.control_plane.repository import ControlPlaneRepository
from app.core.resource_paths import raw_upload_prefix
from app.core.tenancy import require_tenant
from app.integrations.gcs import join_gs
from app.service.entitlements import require_feature
from app.service.errors import (
    ProblemFieldError,
    resource_not_found,
    validation_error,
)
from app.service.object_store import ObjectStore
from app.service.upload_config import (
    ACCEPTED_CONTENT_TYPES,
    ACCEPTED_UPLOAD_EXTENSIONS,
    UPLOAD_MANIFEST_NAME,
    UploadConfig,
)
from app.service.upload_signing import SignedPutUrl, UploadSigner

_UNSAFE_FILENAME = re.compile(r"[\\/]|^\.\.($|/)|[\x00-\x1f\x7f]")


def validate_presentation_filename(filename: str) -> str:
    text = filename.strip()
    if not text:
        raise validation_error(
            [ProblemFieldError(field="filename", message="filename is required.")]
        )
    if _UNSAFE_FILENAME.search(text) or text in {".", ".."}:
        raise validation_error(
            [
                ProblemFieldError(
                    field="filename",
                    message="filename must not contain path separators or traversal.",
                )
            ]
        )
    if PurePosixPath(text).name != text:
        raise validation_error(
            [ProblemFieldError(field="filename", message="filename must be a bare file name.")]
        )
    suffix = PurePosixPath(text).suffix.lower()
    if suffix not in ACCEPTED_UPLOAD_EXTENSIONS:
        raise validation_error(
            [
                ProblemFieldError(
                    field="filename",
                    message=(
                        "Unsupported upload format. Accepted extensions: "
                        + ", ".join(sorted(ACCEPTED_UPLOAD_EXTENSIONS))
                    ),
                )
            ]
        )
    return text


def validate_content_type(content_type: str) -> str:
    value = content_type.strip().lower()
    if value not in ACCEPTED_CONTENT_TYPES:
        raise validation_error(
            [
                ProblemFieldError(
                    field="content_type",
                    message="Unsupported content_type for Dataset upload.",
                )
            ]
        )
    return value


class UploadService:
    def __init__(
        self,
        *,
        repo: ControlPlaneRepository,
        config: UploadConfig,
        signer: UploadSigner,
        object_store: ObjectStore,
    ) -> None:
        self._repo = repo
        self._config = config
        self._signer = signer
        self._store = object_store

    def create_upload(
        self,
        *,
        workspace_id: str,
        dataset_id: str,
        files: list[dict[str, object]],
        idempotency_key: str | None = None,
    ) -> tuple[DatasetUpload, list[SignedPutUrl]]:
        tenant = require_tenant()
        require_feature(self._repo, Feature.DATA_UPLOAD)
        dataset = self._repo.get_dataset_for_workspace(
            tenant_id=tenant.tenant_id, workspace_id=workspace_id, dataset_id=dataset_id
        )
        if dataset is None:
            raise resource_not_found()
        if idempotency_key:
            existing = self._repo.get_idempotent_result(
                tenant_id=tenant.tenant_id,
                operation="create_upload",
                key=idempotency_key,
            )
            if existing is not None:
                upload = self._repo.get_upload(
                    tenant_id=tenant.tenant_id,
                    workspace_id=workspace_id,
                    dataset_id=dataset_id,
                    upload_id=str(existing["upload_id"]),
                )
                if upload is None:
                    raise resource_not_found()
                return upload, self._sign_files(upload)

        if not files:
            raise validation_error(
                [ProblemFieldError(field="files", message="At least one file is required.")]
            )
        if len(files) > self._config.max_files:
            raise validation_error(
                [
                    ProblemFieldError(
                        field="files",
                        message=f"At most {self._config.max_files} files are allowed.",
                    )
                ]
            )

        now = datetime.now(UTC)
        upload_id = new_upload_id()
        prefix = raw_upload_prefix(
            tenant.tenant_id, workspace_id, dataset_id, upload_id
        )
        prepared: list[DatasetUploadFile] = []
        total = 0
        for index, item in enumerate(files):
            filename = validate_presentation_filename(str(item.get("filename") or ""))
            content_type = validate_content_type(str(item.get("content_type") or ""))
            try:
                size = int(item.get("size_bytes"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                raise validation_error(
                    [
                        ProblemFieldError(
                            field=f"files[{index}].size_bytes",
                            message="size_bytes must be an integer.",
                        )
                    ]
                ) from None
            if size <= 0:
                raise validation_error(
                    [
                        ProblemFieldError(
                            field=f"files[{index}].size_bytes",
                            message="size_bytes must be positive.",
                        )
                    ]
                )
            if size > self._config.max_file_bytes:
                raise validation_error(
                    [
                        ProblemFieldError(
                            field=f"files[{index}].size_bytes",
                            message="File exceeds the configured maximum size.",
                        )
                    ]
                )
            total += size
            if total > self._config.max_total_bytes:
                raise validation_error(
                    [
                        ProblemFieldError(
                            field="files",
                            message="Total upload size exceeds the configured maximum.",
                        )
                    ]
                )
            file_id = new_upload_file_id()
            # Opaque file_id prevents collisions; presentation basename is retained so
            # runtime package inventory can recognize model_intent.json / sources.
            object_name = f"{prefix}files/{file_id}/{filename}"
            prepared.append(
                DatasetUploadFile(
                    upload_file_id=file_id,
                    original_filename=filename,
                    object_name=object_name,
                    content_type=content_type,
                    declared_size_bytes=size,
                    created_at=now,
                )
            )

        expires_at = now + timedelta(seconds=self._config.signed_url_ttl_seconds)
        upload = DatasetUpload(
            tenant_id=tenant.tenant_id,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            upload_id=upload_id,
            status=UploadStatus.PENDING,
            object_prefix=prefix,
            files=prepared,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
        )
        stored = self._repo.create_upload(upload)
        signed = self._sign_files(stored)
        if idempotency_key:
            self._repo.put_idempotent_result(
                tenant_id=tenant.tenant_id,
                operation="create_upload",
                key=idempotency_key,
                result={"upload_id": stored.upload_id},
            )
        return stored, signed

    def _sign_files(self, upload: DatasetUpload) -> list[SignedPutUrl]:
        signed: list[SignedPutUrl] = []
        for file_rec in upload.files:
            signed.append(
                self._signer.sign_put(
                    bucket=self._config.raw_bucket,
                    object_name=file_rec.object_name,
                    content_type=file_rec.content_type,
                    size_bytes=file_rec.declared_size_bytes,
                    expires_in_seconds=self._config.signed_url_ttl_seconds,
                    service_account_email=self._config.runtime_sa,
                )
            )
        return signed

    def get_upload(
        self, *, workspace_id: str, dataset_id: str, upload_id: str
    ) -> DatasetUpload:
        tenant = require_tenant()
        upload = self._repo.get_upload(
            tenant_id=tenant.tenant_id,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            upload_id=upload_id,
        )
        if upload is None:
            raise resource_not_found()
        return upload

    def complete_upload(
        self, *, workspace_id: str, dataset_id: str, upload_id: str
    ) -> DatasetUpload:
        tenant = require_tenant()
        require_feature(self._repo, Feature.DATA_UPLOAD)
        upload = self._repo.get_upload(
            tenant_id=tenant.tenant_id,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            upload_id=upload_id,
        )
        if upload is None:
            raise resource_not_found()
        if upload.status is UploadStatus.VERIFIED:
            return upload

        now = datetime.now(UTC)
        verified_files: list[DatasetUploadFile] = []
        for file_rec in upload.files:
            if not file_rec.object_name.startswith(upload.object_prefix):
                return self._mark_invalid(upload, now)
            meta = self._store.get_object_metadata(
                bucket=self._config.raw_bucket, object_name=file_rec.object_name
            )
            if meta is None:
                return self._mark_invalid(upload, now)
            if meta.size != file_rec.declared_size_bytes:
                return self._mark_invalid(upload, now)
            if not meta.generation:
                return self._mark_invalid(upload, now)
            verified_files.append(
                file_rec.model_copy(
                    update={
                        "actual_size_bytes": meta.size,
                        "generation": meta.generation,
                        "etag": meta.etag,
                        "crc32c": meta.crc32c,
                        "md5_hash": meta.md5_hash,
                        "verified_at": now,
                    }
                )
            )

        package_uri = join_gs(self._config.raw_bucket, upload.object_prefix)
        if not package_uri.endswith("/"):
            package_uri = f"{package_uri}/"
        fingerprint = _fingerprint_verified_files(verified_files)
        # Materialize a one-time presentation-named runtime view under the upload
        # prefix so existing package inventory (model_intent.json at package root)
        # keeps working while opaque files/{id}/{filename} remain generation-frozen.
        for item in verified_files:
            runtime_object = f"{upload.object_prefix}{item.original_filename}"
            if runtime_object == item.object_name:
                continue
            source = self._store.get_object_metadata(
                bucket=self._config.raw_bucket, object_name=item.object_name
            )
            if source is None:
                return self._mark_invalid(upload, now)
            self._store.copy_object(
                bucket=self._config.raw_bucket,
                source_object_name=item.object_name,
                dest_object_name=runtime_object,
                if_generation_match=0,
            )
        manifest = {
            "schema": UPLOAD_MANIFEST_NAME,
            "tenant_id": upload.tenant_id,
            "workspace_id": upload.workspace_id,
            "dataset_id": upload.dataset_id,
            "upload_id": upload.upload_id,
            "package_uri": package_uri,
            "package_fingerprint": fingerprint,
            "files": [
                {
                    "upload_file_id": item.upload_file_id,
                    "original_filename": item.original_filename,
                    "object_name": item.object_name,
                    "generation": item.generation,
                    "size_bytes": item.actual_size_bytes,
                    "content_type": item.content_type,
                    "crc32c": item.crc32c,
                    "md5_hash": item.md5_hash,
                }
                for item in verified_files
            ],
        }
        self._store.write_json(
            bucket=self._config.raw_bucket,
            object_name=f"{upload.object_prefix}{UPLOAD_MANIFEST_NAME}",
            payload=manifest,
        )
        verified = upload.model_copy(
            update={
                "status": UploadStatus.VERIFIED,
                "files": verified_files,
                "package_uri": package_uri,
                "package_fingerprint": fingerprint,
                "updated_at": now,
                "completed_at": now,
            }
        )
        return self._repo.update_upload(verified)

    def _mark_invalid(self, upload: DatasetUpload, now: datetime) -> DatasetUpload:
        invalid = upload.model_copy(
            update={
                "status": UploadStatus.INVALID,
                "updated_at": now,
                "completed_at": now,
            }
        )
        return self._repo.update_upload(invalid)


def _fingerprint_verified_files(files: list[DatasetUploadFile]) -> str:
    digest = hashlib.sha256()
    for item in sorted(files, key=lambda row: row.upload_file_id):
        digest.update(item.upload_file_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update((item.generation or "").encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(item.actual_size_bytes or 0).encode("utf-8"))
        digest.update(b"\0")
        digest.update((item.crc32c or item.md5_hash or "").encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()
