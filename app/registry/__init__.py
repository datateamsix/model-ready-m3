"""Provider registry package."""

from app.registry.loader import load_registry, lookup_provider, require_executable, search_providers
from app.registry.schema import (
    FitStatus,
    MeridianFit,
    ProviderCategory,
    ProviderRegistryCatalog,
    ProviderRegistryEntry,
    RegistryField,
    TrustLevel,
)

__all__ = [
    "FitStatus",
    "MeridianFit",
    "ProviderCategory",
    "ProviderRegistryCatalog",
    "ProviderRegistryEntry",
    "RegistryField",
    "TrustLevel",
    "load_registry",
    "lookup_provider",
    "require_executable",
    "search_providers",
]
