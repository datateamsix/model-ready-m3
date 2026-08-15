import pytest

from app.core.errors import RegistryTrustError
from app.registry.loader import load_registry, lookup_provider, require_executable, search_providers
from app.registry.schema import TrustLevel


def test_registry_contains_fifty_providers() -> None:
    catalog = load_registry()
    assert catalog.version == "1.0.0"
    assert len(catalog.providers) == 50
    assert sum(entry.trust is TrustLevel.EXECUTABLE for entry in catalog.providers) == 4


def test_lookup_executable_google_ads_from_filename() -> None:
    entry = lookup_provider("google_ads_daily.csv")
    assert entry is not None
    assert entry.provider_id == "google_ads"
    assert entry.trust is TrustLevel.EXECUTABLE
    assert any(field.source_name == "cost" for field in entry.fields)


def test_directory_provider_cannot_be_executed() -> None:
    with pytest.raises(RegistryTrustError):
        require_executable("tiktok_ads")


def test_search_returns_compact_summaries() -> None:
    matches = search_providers("meta")
    assert matches
    assert "fields" not in matches[0]
    assert matches[0]["provider_id"] == "meta_ads"
