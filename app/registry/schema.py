"""Typed provider-registry records."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegistryField(BaseModel):
    source_name: str
    semantic_concept: str
    data_type: str | None = None
    summable: bool | None = None
    notes: str | None = None


class ProviderRegistryEntry(BaseModel):
    provider: str
    report_family: str
    grain: list[str] = Field(default_factory=list)
    date_fields: list[str] = Field(default_factory=list)
    fields: list[RegistryField] = Field(default_factory=list)
    quirks: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
