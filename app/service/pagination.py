"""Opaque, tenant-free list pagination."""

from __future__ import annotations

import base64
import re
from collections.abc import Callable, Sequence

_CURSOR_SAFE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    if limit < 1:
        return 1
    return min(limit, MAX_LIMIT)


def encode_cursor(resource_id: str) -> str:
    return base64.urlsafe_b64encode(resource_id.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str | None) -> str | None:
    if cursor is None or cursor == "":
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeError):
        return None
    if _CURSOR_SAFE.fullmatch(raw) is None:
        return None
    return raw


def paginate_by_id[T](
    items: Sequence[T],
    *,
    cursor: str | None,
    limit: int | None,
    id_of: Callable[[T], str],
) -> tuple[list[T], str | None]:
    bounded = clamp_limit(limit)
    after = decode_cursor(cursor)
    selected: list[T] = []
    started = after is None
    for item in items:
        item_id = id_of(item)
        if not started:
            if item_id == after:
                started = True
            continue
        selected.append(item)
        if len(selected) == bounded + 1:
            break
    next_cursor = None
    if len(selected) > bounded:
        page = list(selected[:bounded])
        next_cursor = encode_cursor(id_of(page[-1]))
        return page, next_cursor
    return list(selected), None
