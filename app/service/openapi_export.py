"""Deterministic OpenAPI export for prem3-api."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from app.service.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPENAPI_PATH = REPO_ROOT / "contracts" / "openapi.yaml"


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    return value


def build_openapi_document() -> dict[str, Any]:
    application = create_app()
    schema = application.openapi()
    schema.pop("servers", None)
    return _canonicalize(schema)


def render_openapi_yaml() -> bytes:
    document = build_openapi_document()
    text = yaml.safe_dump(
        document,
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    if not text.endswith("\n"):
        text += "\n"
    return text.encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_openapi(dest: Path = DEFAULT_OPENAPI_PATH) -> bytes:
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = render_openapi_yaml()
    dest.write_bytes(payload)
    return payload


def check_openapi(dest: Path = DEFAULT_OPENAPI_PATH) -> list[str]:
    generated = render_openapi_yaml()
    if not dest.is_file():
        return [f"missing: {dest}"]
    existing = dest.read_bytes().replace(b"\r\n", b"\n")
    if existing != generated:
        return [f"stale: {dest}"]
    return []
