"""Mission 08 secret leakage and metadata privacy tests."""

from __future__ import annotations

import tomllib
from pathlib import Path

from app.control_plane.memory import InMemoryControlPlaneRepository
from app.service.billing_config import ALLOWED_METADATA_KEYS
from app.service.openapi_export import render_openapi_yaml
from tests.unit.api_support import auth_header, seed_tenant
from tests.unit.stripe_support import make_stripe_client

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_stripe_sdk_is_pinned() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = pyproject["project"]["dependencies"]
    assert "stripe==15.5.0" in deps
    requirements = (REPO_ROOT / "app" / "requirements.txt").read_text(encoding="utf-8")
    assert "stripe==15.5.0" in requirements


def test_secrets_are_absent_from_openapi() -> None:
    payload = render_openapi_yaml().decode("utf-8")
    lowered = payload.lower()
    assert "sk_test" not in lowered
    assert "sk_live" not in lowered
    assert "whsec_" not in lowered
    assert "stripe_secret_key" not in lowered
    assert "stripe_webhook_secret" not in lowered
    assert "stripe_price_id" not in lowered


def test_secrets_are_absent_from_frontend_sources() -> None:
    frontend = REPO_ROOT / "frontend"
    blob = ""
    skip_dirs = {"node_modules", ".next", "dist", "coverage"}
    if frontend.is_dir():
        for path in frontend.rglob("*"):
            if any(part in skip_dirs for part in path.parts):
                continue
            if path.suffix.lower() in {".ts", ".tsx", ".js", ".json", ".env"} and path.is_file():
                blob += path.read_text(encoding="utf-8", errors="ignore").lower()
    assert "sk_live_" not in blob
    assert "sk_test_" not in blob
    assert "stripe_secret_key" not in blob
    assert "stripe_webhook_secret" not in blob
    assert "whsec_" not in blob


def test_checkout_metadata_is_narrow_reconciliation_only() -> None:
    repo = InMemoryControlPlaneRepository()
    tenant, identity = seed_tenant(repo)
    client, stripe, *_ = make_stripe_client(repo, identity)
    client.post(
        "/v1/billing/checkout-session",
        headers=auth_header(),
        json={"plan_id": "project"},
    )
    metadata = stripe.checkout_sessions[-1].metadata
    assert set(metadata) <= ALLOWED_METADATA_KEYS
    assert metadata["prem3_tenant_id"] == tenant.tenant_id
    assert metadata["prem3_plan_id"] == "project"
    joined = " ".join(metadata.values())
    assert "planner" not in joined
    assert "dataset" not in joined
    assert "kpi" not in joined
