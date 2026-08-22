"""Conservative system-issued identifier rules for Mission 2 storage paths."""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath

from app.core.errors import InvalidResourceIdentifierError

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SCHEME_PREFIX = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def validate_resource_identifier(value: str, *, field: str) -> str:
    """Reject unsafe identifiers. Do not sanitize them into a valid ID."""
    if not isinstance(value, str):
        raise InvalidResourceIdentifierError(f"{field} must be a string.")
    if value == "" or value.strip() == "":
        raise InvalidResourceIdentifierError(f"{field} must not be empty.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise InvalidResourceIdentifierError(f"{field} must not contain control characters.")
    if any(char.isspace() for char in value):
        raise InvalidResourceIdentifierError(f"{field} must not contain whitespace.")
    if value in {".", ".."}:
        raise InvalidResourceIdentifierError(f"{field} must not be a dot segment.")
    if "/" in value:
        raise InvalidResourceIdentifierError(f"{field} must not contain '/'.")
    if "\\" in value:
        raise InvalidResourceIdentifierError(f"{field} must not contain '\\'.")
    if "://" in value or _SCHEME_PREFIX.match(value) is not None:
        raise InvalidResourceIdentifierError(f"{field} must not be URI-shaped.")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or value.startswith("\\\\"):
        raise InvalidResourceIdentifierError(f"{field} must not be an absolute path.")
    if _SAFE_IDENTIFIER.fullmatch(value) is None:
        raise InvalidResourceIdentifierError(
            f"{field} must be a system-issued identifier, not a customer display name."
        )
    return value
