"""Google Cloud Storage adapter."""

from __future__ import annotations

from google.cloud import storage


def list_objects(bucket_name: str, prefix: str = "") -> list[str]:
    client = storage.Client()
    return sorted(blob.name for blob in client.list_blobs(bucket_name, prefix=prefix))
