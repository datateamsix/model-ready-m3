"""Clerk provider runtime. Official SDK: clerk-backend-api 6.0.1."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from clerk_backend_api import Clerk
from clerk_backend_api.security import authenticate_request
from clerk_backend_api.security.types import (
    AuthenticateRequestOptions,
    AuthErrorReason,
    TokenVerificationErrorReason,
)
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.service.auth import VerifiedIdentity
from app.service.clerk_webhooks import verify_standard_webhook
from app.service.errors import (
    APIError,
    auth_provider_not_configured,
    auth_provider_unavailable,
    auth_required,
    organization_context_required,
)

_CLERK_PROVIDER = "clerk"


class CurrentMembership(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    active: bool
    role: str | None = None


class ClerkOrganization(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: str
    name: str


class MembershipAuthority(Protocol):
    def verify_current_membership(self, identity: VerifiedIdentity) -> CurrentMembership: ...


class WebhookVerifier(Protocol):
    def verify_webhook(self, *, body: bytes, headers: Mapping[str, str]) -> dict[str, Any]: ...


class OrganizationDirectory(Protocol):
    def get_organization(self, organization_id: str) -> ClerkOrganization | None: ...


class ClerkRuntime(Protocol):
    def verify(self, authorization: str | None) -> VerifiedIdentity: ...

    def verify_current_membership(self, identity: VerifiedIdentity) -> CurrentMembership: ...

    def get_organization(self, organization_id: str) -> ClerkOrganization | None: ...

    def verify_webhook(self, *, body: bytes, headers: Mapping[str, str]) -> dict[str, Any]: ...


class _AuthorizationRequest:
    def __init__(self, authorization: str) -> None:
        self.headers = {"Authorization": authorization}


class RealClerkRuntime:
    """Production Clerk adapter. Constructed only when a secret key is configured."""

    def __init__(self, settings: Settings) -> None:
        if not settings.clerk_secret_key:
            raise auth_provider_not_configured()
        self._secret_key = settings.clerk_secret_key
        self._jwt_key = settings.clerk_jwt_key
        self._authorized_parties = list(settings.clerk_authorized_parties) or None
        self._webhook_secret = settings.clerk_webhook_signing_secret
        timeout_ms = max(1, settings.clerk_api_timeout_seconds) * 1000
        self._client = Clerk(bearer_auth=self._secret_key, timeout_ms=timeout_ms)

    def verify(self, authorization: str | None) -> VerifiedIdentity:
        if authorization is None or not authorization.strip():
            raise auth_required()
        state = authenticate_request(
            _AuthorizationRequest(authorization),
            AuthenticateRequestOptions(
                secret_key=self._secret_key,
                jwt_key=self._jwt_key,
                authorized_parties=self._authorized_parties,
                accepts_token=["session_token"],
            ),
        )
        if not state.is_signed_in or state.payload is None:
            raise _map_clerk_failure(state.reason)
        payload = state.payload
        user_id = str(payload.get("sub") or "").strip()
        org_id = str(payload.get("org_id") or "").strip()
        if not user_id:
            raise auth_required()
        if not org_id:
            raise organization_context_required()
        session_id = str(payload.get("sid") or "").strip() or None
        return VerifiedIdentity(
            provider=_CLERK_PROVIDER,
            provider_user_id=user_id,
            provider_organization_id=org_id,
            session_id=session_id,
        )

    def verify_current_membership(self, identity: VerifiedIdentity) -> CurrentMembership:
        try:
            result = self._client.organization_memberships.list(
                organization_id=identity.provider_organization_id,
                user_id=[identity.provider_user_id],
                limit=1,
            )
        except APIError:
            raise
        except Exception as exc:
            raise auth_provider_unavailable() from exc
        rows = getattr(result, "data", None) or []
        if not rows:
            return CurrentMembership(active=False)
        role = getattr(rows[0], "role", None)
        return CurrentMembership(active=True, role=str(role) if role else None)

    def get_organization(self, organization_id: str) -> ClerkOrganization | None:
        try:
            org = self._client.organizations.get(organization_id=organization_id)
        except APIError:
            raise
        except Exception:
            return None
        org_id = str(getattr(org, "id", "") or "").strip()
        if not org_id:
            return None
        name = str(getattr(org, "name", "") or "Organization")
        return ClerkOrganization(organization_id=org_id, name=name)

    def verify_webhook(self, *, body: bytes, headers: Mapping[str, str]) -> dict[str, Any]:
        if not self._webhook_secret:
            raise auth_provider_not_configured()
        return verify_standard_webhook(self._webhook_secret, body, headers)


class FakeClerkRuntime:
    """Test-only Clerk runtime. Injected through the application factory."""

    def __init__(self, *, webhook_secret: str = "whsec_dGVzdF9jbGVya19zaWduaW5nX3NlY3JldA") -> None:
        self.identities: dict[str, VerifiedIdentity] = {}
        self.expired_tokens: set[str] = set()
        self.wrong_azp_tokens: set[str] = set()
        self.machine_tokens: set[str] = set()
        self.no_org_tokens: set[str] = set()
        self.memberships: dict[tuple[str, str], str | None] = {}
        self.membership_unavailable = False
        self.organizations: dict[str, ClerkOrganization] = {}
        self.webhook_secret = webhook_secret
        self.authorized_parties: tuple[str, ...] = ()

    def verify(self, authorization: str | None) -> VerifiedIdentity:
        if authorization is None or not authorization.strip():
            raise auth_required()
        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            raise auth_required()
        if token in self.machine_tokens:
            raise auth_required()
        if token in self.expired_tokens:
            raise auth_required()
        if token in self.wrong_azp_tokens:
            raise auth_required()
        if token in self.no_org_tokens:
            raise organization_context_required()
        identity = self.identities.get(token)
        if identity is None:
            raise auth_required()
        return identity

    def verify_current_membership(self, identity: VerifiedIdentity) -> CurrentMembership:
        if self.membership_unavailable:
            raise auth_provider_unavailable()
        key = (identity.provider_user_id, identity.provider_organization_id)
        if key not in self.memberships:
            return CurrentMembership(active=False)
        return CurrentMembership(active=True, role=self.memberships[key])

    def get_organization(self, organization_id: str) -> ClerkOrganization | None:
        return self.organizations.get(organization_id)

    def verify_webhook(self, *, body: bytes, headers: Mapping[str, str]) -> dict[str, Any]:
        return verify_standard_webhook(self.webhook_secret, body, headers)

    def grant(
        self,
        token: str,
        *,
        user_id: str,
        organization_id: str,
        role: str = "org:member",
        session_id: str | None = "sess_test",
    ) -> VerifiedIdentity:
        identity = VerifiedIdentity(
            provider=_CLERK_PROVIDER,
            provider_user_id=user_id,
            provider_organization_id=organization_id,
            session_id=session_id,
        )
        self.identities[token] = identity
        self.memberships[(user_id, organization_id)] = role
        return identity


def _map_clerk_failure(reason: object) -> APIError:
    if reason is None:
        return auth_required()
    if isinstance(reason, AuthErrorReason):
        return _map_auth_error(reason)
    if isinstance(reason, TokenVerificationErrorReason):
        return _map_token_error(reason)
    return auth_required()


def _map_auth_error(reason: AuthErrorReason) -> APIError:
    match reason:
        case AuthErrorReason.SESSION_TOKEN_MISSING:
            return auth_required()
        case AuthErrorReason.SECRET_KEY_MISSING:
            return auth_provider_not_configured()
        case AuthErrorReason.TOKEN_TYPE_NOT_SUPPORTED:
            return auth_required()
        case _:
            _assert_never(reason)


def _map_token_error(reason: TokenVerificationErrorReason) -> APIError:
    match reason:
        case TokenVerificationErrorReason.JWK_FAILED_TO_LOAD:
            return auth_provider_unavailable()
        case TokenVerificationErrorReason.JWK_REMOTE_INVALID:
            return auth_provider_unavailable()
        case TokenVerificationErrorReason.JWK_FAILED_TO_RESOLVE:
            return auth_provider_unavailable()
        case TokenVerificationErrorReason.SERVER_ERROR:
            return auth_provider_unavailable()
        case TokenVerificationErrorReason.SECRET_KEY_MISSING:
            return auth_provider_not_configured()
        case TokenVerificationErrorReason.JWK_KID_MISMATCH:
            return auth_required()
        case TokenVerificationErrorReason.TOKEN_EXPIRED:
            return auth_required()
        case TokenVerificationErrorReason.TOKEN_INVALID:
            return auth_required()
        case TokenVerificationErrorReason.TOKEN_INVALID_AUTHORIZED_PARTIES:
            return auth_required()
        case TokenVerificationErrorReason.TOKEN_INVALID_AUDIENCE:
            return auth_required()
        case TokenVerificationErrorReason.TOKEN_IAT_IN_THE_FUTURE:
            return auth_required()
        case TokenVerificationErrorReason.TOKEN_NOT_ACTIVE_YET:
            return auth_required()
        case TokenVerificationErrorReason.TOKEN_INVALID_SIGNATURE:
            return auth_required()
        case TokenVerificationErrorReason.INVALID_TOKEN_TYPE:
            return auth_required()
        case _:
            _assert_never(reason)


def _assert_never(value: object) -> APIError:
    raise auth_required()
