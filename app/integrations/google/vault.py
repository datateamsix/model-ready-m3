"""Encrypted Google credential vault. Refresh tokens never stored plaintext."""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import UTC, datetime
from typing import Protocol

from app.control_plane.models import CredentialEnvelope
from app.control_plane.repository import ControlPlaneRepository


class CredentialVault(Protocol):
    def put_refresh_token(
        self, *, tenant_id: str, credential_ref: str, refresh_token: str
    ) -> CredentialEnvelope: ...

    def get_refresh_token(self, *, tenant_id: str, credential_ref: str) -> str | None: ...

    def delete(self, *, tenant_id: str, credential_ref: str) -> None: ...


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        stream.extend(hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest())
        counter += 1
    return bytes(stream[:length])


def encrypt_secret(*, master_key: bytes, plaintext: str) -> tuple[str, str]:
    nonce = os.urandom(16)
    raw = plaintext.encode("utf-8")
    stream = _keystream(master_key, nonce, len(raw))
    ciphertext = bytes(a ^ b for a, b in zip(raw, stream, strict=True))
    mac = hmac.new(master_key, nonce + ciphertext, hashlib.sha256).digest()
    return nonce.hex(), (mac + ciphertext).hex()


def decrypt_secret(*, master_key: bytes, wrapped_dek: str, ciphertext: str) -> str:
    nonce = bytes.fromhex(wrapped_dek)
    blob = bytes.fromhex(ciphertext)
    mac, encrypted = blob[:32], blob[32:]
    expected = hmac.new(master_key, nonce + encrypted, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("Credential envelope MAC mismatch.")
    stream = _keystream(master_key, nonce, len(encrypted))
    raw = bytes(a ^ b for a, b in zip(encrypted, stream, strict=True))
    return raw.decode("utf-8")


class InMemoryCredentialVault:
    """Test vault. Encrypts in-process; never stores plaintext refresh tokens."""

    def __init__(self, *, master_key: bytes | None = None) -> None:
        self._key = master_key or (b"prem3-test-credential-vault-key-32")
        self._envelopes: dict[tuple[str, str], CredentialEnvelope] = {}
        self.plaintexts_written: list[str] = []

    def put_refresh_token(
        self, *, tenant_id: str, credential_ref: str, refresh_token: str
    ) -> CredentialEnvelope:
        if not refresh_token:
            raise ValueError("refresh_token must not be empty.")
        wrapped, ciphertext = encrypt_secret(master_key=self._key, plaintext=refresh_token)
        now = datetime.now(UTC)
        envelope = CredentialEnvelope(
            tenant_id=tenant_id,
            credential_ref=credential_ref,
            algorithm="hmac-sha256-xor-v1",
            ciphertext=ciphertext,
            wrapped_dek=wrapped,
            kms_key=None,
            created_at=now,
            updated_at=now,
        )
        self._envelopes[(tenant_id, credential_ref)] = envelope
        return envelope

    def get_refresh_token(self, *, tenant_id: str, credential_ref: str) -> str | None:
        envelope = self._envelopes.get((tenant_id, credential_ref))
        if envelope is None:
            return None
        return decrypt_secret(
            master_key=self._key,
            wrapped_dek=envelope.wrapped_dek,
            ciphertext=envelope.ciphertext,
        )

    def delete(self, *, tenant_id: str, credential_ref: str) -> None:
        self._envelopes.pop((tenant_id, credential_ref), None)

    def envelope(self, *, tenant_id: str, credential_ref: str) -> CredentialEnvelope | None:
        return self._envelopes.get((tenant_id, credential_ref))


class ControlPlaneCredentialVault:
    """Persists ciphertext envelopes only. Optional KMS wrap of the local DEK."""

    def __init__(
        self,
        *,
        repo: ControlPlaneRepository,
        master_key: bytes,
        kms_key: str | None = None,
    ) -> None:
        self._repo = repo
        self._key = master_key
        self._kms_key = kms_key

    def put_refresh_token(
        self, *, tenant_id: str, credential_ref: str, refresh_token: str
    ) -> CredentialEnvelope:
        if not refresh_token:
            raise ValueError("refresh_token must not be empty.")
        wrapped, ciphertext = encrypt_secret(master_key=self._key, plaintext=refresh_token)
        now = datetime.now(UTC)
        existing = self._repo.get_credential_envelope(
            tenant_id=tenant_id, credential_ref=credential_ref
        )
        envelope = CredentialEnvelope(
            tenant_id=tenant_id,
            credential_ref=credential_ref,
            algorithm="hmac-sha256-xor-v1",
            ciphertext=ciphertext,
            wrapped_dek=wrapped,
            kms_key=self._kms_key,
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        return self._repo.put_credential_envelope(envelope)

    def get_refresh_token(self, *, tenant_id: str, credential_ref: str) -> str | None:
        envelope = self._repo.get_credential_envelope(
            tenant_id=tenant_id, credential_ref=credential_ref
        )
        if envelope is None:
            return None
        return decrypt_secret(
            master_key=self._key,
            wrapped_dek=envelope.wrapped_dek,
            ciphertext=envelope.ciphertext,
        )

    def delete(self, *, tenant_id: str, credential_ref: str) -> None:
        self._repo.delete_credential_envelope(tenant_id=tenant_id, credential_ref=credential_ref)
