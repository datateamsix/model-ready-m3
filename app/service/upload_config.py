"""Upload limits, accepted formats, and signed-URL configuration."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings

ACCEPTED_UPLOAD_EXTENSIONS: frozenset[str] = frozenset({".csv", ".parquet", ".json"})
ACCEPTED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "text/csv",
        "application/csv",
        "application/json",
        "application/octet-stream",
        "application/parquet",
        "application/x-parquet",
    }
)
UPLOAD_MANIFEST_NAME = "prem3_upload_manifest.v1.json"


@dataclass(frozen=True, slots=True)
class UploadConfig:
    raw_bucket: str
    signed_url_ttl_seconds: int
    max_files: int
    max_file_bytes: int
    max_total_bytes: int
    runtime_sa: str | None

    @classmethod
    def from_settings(cls, settings: Settings) -> UploadConfig:
        bucket = (settings.raw_bucket or "").strip()
        if not bucket:
            raise ValueError("MODELREADY_RAW_BUCKET is required for Dataset uploads.")
        return cls(
            raw_bucket=bucket,
            signed_url_ttl_seconds=settings.upload_signed_url_ttl_seconds,
            max_files=settings.upload_max_files,
            max_file_bytes=settings.upload_max_file_bytes,
            max_total_bytes=settings.upload_max_total_bytes,
            runtime_sa=settings.runtime_sa,
        )
