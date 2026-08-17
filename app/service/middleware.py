"""Request-ID middleware. Observability only — confers no authority."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

from starlette.types import ASGIApp, Receive, Scope, Send

REQUEST_ID_HEADER = "x-request-id"
_REQUEST_ID_SAFE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

_current_request_id: ContextVar[str] = ContextVar("prem3_request_id", default="")


def current_request_id() -> str:
    return _current_request_id.get() or ""


def _normalize_inbound(value: str | None) -> str:
    if value is None:
        return ""
    text = value.strip()
    if _REQUEST_ID_SAFE.fullmatch(text) is None:
        return ""
    return text


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        raw_headers = scope.get("headers", [])
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1") for key, value in raw_headers
        }
        inbound = _normalize_inbound(headers.get(REQUEST_ID_HEADER))
        request_id = inbound or f"req_{uuid.uuid4().hex[:20]}"
        token = _current_request_id.set(request_id)

        async def send_with_id(message: dict) -> None:
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers", []))
                raw_headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            _current_request_id.reset(token)
