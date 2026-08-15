"""Google Cloud Storage adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google.cloud import storage

from app.core.errors import SafetyViolationError


def parse_gs_uri(uri: str) -> tuple[str, str]:
    """Split `gs://bucket/path` into bucket and blob path."""
    value = uri.strip()
    if not value.startswith("gs://"):
        raise SafetyViolationError("Only gs:// URIs are accepted.")
    rest = value[5:]
    bucket, separator, blob = rest.partition("/")
    if not bucket or not separator:
        raise SafetyViolationError("GCS URI must include a bucket and object path.")
    return bucket, blob


def join_gs(bucket: str, *parts: str) -> str:
    blob = "/".join(part.strip("/") for part in parts if part)
    return f"gs://{bucket}/{blob}"


def list_objects(bucket_name: str, prefix: str = "") -> list[str]:
    client = storage.Client()
    return sorted(blob.name for blob in client.list_blobs(bucket_name, prefix=prefix))


def list_object_metadata(bucket_name: str, prefix: str = "") -> list[dict[str, Any]]:
    client = storage.Client()
    records: list[dict[str, Any]] = []
    for blob in client.list_blobs(bucket_name, prefix=prefix):
        if blob.name.endswith("/"):
            continue
        records.append(
            {
                "name": blob.name,
                "generation": str(blob.generation) if blob.generation is not None else "",
                "size": int(blob.size or 0),
                "updated": blob.updated.isoformat() if blob.updated else None,
            }
        )
    return sorted(records, key=lambda item: str(item["name"]))


def download_prefix(bucket_name: str, prefix: str, dest: str | Path) -> list[dict[str, Any]]:
    client = storage.Client()
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True)
    normalized = prefix.strip("/")
    records: list[dict[str, Any]] = []
    for blob in client.list_blobs(bucket_name, prefix=prefix):
        if blob.name.endswith("/"):
            continue
        relative = blob.name
        if normalized:
            relative = blob.name[len(normalized) :].lstrip("/")
        if not relative:
            continue
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(target))
        records.append(
            {
                "name": blob.name,
                "relative": relative.replace("\\", "/"),
                "generation": str(blob.generation) if blob.generation is not None else "",
                "path": str(target),
            }
        )
    return records


def download_file(uri: str, dest: str | Path) -> Path:
    bucket_name, blob_name = parse_gs_uri(uri)
    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    blob = storage.Client().bucket(bucket_name).blob(blob_name)
    blob.download_to_filename(str(target))
    return target


def upload_file(local_path: str | Path, uri: str) -> str:
    bucket_name, blob_name = parse_gs_uri(uri)
    path = Path(local_path)
    blob = storage.Client().bucket(bucket_name).blob(blob_name)
    blob.upload_from_filename(str(path))
    return uri


def blob_exists(uri: str) -> bool:
    bucket_name, blob_name = parse_gs_uri(uri)
    blob = storage.Client().bucket(bucket_name).blob(blob_name)
    return bool(blob.exists())
