"""Prove Clerk secrets never enter public contracts or frontend config."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.service.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_clerk_secret_key_not_exposed_in_openapi() -> None:
    schema = create_app().openapi()
    blob = str(schema)
    assert "CLERK_SECRET_KEY" not in blob
    assert "sk_test_" not in blob
    assert "sk_live_" not in blob
    assert "whsec_" not in blob
    assert "CLERK_WEBHOOK_SIGNING_SECRET" not in blob


def test_clerk_secret_key_not_in_public_api_responses() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)
    for path in ("/healthz", "/readyz", "/v1/catalog/plans"):
        body = str(client.get(path).json())
        assert "CLERK_SECRET_KEY" not in body
        assert "sk_live_" not in body
        assert "whsec_" not in body


def test_webhook_secret_not_in_openapi() -> None:
    schema = str(create_app().openapi())
    assert "webhook_signing_secret" not in schema
    assert "signingSecret" not in schema


def test_no_clerk_secret_in_frontend_files() -> None:
    frontend = REPO_ROOT / "frontend"
    forbidden = (
        "CLERK_SECRET_KEY",
        "NEXT_PUBLIC_CLERK_SECRET_KEY",
        "CLERK_WEBHOOK_SIGNING_SECRET",
    )
    for path in frontend.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"node_modules", ".next", "dist"} for part in path.parts):
            continue
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx", ".json", ".env", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            assert token not in text, f"{token} found in {path}"


def test_server_config_does_not_use_next_public_clerk_secret() -> None:
    from app.config import Settings

    assert not hasattr(Settings, "NEXT_PUBLIC_CLERK_SECRET_KEY")
    source = (REPO_ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_CLERK_SECRET_KEY" not in source
    assert "NEXT_PUBLIC_" not in source or "NEXT_PUBLIC_CLERK" not in source
