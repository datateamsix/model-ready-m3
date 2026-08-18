"""Google credential vault and public-surface token absence tests."""

from __future__ import annotations

import logging

from app.control_plane.models import CredentialEnvelope
from app.service.app import create_app
from tests.unit.api_support import auth_header
from tests.unit.google_support import connect_google, google_harness


def test_refresh_token_not_plaintext_firestore() -> None:
    harness = google_harness()
    connection_id = connect_google(
        harness, capabilities=["GOOGLE_DRIVE"], refresh_token="rt-secret"
    )
    connection = harness["repo"].get_google_connection(
        tenant_id=harness["tenant"].tenant_id, connection_id=connection_id
    )
    assert connection is not None
    envelope = harness["vault"].envelope(
        tenant_id=harness["tenant"].tenant_id, credential_ref=connection.credential_ref
    )
    assert envelope is not None
    persisted = harness["repo"].get_credential_envelope(
        tenant_id=harness["tenant"].tenant_id, credential_ref=connection.credential_ref
    )
    # In-memory vault does not dual-write unless ControlPlaneCredentialVault is used.
    dumped = envelope.model_dump()
    blob = str(dumped)
    assert "rt-secret" not in blob
    assert envelope.ciphertext != "rt-secret"
    assert "refresh_token" not in dumped
    if persisted is not None:
        assert "rt-secret" not in str(persisted.model_dump())


def test_refresh_token_not_public_api() -> None:
    harness = google_harness()
    connect_google(harness, capabilities=["GOOGLE_DRIVE"], refresh_token="rt-secret")
    listed = harness["client"].get(
        "/v1/integrations/google/connections", headers=auth_header()
    )
    assert "rt-secret" not in listed.text
    assert "refresh_token" not in listed.text


def test_access_token_not_public_api() -> None:
    harness = google_harness()
    connect_google(harness, capabilities=["GOOGLE_DRIVE"])
    listed = harness["client"].get(
        "/v1/integrations/google/connections", headers=auth_header()
    )
    assert "ya29.user-access" not in listed.text
    assert "access_token" not in listed.text


def test_google_client_secret_absent_from_openapi() -> None:
    schema = str(create_app().openapi())
    assert "GOOGLE_OAUTH_CLIENT_SECRET" not in schema
    assert "client_secret" not in schema.lower()
    assert "refresh_token" not in schema.lower()
    assert "access_token" not in schema.lower()


def test_tokens_absent_from_logs(caplog) -> None:
    harness = google_harness()
    with caplog.at_level(logging.INFO):
        connect_google(harness, capabilities=["GOOGLE_DRIVE"], refresh_token="rt-secret")
    text = caplog.text
    assert "rt-secret" not in text
    assert "ya29.user-access" not in text


def test_disconnect_removes_encrypted_credential() -> None:
    harness = google_harness()
    connection_id = connect_google(
        harness, capabilities=["GOOGLE_DRIVE"], refresh_token="rt-secret"
    )
    connection = harness["repo"].get_google_connection(
        tenant_id=harness["tenant"].tenant_id, connection_id=connection_id
    )
    assert connection is not None
    response = harness["client"].post(
        f"/v1/integrations/google/connections/{connection_id}/disconnect",
        headers=auth_header(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REVOKED"
    assert harness["vault"].get_refresh_token(
        tenant_id=harness["tenant"].tenant_id, credential_ref=connection.credential_ref
    ) is None
    assert "rt-secret" in harness["oauth"].revoked


def test_credential_envelope_type_has_no_plaintext_field() -> None:
    fields = CredentialEnvelope.model_fields
    assert "refresh_token" not in fields
    assert "access_token" not in fields
    assert "ciphertext" in fields
