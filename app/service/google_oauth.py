"""Clerk-gated Google OAuth and tenant-scoped GoogleConnection lifecycle."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from app.control_plane.ids import (
    new_credential_ref,
    new_google_connection_id,
    new_oauth_transaction_id,
    new_receipt_id,
)
from app.control_plane.models import Feature, GoogleConnection, GoogleOAuthTransaction
from app.control_plane.repository import ControlPlaneRepository
from app.core.tenancy import require_tenant
from app.governance.codes import (
    BindingStatus,
    CheckSeverity,
    ConnectionStatus,
    GoogleCapability,
    GovernanceCheckCode,
    ImportReadinessStatus,
)
from app.governance.import_contract import GovernanceCheckResult, ImportReadinessReceipt
from app.integrations.google.adapters import GoogleOAuthProvider
from app.integrations.google.capabilities import (
    capabilities_from_scopes,
    parse_capabilities,
    scopes_for_capabilities,
)
from app.integrations.google.vault import CredentialVault
from app.service.entitlements import require_feature
from app.service.errors import (
    APIError,
    ProblemFieldError,
    resource_not_found,
    validation_error,
)
from app.service.security_log import security_log

OAUTH_STATE_BYTES = 32
OAUTH_TTL_SECONDS = 600


def hash_oauth_state(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def new_oauth_state() -> str:
    return secrets.token_urlsafe(OAUTH_STATE_BYTES)


class GoogleConnectionService:
    def __init__(
        self,
        *,
        repo: ControlPlaneRepository,
        vault: CredentialVault,
        oauth: GoogleOAuthProvider | None,
        redirect_uri: str,
        frontend_origin: str,
        ttl_seconds: int = OAUTH_TTL_SECONDS,
    ) -> None:
        self._repo = repo
        self._vault = vault
        self._oauth = oauth
        self._redirect_uri = redirect_uri
        self._frontend_origin = frontend_origin.rstrip("/")
        self._ttl_seconds = ttl_seconds

    def start_oauth(
        self,
        *,
        capabilities: list[str],
        workspace_id: str | None,
        dataset_id: str | None,
        return_path: str,
        initiating_user_id: str,
    ) -> tuple[str, datetime]:
        require_feature(self._repo, Feature.DATA_UPLOAD)
        if self._oauth is None:
            raise _oauth_not_configured()
        tenant = require_tenant()
        parsed = _parse_requested_capabilities(capabilities)
        if workspace_id is not None:
            workspace = self._repo.get_workspace_for_tenant(
                tenant_id=tenant.tenant_id, workspace_id=workspace_id
            )
            if workspace is None:
                raise resource_not_found()
        if dataset_id is not None:
            if workspace_id is None:
                raise validation_error(
                    [
                        ProblemFieldError(
                            field="dataset_id",
                            message="dataset_id requires an authorized workspace_id.",
                        )
                    ]
                )
            dataset = self._repo.get_dataset_for_workspace(
                tenant_id=tenant.tenant_id,
                workspace_id=workspace_id,
                dataset_id=dataset_id,
            )
            if dataset is None:
                raise resource_not_found()
        now = datetime.now(UTC)
        state = new_oauth_state()
        scopes = scopes_for_capabilities(parsed)
        txn = GoogleOAuthTransaction(
            transaction_id=new_oauth_transaction_id(),
            state_hash=hash_oauth_state(state),
            tenant_id=tenant.tenant_id,
            initiating_user_id=initiating_user_id,
            workspace_id=workspace_id,
            dataset_id=dataset_id,
            requested_capabilities=tuple(item.value for item in parsed),
            requested_scopes=scopes,
            return_path=return_path,
            created_at=now,
            expires_at=now + timedelta(seconds=self._ttl_seconds),
            consumed_at=None,
        )
        self._repo.put_oauth_transaction(txn)
        authorization_url = self._oauth.authorization_url(
            state=state, scopes=scopes, redirect_uri=self._redirect_uri
        )
        security_log(
            "google.oauth.start",
            tenant_id=tenant.tenant_id,
            transaction_id=txn.transaction_id,
            capabilities=",".join(txn.requested_capabilities),
        )
        return authorization_url, txn.expires_at

    def complete_oauth(
        self,
        *,
        state: str | None,
        code: str | None,
        error: str | None,
    ) -> str:
        if self._oauth is None:
            return self._redirect({"google": "error", "code": "OAUTH_NOT_CONFIGURED"})
        if error:
            return self._redirect({"google": "error", "code": "OAUTH_DENIED"})
        if not state or not code:
            return self._redirect({"google": "error", "code": "OAUTH_INVALID_CALLBACK"})
        now = datetime.now(UTC)
        txn = self._repo.get_oauth_transaction_by_state_hash(hash_oauth_state(state))
        if txn is None:
            return self._redirect(
                {"google": "error", "code": "OAUTH_STATE_UNKNOWN"}, "/app/settings"
            )
        if txn.consumed_at is not None:
            return self._redirect(
                {"google": "error", "code": "OAUTH_STATE_REPLAY"}, txn.return_path
            )
        if txn.expires_at <= now:
            return self._redirect(
                {"google": "error", "code": "OAUTH_STATE_EXPIRED"}, txn.return_path
            )
        try:
            tokens = self._oauth.exchange_code(code=code, redirect_uri=self._redirect_uri)
        except Exception:
            security_log("google.oauth.exchange_failed", transaction_id=txn.transaction_id)
            return self._redirect(
                {"google": "error", "code": "OAUTH_EXCHANGE_FAILED"}, txn.return_path
            )
        consumed = self._repo.consume_oauth_transaction(
            state_hash=txn.state_hash, consumed_at=now
        )
        if consumed is None:
            return self._redirect(
                {"google": "error", "code": "OAUTH_STATE_REPLAY"}, txn.return_path
            )
        granted = capabilities_from_scopes(list(tokens.granted_scopes))
        existing = self._connection_for_subject(
            tenant_id=txn.tenant_id, google_subject=tokens.google_subject
        )
        if existing is not None and existing.status != ConnectionStatus.REVOKED.value:
            merged_scopes = tuple(
                sorted(set(existing.granted_scopes) | set(tokens.granted_scopes))
            )
            merged_caps = tuple(
                item.value for item in capabilities_from_scopes(list(merged_scopes))
            )
            if tokens.refresh_token:
                self._vault.put_refresh_token(
                    tenant_id=existing.tenant_id,
                    credential_ref=existing.credential_ref,
                    refresh_token=tokens.refresh_token,
                )
            connection = existing.model_copy(
                update={
                    "status": ConnectionStatus.ACTIVE.value,
                    "granted_scopes": merged_scopes,
                    "capabilities": merged_caps,
                    "display_email": tokens.display_email or existing.display_email,
                    "updated_at": now,
                    "last_verified_at": now,
                    "revoked_at": None,
                }
            )
        else:
            if not tokens.refresh_token:
                return self._redirect(
                    {"google": "error", "code": "OAUTH_REFRESH_TOKEN_MISSING"},
                    txn.return_path,
                )
            credential_ref = new_credential_ref()
            self._vault.put_refresh_token(
                tenant_id=txn.tenant_id,
                credential_ref=credential_ref,
                refresh_token=tokens.refresh_token,
            )
            connection = GoogleConnection(
                connection_id=new_google_connection_id(),
                tenant_id=txn.tenant_id,
                authorized_by_user_id=txn.initiating_user_id,
                google_subject=tokens.google_subject,
                display_email=tokens.display_email,
                status=ConnectionStatus.ACTIVE.value,
                granted_scopes=tokens.granted_scopes,
                capabilities=tuple(item.value for item in granted),
                credential_ref=credential_ref,
                created_at=now,
                updated_at=now,
                last_verified_at=now,
                revoked_at=None,
            )
        stored = self._repo.put_google_connection(connection)
        security_log(
            "google.oauth.connected",
            tenant_id=stored.tenant_id,
            connection_id=stored.connection_id,
        )
        return self._redirect(
            {"google": "connected", "connection_id": stored.connection_id},
            txn.return_path,
        )

    def list_connections(self) -> list[GoogleConnection]:
        require_feature(self._repo, Feature.DATA_UPLOAD)
        tenant = require_tenant()
        return self._repo.list_google_connections(tenant_id=tenant.tenant_id)

    def get_connection(self, *, connection_id: str) -> GoogleConnection:
        tenant = require_tenant()
        connection = self._repo.get_google_connection(
            tenant_id=tenant.tenant_id, connection_id=connection_id
        )
        if connection is None:
            raise resource_not_found()
        return connection

    def disconnect(self, *, connection_id: str) -> GoogleConnection:
        require_feature(self._repo, Feature.DATA_UPLOAD)
        tenant = require_tenant()
        connection = self._repo.get_google_connection(
            tenant_id=tenant.tenant_id, connection_id=connection_id
        )
        if connection is None:
            raise resource_not_found()
        refresh = self._vault.get_refresh_token(
            tenant_id=tenant.tenant_id, credential_ref=connection.credential_ref
        )
        if self._oauth is not None and refresh:
            try:
                self._oauth.revoke(token=refresh)
            except Exception:
                security_log(
                    "google.oauth.revoke_failed",
                    tenant_id=tenant.tenant_id,
                    connection_id=connection.connection_id,
                )
        self._vault.delete(tenant_id=tenant.tenant_id, credential_ref=connection.credential_ref)
        now = datetime.now(UTC)
        revoked = connection.model_copy(
            update={
                "status": ConnectionStatus.REVOKED.value,
                "updated_at": now,
                "revoked_at": now,
            }
        )
        stored = self._repo.put_google_connection(revoked)
        self._mark_bindings_unavailable(tenant_id=tenant.tenant_id, connection_id=connection_id)
        self._invalidate_import_ready(tenant_id=tenant.tenant_id, connection_id=connection_id)
        security_log(
            "google.oauth.disconnected",
            tenant_id=tenant.tenant_id,
            connection_id=connection_id,
        )
        return stored

    def user_access_token(self, *, connection: GoogleConnection) -> str:
        if self._oauth is None:
            raise _oauth_not_configured()
        if connection.status != ConnectionStatus.ACTIVE.value:
            raise validation_error(
                [
                    ProblemFieldError(
                        field="connection_id",
                        message="Google connection is not active.",
                    )
                ]
            )
        refresh = self._vault.get_refresh_token(
            tenant_id=connection.tenant_id, credential_ref=connection.credential_ref
        )
        if not refresh:
            raise validation_error(
                [
                    ProblemFieldError(
                        field="connection_id",
                        message="Google credential is missing.",
                    )
                ]
            )
        return self._oauth.refresh_access_token(refresh_token=refresh)

    def _connection_for_subject(
        self, *, tenant_id: str, google_subject: str
    ) -> GoogleConnection | None:
        for item in self._repo.list_google_connections(tenant_id=tenant_id):
            if item.google_subject == google_subject:
                return item
        return None

    def _mark_bindings_unavailable(self, *, tenant_id: str, connection_id: str) -> None:
        now = datetime.now(UTC)
        for workspace in self._repo.list_workspaces_for_tenant(tenant_id):
            drive = self._repo.get_drive_binding(
                tenant_id=tenant_id, workspace_id=workspace.workspace_id
            )
            if drive is not None and drive.connection_id == connection_id:
                self._repo.put_drive_binding(
                    drive.model_copy(
                        update={
                            "status": BindingStatus.UNAVAILABLE.value,
                            "import_enabled": False,
                            "export_enabled": False,
                            "updated_at": now,
                        }
                    )
                )
            bq = self._repo.get_bigquery_binding(
                tenant_id=tenant_id, workspace_id=workspace.workspace_id
            )
            if bq is not None and bq.connection_id == connection_id:
                self._repo.put_bigquery_binding(
                    bq.model_copy(
                        update={
                            "status": BindingStatus.UNAVAILABLE.value,
                            "read_verified": False,
                            "write_verified": False,
                            "updated_at": now,
                        }
                    )
                )

    def _invalidate_import_ready(self, *, tenant_id: str, connection_id: str) -> None:
        now = datetime.now(UTC)
        for workspace in self._repo.list_workspaces_for_tenant(tenant_id):
            for dataset in self._repo.list_datasets_for_workspace(
                tenant_id=tenant_id, workspace_id=workspace.workspace_id
            ):
                selection = self._repo.get_import_selection(
                    tenant_id=tenant_id,
                    workspace_id=workspace.workspace_id,
                    dataset_id=dataset.dataset_id,
                )
                if selection is None or selection.connection_id != connection_id:
                    continue
                current = self._repo.get_current_import_receipt(
                    tenant_id=tenant_id,
                    workspace_id=workspace.workspace_id,
                    dataset_id=dataset.dataset_id,
                )
                if current is None or current.status is not ImportReadinessStatus.IMPORT_READY:
                    continue
                invalidated = ImportReadinessReceipt(
                    receipt_id=new_receipt_id(),
                    contract_version=current.contract_version,
                    tenant_id=current.tenant_id,
                    workspace_id=current.workspace_id,
                    dataset_id=current.dataset_id,
                    source_type=current.source_type,
                    status=ImportReadinessStatus.NOT_IMPORT_READY,
                    check_results=[
                        GovernanceCheckResult(
                            code=GovernanceCheckCode.CONNECTION_INACTIVE,
                            severity=CheckSeverity.ERROR,
                            passed=False,
                            message="CONNECTION_INACTIVE: Google connection was disconnected.",
                            evidence={"connection_id": connection_id},
                        )
                    ],
                    error_count=1,
                    attention_count=0,
                    manifest_fingerprint=current.manifest_fingerprint,
                    verified_at=now,
                    superseded=False,
                )
                self._repo.put_import_receipt(invalidated)

    def _redirect(self, params: dict[str, str], return_path: str | None = None) -> str:
        path = return_path or "/app/settings"
        return f"{self._frontend_origin}{path}?{urlencode(params)}"


def _parse_requested_capabilities(values: list[str]) -> list[GoogleCapability]:
    if not values:
        raise validation_error(
            [
                ProblemFieldError(
                    field="capabilities",
                    message="At least one capability is required.",
                )
            ]
        )
    try:
        return parse_capabilities(values)
    except ValueError as exc:
        raise validation_error(
            [
                ProblemFieldError(
                    field="capabilities",
                    message="Unsupported Google capability.",
                )
            ]
        ) from exc


def _oauth_not_configured() -> APIError:
    return APIError(
        code="GOOGLE_OAUTH_NOT_CONFIGURED",
        status=503,
        title="Google OAuth not configured",
        detail="Google OAuth is not configured for this runtime.",
    )
