"""Clerk identity webhook verification (Standard Webhooks / Svix headers)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from typing import Any

from app.service.errors import auth_required

_SIGNATURE_TOLERANCE_SECONDS = 300


class WebhookSignatureError(Exception):
    """Raised when a Clerk/Svix webhook signature is missing or invalid."""


def sign_standard_webhook(
    secret: str,
    body: bytes,
    *,
    msg_id: str,
    timestamp: str,
) -> str:
    digest = hmac.new(
        _secret_bytes(secret),
        f"{msg_id}.{timestamp}.".encode() + body,
        hashlib.sha256,
    ).digest()
    return "v1," + base64.b64encode(digest).decode("ascii")


def verify_standard_webhook(
    secret: str,
    body: bytes,
    headers: Mapping[str, str],
) -> dict[str, Any]:
    msg_id = _header(headers, "svix-id")
    timestamp = _header(headers, "svix-timestamp")
    signatures = _header(headers, "svix-signature")
    if not msg_id or not timestamp or not signatures:
        raise WebhookSignatureError("Webhook signature headers are required.")
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise WebhookSignatureError("Webhook timestamp is invalid.") from exc
    if abs(time.time() - ts) > _SIGNATURE_TOLERANCE_SECONDS:
        raise WebhookSignatureError("Webhook timestamp is outside tolerance.")
    expected = sign_standard_webhook(secret, body, msg_id=msg_id, timestamp=timestamp)
    expected_sig = expected.split(",", 1)[1]
    if not _signatures_match(signatures, expected_sig):
        raise WebhookSignatureError("Webhook signature is invalid.")
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebhookSignatureError("Verified webhook body is not JSON.") from exc
    if not isinstance(parsed, dict):
        raise WebhookSignatureError("Verified webhook body must be an object.")
    return parsed


def reject_unverified_webhook() -> None:
    raise auth_required()


def _secret_bytes(secret: str) -> bytes:
    raw = secret.removeprefix("whsec_")
    try:
        return base64.b64decode(raw)
    except Exception:
        return secret.encode("utf-8")


def _header(headers: Mapping[str, str], name: str) -> str:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return str(value).strip()
    return ""


def _signatures_match(header_value: str, expected_sig: str) -> bool:
    for part in header_value.split():
        algorithm, _, signature = part.partition(",")
        if algorithm != "v1" or not signature:
            continue
        if hmac.compare_digest(signature, expected_sig):
            return True
    return False
