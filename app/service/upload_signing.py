"""V4 signed PUT URL issuance for Dataset uploads.

Cloud Run uses workload identity + IAM Credentials signBlob. No private key file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlparse

from google.auth import default as google_auth_default
from google.auth.transport.requests import Request
from google.cloud import storage


@dataclass(frozen=True, slots=True)
class SignedPutUrl:
    url: str
    method: str
    headers: dict[str, str]
    expires_at: datetime
    bucket: str
    object_name: str


class UploadSigner(Protocol):
    def sign_put(
        self,
        *,
        bucket: str,
        object_name: str,
        content_type: str,
        size_bytes: int,
        expires_in_seconds: int,
        service_account_email: str | None,
    ) -> SignedPutUrl: ...


class FakeUploadSigner:
    """Deterministic signer for unit tests. Does not call GCP."""

    def __init__(self, *, base_url: str = "https://storage.googleapis.com") -> None:
        self.base_url = base_url.rstrip("/")
        self.calls: list[dict[str, object]] = []

    def sign_put(
        self,
        *,
        bucket: str,
        object_name: str,
        content_type: str,
        size_bytes: int,
        expires_in_seconds: int,
        service_account_email: str | None,
    ) -> SignedPutUrl:
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
        url = (
            f"{self.base_url}/{bucket}/{object_name}"
            f"?X-Goog-Algorithm=GOOG4-RSA-SHA256"
            f"&X-Goog-Expires={expires_in_seconds}"
            f"&fake_sign=1"
        )
        headers = {
            "Content-Type": content_type,
            "x-goog-content-length-range": f"{size_bytes},{size_bytes}",
            "x-goog-if-generation-match": "0",
        }
        self.calls.append(
            {
                "bucket": bucket,
                "object_name": object_name,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "service_account_email": service_account_email,
            }
        )
        return SignedPutUrl(
            url=url,
            method="PUT",
            headers=headers,
            expires_at=expires_at,
            bucket=bucket,
            object_name=object_name,
        )


class GcsV4UploadSigner:
    """Issue V4 signed PUT URLs using IAM signBlob when no private key is present."""

    def __init__(self, *, client: storage.Client | None = None) -> None:
        self._client = client

    def sign_put(
        self,
        *,
        bucket: str,
        object_name: str,
        content_type: str,
        size_bytes: int,
        expires_in_seconds: int,
        service_account_email: str | None,
    ) -> SignedPutUrl:
        client = self._client or storage.Client()
        blob = client.bucket(bucket).blob(object_name)
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
        headers = {
            "Content-Type": content_type,
            "x-goog-content-length-range": f"{size_bytes},{size_bytes}",
            "x-goog-if-generation-match": "0",
        }
        credentials, _ = google_auth_default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())
        kwargs: dict[str, object] = {
            "version": "v4",
            "expiration": expires_at,
            "method": "PUT",
            "content_type": content_type,
            "headers": headers,
        }
        if service_account_email:
            kwargs["service_account_email"] = service_account_email
            kwargs["access_token"] = credentials.token
        url = blob.generate_signed_url(**kwargs)
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise RuntimeError("Signed upload URL must be HTTPS.")
        return SignedPutUrl(
            url=url,
            method="PUT",
            headers=headers,
            expires_at=expires_at,
            bucket=bucket,
            object_name=object_name,
        )
