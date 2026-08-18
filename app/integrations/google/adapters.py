"""Fake and real Google OAuth/Drive/BigQuery adapters used by prem3-api."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class GoogleTokenSet:
    access_token: str
    refresh_token: str | None
    granted_scopes: tuple[str, ...]
    google_subject: str
    display_email: str | None
    expires_in: int = 3600


@dataclass(frozen=True, slots=True)
class DriveFile:
    file_id: str
    name: str
    mime_type: str
    parents: tuple[str, ...]
    md5: str | None
    head_revision_id: str | None
    version: str | None
    size_bytes: int
    trashed: bool = False


@dataclass(frozen=True, slots=True)
class BigQueryTableInfo:
    project_id: str
    dataset_id: str
    table_id: str
    object_type: str
    schema_fingerprint: str
    etag: str
    last_modified: str
    num_bytes: int
    num_rows: int
    location: str


class GoogleOAuthProvider(Protocol):
    def authorization_url(
        self, *, state: str, scopes: tuple[str, ...], redirect_uri: str
    ) -> str: ...

    def exchange_code(self, *, code: str, redirect_uri: str) -> GoogleTokenSet: ...

    def refresh_access_token(self, *, refresh_token: str) -> str: ...

    def revoke(self, *, token: str) -> None: ...


class DriveClient(Protocol):
    def get_file(self, *, access_token: str, file_id: str) -> DriveFile | None: ...

    def create_folder(
        self, *, access_token: str, name: str, parent_id: str | None
    ) -> DriveFile: ...


class BigQueryClient(Protocol):
    def list_projects(self, *, access_token: str) -> list[dict[str, str]]: ...

    def list_datasets(self, *, access_token: str, project_id: str) -> list[dict[str, str]]: ...

    def list_tables(
        self, *, access_token: str, project_id: str, dataset_id: str
    ) -> list[BigQueryTableInfo]: ...

    def get_table(
        self, *, access_token: str, project_id: str, dataset_id: str, table_id: str
    ) -> BigQueryTableInfo | None: ...

    def get_dataset(
        self, *, access_token: str, project_id: str, dataset_id: str
    ) -> dict[str, Any] | None: ...

    def create_dataset(
        self,
        *,
        access_token: str,
        project_id: str,
        dataset_id: str,
        friendly_name: str,
        location: str,
    ) -> dict[str, Any]: ...

    def can_write_dataset(
        self, *, access_token: str, project_id: str, dataset_id: str
    ) -> bool: ...


class FakeGoogleOAuthProvider:
    def __init__(self) -> None:
        self.codes: dict[str, GoogleTokenSet] = {}
        self.revoked: list[str] = []
        self.authorization_urls: list[str] = []
        self.access_tokens: dict[str, str] = {}

    def seed_code(self, code: str, tokens: GoogleTokenSet) -> None:
        self.codes[code] = tokens
        if tokens.refresh_token:
            self.access_tokens[tokens.refresh_token] = tokens.access_token

    def authorization_url(self, *, state: str, scopes: tuple[str, ...], redirect_uri: str) -> str:
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
            {
                "response_type": "code",
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent",
                "state": state,
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
            }
        )
        self.authorization_urls.append(url)
        return url

    def exchange_code(self, *, code: str, redirect_uri: str) -> GoogleTokenSet:
        del redirect_uri
        if code not in self.codes:
            raise ValueError("Unknown authorization code.")
        return self.codes[code]

    def refresh_access_token(self, *, refresh_token: str) -> str:
        return self.access_tokens.get(refresh_token, "ya29.fake-access")

    def revoke(self, *, token: str) -> None:
        self.revoked.append(token)


class FakeDriveClient:
    def __init__(self) -> None:
        self.files: dict[str, DriveFile] = {}
        self.created: list[str] = []

    def seed(self, file: DriveFile) -> None:
        self.files[file.file_id] = file

    def get_file(self, *, access_token: str, file_id: str) -> DriveFile | None:
        del access_token
        return self.files.get(file_id)

    def create_folder(
        self, *, access_token: str, name: str, parent_id: str | None
    ) -> DriveFile:
        del access_token
        file_id = f"folder_{len(self.files) + 1:04d}"
        folder = DriveFile(
            file_id=file_id,
            name=name,
            mime_type="application/vnd.google-apps.folder",
            parents=(parent_id,) if parent_id else (),
            md5=None,
            head_revision_id=None,
            version="1",
            size_bytes=0,
        )
        self.files[file_id] = folder
        self.created.append(file_id)
        return folder

    def trash(self, file_id: str) -> None:
        existing = self.files.get(file_id)
        if existing is None:
            return
        self.files[file_id] = DriveFile(
            file_id=existing.file_id,
            name=existing.name,
            mime_type=existing.mime_type,
            parents=existing.parents,
            md5=existing.md5,
            head_revision_id=existing.head_revision_id,
            version=existing.version,
            size_bytes=existing.size_bytes,
            trashed=True,
        )


class FakeBigQueryClient:
    def __init__(self) -> None:
        self.projects: list[dict[str, str]] = []
        self.datasets: dict[str, dict[str, Any]] = {}
        self.tables: dict[str, BigQueryTableInfo] = {}
        self.created_datasets: list[str] = []
        self.discovery_tokens: list[str] = []

    def list_projects(self, *, access_token: str) -> list[dict[str, str]]:
        self.discovery_tokens.append(access_token)
        return list(self.projects)

    def list_datasets(self, *, access_token: str, project_id: str) -> list[dict[str, str]]:
        self.discovery_tokens.append(access_token)
        rows = []
        for key, dataset in self.datasets.items():
            if key.startswith(f"{project_id}."):
                rows.append(
                    {
                        "project_id": project_id,
                        "dataset_id": dataset["dataset_id"],
                        "location": dataset.get("location", "US"),
                    }
                )
        return rows

    def list_tables(
        self, *, access_token: str, project_id: str, dataset_id: str
    ) -> list[BigQueryTableInfo]:
        self.discovery_tokens.append(access_token)
        prefix = f"{project_id}.{dataset_id}."
        return [item for key, item in self.tables.items() if key.startswith(prefix)]

    def get_table(
        self, *, access_token: str, project_id: str, dataset_id: str, table_id: str
    ) -> BigQueryTableInfo | None:
        self.discovery_tokens.append(access_token)
        return self.tables.get(f"{project_id}.{dataset_id}.{table_id}")

    def get_dataset(
        self, *, access_token: str, project_id: str, dataset_id: str
    ) -> dict[str, Any] | None:
        self.discovery_tokens.append(access_token)
        return self.datasets.get(f"{project_id}.{dataset_id}")

    def create_dataset(
        self,
        *,
        access_token: str,
        project_id: str,
        dataset_id: str,
        friendly_name: str,
        location: str,
    ) -> dict[str, Any]:
        self.discovery_tokens.append(access_token)
        key = f"{project_id}.{dataset_id}"
        if key in self.datasets:
            return self.datasets[key]
        payload = {
            "project_id": project_id,
            "dataset_id": dataset_id,
            "friendly_name": friendly_name,
            "location": location,
            "write_ok": True,
        }
        self.datasets[key] = payload
        self.created_datasets.append(key)
        return payload

    def seed_dataset(
        self,
        *,
        project_id: str,
        dataset_id: str,
        location: str = "US",
        write_ok: bool = False,
        friendly_name: str | None = None,
    ) -> None:
        self.datasets[f"{project_id}.{dataset_id}"] = {
            "project_id": project_id,
            "dataset_id": dataset_id,
            "friendly_name": friendly_name or dataset_id,
            "location": location,
            "write_ok": write_ok,
        }

    def can_write_dataset(
        self, *, access_token: str, project_id: str, dataset_id: str
    ) -> bool:
        self.discovery_tokens.append(access_token)
        dataset = self.datasets.get(f"{project_id}.{dataset_id}")
        return bool(dataset and dataset.get("write_ok"))


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class RestGoogleOAuthProvider:
    """Authorization-code + refresh-token Google OAuth using the token endpoint."""

    def __init__(self, *, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def authorization_url(self, *, state: str, scopes: tuple[str, ...], redirect_uri: str) -> str:
        return GOOGLE_AUTH_URL + "?" + urlencode(
            {
                "client_id": self._client_id,
                "response_type": "code",
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent",
                "state": state,
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
            }
        )

    def exchange_code(self, *, code: str, redirect_uri: str) -> GoogleTokenSet:
        payload = urlencode(
            {
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        body = _post_form(GOOGLE_TOKEN_URL, payload)
        access_token = str(body.get("access_token") or "")
        if not access_token:
            raise ValueError("Google token exchange did not return an access token.")
        refresh = body.get("refresh_token")
        refresh_token = str(refresh) if refresh else None
        granted = tuple(str(body.get("scope") or "").split())
        subject, email = _userinfo(access_token)
        return GoogleTokenSet(
            access_token=access_token,
            refresh_token=refresh_token,
            granted_scopes=granted,
            google_subject=subject,
            display_email=email,
            expires_in=int(body.get("expires_in") or 3600),
        )

    def refresh_access_token(self, *, refresh_token: str) -> str:
        payload = urlencode(
            {
                "refresh_token": refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        body = _post_form(GOOGLE_TOKEN_URL, payload)
        access_token = str(body.get("access_token") or "")
        if not access_token:
            raise ValueError("Google refresh did not return an access token.")
        return access_token

    def revoke(self, *, token: str) -> None:
        payload = urlencode({"token": token}).encode("utf-8")
        request = Request(GOOGLE_REVOKE_URL, data=payload, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urlopen(request, timeout=15):
            return


def _post_form(url: str, payload: bytes) -> dict[str, Any]:
    request = Request(url, data=payload, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urlopen(request, timeout=15) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Google OAuth response was not an object.")
    return parsed


def _userinfo(access_token: str) -> tuple[str, str | None]:
    request = Request(GOOGLE_USERINFO_URL, method="GET")
    request.add_header("Authorization", f"Bearer {access_token}")
    with urlopen(request, timeout=15) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    subject = str(parsed.get("sub") or "")
    if not subject:
        raise ValueError("Google userinfo did not return a subject.")
    email = parsed.get("email")
    return subject, str(email) if email else None
