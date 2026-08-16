"""Load and query the versioned marketing/advertising provider registry."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from app.core.errors import RegistryTrustError
from app.registry.schema import (
    ProviderRegistryCatalog,
    ProviderRegistryEntry,
    TrustLevel,
)

REGISTRY_FILENAME = "marketing_advertising_providers.v1.json"
REGISTRY_PATH = Path(__file__).parent / "providers" / REGISTRY_FILENAME


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


@lru_cache(maxsize=1)
def load_registry() -> ProviderRegistryCatalog:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    catalog = ProviderRegistryCatalog.model_validate(payload)
    if len(catalog.providers) != 52:
        raise ValueError(
            f"Provider registry {REGISTRY_FILENAME} must contain 52 entries, "
            f"found {len(catalog.providers)}"
        )
    return catalog


def lookup_provider(query: str) -> ProviderRegistryEntry | None:
    """Return the best matching registry card, or None if nothing matches."""
    needle = _normalize(query)
    if not needle:
        return None

    catalog = load_registry()
    exact: list[ProviderRegistryEntry] = []
    hinted: list[ProviderRegistryEntry] = []
    for entry in catalog.providers:
        if _normalize(entry.provider_id) == needle or _normalize(entry.display_name) == needle:
            exact.append(entry)
            continue
        haystacks = [entry.provider_id, entry.display_name, *entry.filename_hints]
        matched = False
        for item in haystacks:
            if not item:
                continue
            normalized_item = _normalize(item)
            if needle in normalized_item or normalized_item in needle:
                matched = True
                break
        if matched:
            hinted.append(entry)

    if exact:
        return exact[0]
    if len(hinted) == 1:
        return hinted[0]
    if hinted:
        hinted.sort(key=lambda item: len(item.provider_id))
        return hinted[0]
    return None


def search_providers(query: str, limit: int = 8) -> list[dict[str, str]]:
    """Return compact matches for intake. Does not include field maps."""
    needle = _normalize(query)
    catalog = load_registry()
    hits: list[dict[str, str]] = []
    for entry in catalog.providers:
        haystacks = [entry.provider_id, entry.display_name, *entry.filename_hints]
        if needle and not any(needle in _normalize(item) for item in haystacks if item):
            continue
        gaps = ",".join(entry.meridian_gaps) if entry.meridian_gaps else "none"
        hits.append(
            {
                "provider_id": entry.provider_id,
                "display_name": entry.display_name,
                "category": entry.category.value,
                "trust": entry.trust.value,
                "meridian_gaps": gaps,
            }
        )
        if len(hits) >= limit:
            break
    return hits


def require_executable(provider_id: str) -> ProviderRegistryEntry:
    entry = lookup_provider(provider_id)
    if entry is None:
        raise RegistryTrustError(f"Unknown provider: {provider_id}")
    if entry.trust is not TrustLevel.EXECUTABLE:
        raise RegistryTrustError(
            f"Provider {entry.provider_id} is trust={entry.trust.value}; "
            "executable field mapping is blocked until the card is sourced."
        )
    return entry
