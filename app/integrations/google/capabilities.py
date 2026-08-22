"""Google OAuth capability → scope mapping. Frontend cannot submit raw scopes."""

from __future__ import annotations

from app.governance.codes import (
    CAPABILITY_SCOPES,
    OPENID_SCOPES,
    GoogleCapability,
)


def scopes_for_capabilities(capabilities: list[GoogleCapability]) -> tuple[str, ...]:
    scopes: list[str] = list(OPENID_SCOPES)
    seen = set(scopes)
    for capability in capabilities:
        for scope in CAPABILITY_SCOPES[capability]:
            if scope not in seen:
                seen.add(scope)
                scopes.append(scope)
    return tuple(scopes)


def capabilities_from_scopes(granted: list[str]) -> tuple[GoogleCapability, ...]:
    granted_set = set(granted)
    found: list[GoogleCapability] = []
    for capability, scopes in CAPABILITY_SCOPES.items():
        if set(scopes).issubset(granted_set):
            found.append(capability)
    return tuple(found)


def parse_capabilities(values: list[str]) -> list[GoogleCapability]:
    parsed: list[GoogleCapability] = []
    for item in values:
        parsed.append(GoogleCapability(item))
    return parsed
