"""Google OAuth transaction, callback, and connection tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from urllib.parse import parse_qs, urlparse

from app.control_plane.entitlements import PlanId
from app.governance.codes import DRIVE_SCOPE, OPENID_SCOPES, GoogleCapability
from app.integrations.google.adapters import GoogleTokenSet
from tests.unit.api_support import auth_header, make_client, seed_tenant
from tests.unit.google_support import connect_google, google_harness


def test_google_oauth_start_requires_clerk() -> None:
    client, _repo = make_client()
    response = client.post(
        "/v1/integrations/google/oauth/start",
        json={"capabilities": ["GOOGLE_DRIVE"], "return_path": "/app/settings"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_google_oauth_transaction_bound_to_tenant() -> None:
    harness = google_harness()
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={"capabilities": ["GOOGLE_DRIVE"], "return_path": "/app/settings"},
    )
    assert started.status_code == 200, started.text
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    txn = harness["repo"].get_oauth_transaction_by_state_hash(
        sha256(state.encode("utf-8")).hexdigest()
    )
    assert txn is not None
    assert txn.tenant_id == harness["tenant"].tenant_id
    assert txn.workspace_id is None or txn.workspace_id == harness["workspace"]["workspace_id"]


def test_google_oauth_transaction_bound_to_authorized_workspace() -> None:
    harness = google_harness()
    other = seed_tenant(
        harness["repo"],
        provider_org="org_other",
        provider_user="user_other",
        plan_id=PlanId.PROJECT,
    )
    other_tenant, _identity = other
    workspace = harness["repo"].create_workspace_with_capacity(
        tenant_id=other_tenant.tenant_id, name="Foreign"
    )
    response = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={
            "capabilities": ["GOOGLE_DRIVE"],
            "workspace_id": workspace.workspace_id,
            "return_path": "/app/settings",
        },
    )
    assert response.status_code == 404


def test_client_cannot_submit_raw_scopes() -> None:
    harness = google_harness()
    response = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={
            "capabilities": ["GOOGLE_DRIVE"],
            "scopes": ["https://www.googleapis.com/auth/drive"],
            "return_path": "/app/settings",
        },
    )
    assert response.status_code == 422


def test_state_high_entropy() -> None:
    harness = google_harness()
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={"capabilities": ["GOOGLE_DRIVE"], "return_path": "/app/settings"},
    )
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    assert len(state) >= 32


def test_state_single_use() -> None:
    harness = google_harness()
    connection_id = connect_google(harness, capabilities=["GOOGLE_DRIVE"])
    assert connection_id.startswith("gconn_")
    listed = harness["client"].get(
        "/v1/integrations/google/connections", headers=auth_header()
    )
    assert listed.json()["items"][0]["status"] == "ACTIVE"


def test_state_expiry() -> None:
    harness = google_harness()
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={"capabilities": ["GOOGLE_DRIVE"], "return_path": "/app/settings"},
    )
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    txn = harness["repo"].get_oauth_transaction_by_state_hash(
        sha256(state.encode("utf-8")).hexdigest()
    )
    assert txn is not None
    harness["repo"].put_oauth_transaction(
        txn.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)})
    )
    harness["oauth"].seed_code(
        "late-code",
        GoogleTokenSet(
            access_token="ya29.user-access",
            refresh_token="rt-late",
            granted_scopes=(*OPENID_SCOPES, DRIVE_SCOPE),
            google_subject="google-sub-1",
            display_email="user@example.com",
        ),
    )
    callback = harness["client"].get(
        "/v1/integrations/google/oauth/callback",
        params={"state": state, "code": "late-code"},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert "OAUTH_STATE_EXPIRED" in callback.headers["location"]


def test_state_replay_denied() -> None:
    harness = google_harness()
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={"capabilities": ["GOOGLE_DRIVE"], "return_path": "/app/settings"},
    )
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    harness["oauth"].seed_code(
        "replay-code",
        GoogleTokenSet(
            access_token="ya29.user-access",
            refresh_token="rt-replay",
            granted_scopes=(*OPENID_SCOPES, DRIVE_SCOPE),
            google_subject="google-sub-1",
            display_email="user@example.com",
        ),
    )
    first = harness["client"].get(
        "/v1/integrations/google/oauth/callback",
        params={"state": state, "code": "replay-code"},
        follow_redirects=False,
    )
    second = harness["client"].get(
        "/v1/integrations/google/oauth/callback",
        params={"state": state, "code": "replay-code"},
        follow_redirects=False,
    )
    assert first.status_code == 302
    assert "google=connected" in first.headers["location"]
    assert second.status_code == 302
    assert "OAUTH_STATE_REPLAY" in second.headers["location"]


def test_callback_cannot_override_tenant() -> None:
    harness = google_harness()
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={"capabilities": ["GOOGLE_DRIVE"], "return_path": "/app/settings"},
    )
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    harness["oauth"].seed_code(
        "cb-code",
        GoogleTokenSet(
            access_token="ya29.user-access",
            refresh_token="rt-1",
            granted_scopes=(*OPENID_SCOPES, DRIVE_SCOPE),
            google_subject="google-sub-1",
            display_email="user@example.com",
        ),
    )
    callback = harness["client"].get(
        "/v1/integrations/google/oauth/callback",
        params={
            "state": state,
            "code": "cb-code",
            "tenant_id": "ten_attacker0000000000",
        },
        follow_redirects=False,
    )
    assert callback.status_code == 302
    connection_id = parse_qs(urlparse(callback.headers["location"]).query)["connection_id"][0]
    stored = harness["repo"].get_google_connection(
        tenant_id=harness["tenant"].tenant_id, connection_id=connection_id
    )
    assert stored is not None
    assert stored.tenant_id == harness["tenant"].tenant_id


def test_callback_cannot_override_workspace() -> None:
    harness = google_harness()
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={
            "capabilities": ["GOOGLE_DRIVE"],
            "workspace_id": harness["workspace"]["workspace_id"],
            "return_path": "/app/settings",
        },
    )
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    harness["oauth"].seed_code(
        "ws-code",
        GoogleTokenSet(
            access_token="ya29.user-access",
            refresh_token="rt-1",
            granted_scopes=(*OPENID_SCOPES, DRIVE_SCOPE),
            google_subject="google-sub-1",
            display_email="user@example.com",
        ),
    )
    callback = harness["client"].get(
        "/v1/integrations/google/oauth/callback",
        params={"state": state, "code": "ws-code", "workspace_id": "wsp_attacker000000000"},
        follow_redirects=False,
    )
    txn = harness["repo"].get_oauth_transaction_by_state_hash(
        sha256(state.encode("utf-8")).hexdigest()
    )
    assert txn is not None
    assert txn.workspace_id == harness["workspace"]["workspace_id"]
    assert callback.status_code == 302


def test_callback_cannot_override_dataset() -> None:
    harness = google_harness()
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={
            "capabilities": ["GOOGLE_DRIVE"],
            "workspace_id": harness["workspace"]["workspace_id"],
            "dataset_id": harness["dataset"]["dataset_id"],
            "return_path": "/app/settings",
        },
    )
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    harness["oauth"].seed_code(
        "ds-code",
        GoogleTokenSet(
            access_token="ya29.user-access",
            refresh_token="rt-1",
            granted_scopes=(*OPENID_SCOPES, DRIVE_SCOPE),
            google_subject="google-sub-1",
            display_email="user@example.com",
        ),
    )
    callback = harness["client"].get(
        "/v1/integrations/google/oauth/callback",
        params={"state": state, "code": "ds-code", "dataset_id": "dset_attacker00000000"},
        follow_redirects=False,
    )
    txn = harness["repo"].get_oauth_transaction_by_state_hash(
        sha256(state.encode("utf-8")).hexdigest()
    )
    assert txn is not None
    assert txn.dataset_id == harness["dataset"]["dataset_id"]
    assert callback.status_code == 302


def test_partial_grant_does_not_enable_ungranted_capability() -> None:
    harness = google_harness()
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={
            "capabilities": ["GOOGLE_DRIVE", "BIGQUERY_READ"],
            "return_path": "/app/settings",
        },
    )
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    harness["oauth"].seed_code(
        "partial",
        GoogleTokenSet(
            access_token="ya29.user-access",
            refresh_token="rt-1",
            granted_scopes=(*OPENID_SCOPES, DRIVE_SCOPE),
            google_subject="google-sub-1",
            display_email="user@example.com",
        ),
    )
    harness["client"].get(
        "/v1/integrations/google/oauth/callback",
        params={"state": state, "code": "partial"},
        follow_redirects=False,
    )
    listed = harness["client"].get(
        "/v1/integrations/google/connections", headers=auth_header()
    ).json()["items"][0]
    assert GoogleCapability.GOOGLE_DRIVE.value in listed["capabilities"]
    assert GoogleCapability.BIGQUERY_READ.value not in listed["capabilities"]


def test_incremental_auth_preserves_existing_capabilities() -> None:
    harness = google_harness()
    connect_google(harness, capabilities=["GOOGLE_DRIVE"])
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={"capabilities": ["BIGQUERY_READ"], "return_path": "/app/settings"},
    )
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    harness["oauth"].seed_code(
        "inc",
        GoogleTokenSet(
            access_token="ya29.user-access",
            refresh_token=None,
            granted_scopes=(
                *OPENID_SCOPES,
                "https://www.googleapis.com/auth/bigquery.readonly",
            ),
            google_subject="google-sub-1",
            display_email="user@example.com",
        ),
    )
    harness["client"].get(
        "/v1/integrations/google/oauth/callback",
        params={"state": state, "code": "inc"},
        follow_redirects=False,
    )
    listed = harness["client"].get(
        "/v1/integrations/google/connections", headers=auth_header()
    ).json()["items"][0]
    assert "GOOGLE_DRIVE" in listed["capabilities"]
    assert "BIGQUERY_READ" in listed["capabilities"]


def test_missing_refresh_token_preserves_existing_refresh_token() -> None:
    harness = google_harness()
    connection_id = connect_google(harness, capabilities=["GOOGLE_DRIVE"], refresh_token="rt-keep")
    connection = harness["repo"].get_google_connection(
        tenant_id=harness["tenant"].tenant_id, connection_id=connection_id
    )
    assert connection is not None
    before = harness["vault"].get_refresh_token(
        tenant_id=harness["tenant"].tenant_id, credential_ref=connection.credential_ref
    )
    assert before == "rt-keep"
    started = harness["client"].post(
        "/v1/integrations/google/oauth/start",
        headers=auth_header(),
        json={"capabilities": ["BIGQUERY_READ"], "return_path": "/app/settings"},
    )
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]
    harness["oauth"].seed_code(
        "nort",
        GoogleTokenSet(
            access_token="ya29.user-access",
            refresh_token=None,
            granted_scopes=(
                *OPENID_SCOPES,
                "https://www.googleapis.com/auth/bigquery.readonly",
            ),
            google_subject="google-sub-1",
            display_email="user@example.com",
        ),
    )
    harness["client"].get(
        "/v1/integrations/google/oauth/callback",
        params={"state": state, "code": "nort"},
        follow_redirects=False,
    )
    after = harness["vault"].get_refresh_token(
        tenant_id=harness["tenant"].tenant_id, credential_ref=connection.credential_ref
    )
    assert after == "rt-keep"


def test_connection_lookup_tenant_scoped() -> None:
    harness = google_harness()
    connection_id = connect_google(harness, capabilities=["GOOGLE_DRIVE"])
    other_tenant, other_identity = seed_tenant(
        harness["repo"],
        provider_org="org_other",
        provider_user="user_other",
        plan_id=PlanId.PROJECT,
    )
    missing = harness["repo"].get_google_connection(
        tenant_id=other_tenant.tenant_id, connection_id=connection_id
    )
    assert missing is None
    foreign, _ = make_client(repo=harness["repo"], identity=other_identity)
    listed = foreign.get("/v1/integrations/google/connections", headers=auth_header())
    assert listed.status_code == 200
    assert listed.json()["items"] == []
