"""Drive MIME / filename mapping into DatasetUpload formats. Sheets are deferred."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.governance.codes import SUPPORTED_IMPORT_FORMATS

DRIVE_MIME_TO_FORMAT: dict[str, str] = {
    "text/csv": "csv",
    "application/csv": "csv",
    "application/json": "json",
    "application/vnd.apache.parquet": "parquet",
    "application/parquet": "parquet",
    "application/x-parquet": "parquet",
}

SHEETS_MIME = "application/vnd.google-apps.spreadsheet"


def drive_format(*, mime_type: str, name: str) -> str | None:
    if mime_type == SHEETS_MIME:
        return None
    mapped = DRIVE_MIME_TO_FORMAT.get(mime_type)
    if mapped is not None:
        return mapped
    suffix = PurePosixPath(name).suffix.lower().lstrip(".")
    if suffix in SUPPORTED_IMPORT_FORMATS:
        return suffix
    return None


def gcs_format(*, filename: str, content_type: str) -> str | None:
    suffix = PurePosixPath(filename).suffix.lower().lstrip(".")
    if suffix in SUPPORTED_IMPORT_FORMATS:
        return suffix
    mapped = DRIVE_MIME_TO_FORMAT.get(content_type)
    return mapped
