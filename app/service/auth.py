"""Identity verifier seam."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.service.errors import auth_provider_not_configured, auth_required


class VerifiedIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    provider_user_id: str
    provider_organization_id: str
    session_id: str | None = None


class IdentityVerifier(Protocol):
    def verify(self, authorization: str | None) -> VerifiedIdentity: ...


class UnconfiguredIdentityVerifier:
    """Production default. Never manufactures a tenant."""

    def verify(self, authorization: str | None) -> VerifiedIdentity:
        raise auth_provider_not_configured()


class FakeIdentityVerifier:
    """Test-only. Injected through the application factory. Not a production flag."""

    def __init__(
        self,
        *,
        default: VerifiedIdentity | None = None,
        identities: dict[str, VerifiedIdentity] | None = None,
    ) -> None:
        self.default = default
        self.identities = identities or {}

    def verify(self, authorization: str | None) -> VerifiedIdentity:
        if authorization is None or not authorization.strip():
            raise auth_required()
        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            raise auth_required()
        if token in self.identities:
            return self.identities[token]
        if self.default is not None:
            return self.default
        raise auth_required()
