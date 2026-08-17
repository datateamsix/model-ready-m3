"""Manifest-driven source inventory. Filenames are transport metadata only."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.errors import AssignmentInitError
from app.core.model_intent import ModelIntent
from app.registry.loader import lookup_provider
from app.tools.artifacts import sha256_file
from app.tools.io import read_table
from app.tools.provenance import dataset_fingerprint

TIME_FIELD_CANDIDATES = (
    "time",
    "week_start",
    "week_start_date",
    "week_ending",
    "date",
    "timeperiod",
)
GEO_FIELD_CANDIDATES = ("geo",)
INACTIVITY_NAME_MARKERS = ("documented_inactive", "inactive_period")
INTENT_FILENAME = "model_intent.json"
EXPECTED_CONTRACT_FILENAMES = frozenset(
    {
        "expected_issues.json",
        "expected_safe_actions.json",
        "expected_forbidden_actions.json",
        "expected_semantic_triggers.json",
        "expected_model_ready_weekly.csv",
        "expected_model_input.json",
        "expected_authority.json",
        "expected_run_intelligence.json",
        "expected_learning_observations.json",
        "business_truth.json",
    }
)


class CanonicalRole(StrEnum):
    PAID_MEDIA = "paid_media"
    KPI = "kpi"
    REVENUE = "revenue"
    ORGANIC_MEDIA = "organic_media"
    CONTROLS = "controls"
    POPULATION = "population"
    INACTIVITY_EVIDENCE = "inactivity_evidence"
    MODEL_INTENT = "model_intent"
    UNKNOWN = "unknown"


class InitFailureReason(StrEnum):
    MISSING_REQUIRED_SOURCE = "MISSING_REQUIRED_SOURCE"
    UNSUPPORTED_PROVIDER = "UNSUPPORTED_PROVIDER"
    UNSUPPORTED_REPORT_TYPE = "UNSUPPORTED_REPORT_TYPE"
    UNSUPPORTED_GRAIN = "UNSUPPORTED_GRAIN"
    INVALID_SOURCE_SCHEMA = "INVALID_SOURCE_SCHEMA"
    AMBIGUOUS_SOURCE_ROLE = "AMBIGUOUS_SOURCE_ROLE"
    MANIFEST_CONTRACT_ERROR = "MANIFEST_CONTRACT_ERROR"
    UNKNOWN_ABSENCE = "UNKNOWN_ABSENCE"
    USER_CONTEXT_REQUIRED = "USER_CONTEXT_REQUIRED"


class SourceDescriptor(BaseModel):
    source_id: str
    provider_id: str | None = None
    report_type: str | None = None
    relative_path: str
    grain: str | None = None
    date_field: str | None = None
    geo_field: str | None = None
    canonical_role: CanonicalRole
    required: bool = False
    supported: bool = True
    mapping_status: str = "identified"
    channel_hint: str | None = None
    rows: int = 0
    columns: list[str] = Field(default_factory=list)
    sha256: str = ""


class SourceInventory(BaseModel):
    assignment_id: str = ""
    dataset_id: str = ""
    dataset_role: str | None = None
    business_name: str | None = None
    source_count: int = 0
    sources: list[SourceDescriptor] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    required_providers: list[str] = Field(default_factory=list)
    optional_sources: list[str] = Field(default_factory=list)
    unsupported_sources: list[str] = Field(default_factory=list)
    missing_required_sources: list[str] = Field(default_factory=list)
    canonical_roles_expected: list[str] = Field(default_factory=list)
    manifest_fingerprint: str = ""

    def descriptor_for(self, relative_path: str) -> SourceDescriptor | None:
        for item in self.sources:
            if item.relative_path == relative_path:
                return item
        return None

    def sources_for_role(self, role: CanonicalRole) -> list[SourceDescriptor]:
        return [item for item in self.sources if item.canonical_role is role]

    def sources_for_provider(self, provider_id: str) -> list[SourceDescriptor]:
        return [item for item in self.sources if item.provider_id == provider_id]


def required_provider_ids(intent: ModelIntent) -> list[str]:
    providers: list[str] = [intent.kpi.provider, intent.revenue.provider]
    if intent.population is not None:
        providers.append(intent.population.provider)
    providers.extend(channel.provider for channel in intent.paid_media)
    providers.extend(item.provider for item in intent.organic_media)
    ordered: list[str] = []
    seen: set[str] = set()
    for provider in providers:
        if provider in seen:
            continue
        seen.add(provider)
        ordered.append(provider)
    return ordered


def detect_time_field(columns: list[str], provider_id: str | None = None) -> str | None:
    lowered = {column.lower(): column for column in columns}
    if provider_id:
        entry = lookup_provider(provider_id)
        if entry is not None:
            for field in entry.resolved_date_fields():
                if field.lower() in lowered:
                    return lowered[field.lower()]
    for candidate in TIME_FIELD_CANDIDATES:
        if candidate in lowered:
            return lowered[candidate]
    return None


def detect_geo_field(columns: list[str]) -> str | None:
    lowered = {column.lower(): column for column in columns}
    for candidate in GEO_FIELD_CANDIDATES:
        if candidate in lowered:
            return lowered[candidate]
    return None


def inventory_assignment_sources(
    raw_dir: str | Path,
    intent: ModelIntent,
    *,
    dataset_id: str = "",
    dataset_role: str | None = None,
    assignment_id: str = "",
    business_name: str | None = None,
) -> SourceInventory:
    """Build typed source descriptors from model intent + package files.

    Does not read expected-answer artifacts. Those exist only for tests.
    """
    root = Path(raw_dir)
    hashes: dict[str, str] = {}
    descriptors: list[SourceDescriptor] = []
    required = required_provider_ids(intent)
    claimed_providers: set[str] = set()

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        name = path.name
        if name in EXPECTED_CONTRACT_FILENAMES or "truth/" in relative.lower():
            continue
        hashes[relative] = sha256_file(path)
        if name == INTENT_FILENAME:
            descriptors.append(
                SourceDescriptor(
                    source_id="model_intent",
                    provider_id=None,
                    relative_path=relative,
                    canonical_role=CanonicalRole.MODEL_INTENT,
                    required=True,
                    mapping_status="identified",
                    sha256=hashes[relative],
                )
            )
            continue
        if path.suffix.lower() not in {".csv", ".parquet"}:
            continue
        frame = read_table(path)
        columns = [str(column) for column in frame.columns]
        descriptor = _classify_source(
            relative=relative,
            columns=columns,
            row_count=int(len(frame)),
            digest=hashes[relative],
            intent=intent,
        )
        descriptors.append(descriptor)
        if descriptor.provider_id:
            claimed_providers.add(descriptor.provider_id)

    missing = [provider for provider in required if provider not in claimed_providers]
    optional = [
        item.relative_path
        for item in descriptors
        if item.canonical_role is CanonicalRole.INACTIVITY_EVIDENCE
    ]
    unsupported = [
        item.relative_path
        for item in descriptors
        if not item.supported and item.canonical_role is not CanonicalRole.MODEL_INTENT
    ]
    providers = sorted(
        {
            item.provider_id
            for item in descriptors
            if item.provider_id and item.canonical_role is not CanonicalRole.MODEL_INTENT
        }
    )
    roles = sorted({item.canonical_role.value for item in descriptors})
    inventory = SourceInventory(
        assignment_id=assignment_id,
        dataset_id=dataset_id,
        dataset_role=dataset_role,
        business_name=business_name,
        source_count=len(descriptors),
        sources=descriptors,
        providers=providers,
        required_providers=required,
        optional_sources=optional,
        unsupported_sources=unsupported,
        missing_required_sources=missing,
        canonical_roles_expected=roles,
        manifest_fingerprint=dataset_fingerprint(hashes),
    )
    return inventory


def assert_required_sources_present(inventory: SourceInventory) -> None:
    if inventory.missing_required_sources:
        raise AssignmentInitError(
            "Assignment is missing required sources for providers: "
            + ", ".join(inventory.missing_required_sources),
            reason=InitFailureReason.MISSING_REQUIRED_SOURCE.value,
            source=",".join(inventory.missing_required_sources),
            recoverability="USER_REQUIRED",
            owner="user",
        )
    for item in inventory.sources:
        if item.canonical_role is not CanonicalRole.PAID_MEDIA or not item.provider_id:
            continue
        if lookup_provider(item.provider_id) is None:
            raise AssignmentInitError(
                f"Required provider is not in the registry: {item.provider_id}",
                reason=InitFailureReason.UNSUPPORTED_PROVIDER.value,
                source=item.provider_id,
                recoverability="USER_REQUIRED",
                owner="user",
            )
    unsupported_required = [
        item
        for item in inventory.sources
        if item.required and not item.supported
    ]
    if unsupported_required:
        item = unsupported_required[0]
        reason = (
            InitFailureReason.UNSUPPORTED_REPORT_TYPE
            if item.report_type
            else InitFailureReason.AMBIGUOUS_SOURCE_ROLE
        )
        raise AssignmentInitError(
            f"Required source is unsupported: {item.relative_path}",
            reason=reason.value,
            source=item.relative_path,
            recoverability="USER_REQUIRED",
            owner="user",
        )


def source_inventory_receipt(inventory: SourceInventory) -> dict[str, Any]:
    return {
        "receipt_type": "source_inventory_receipt",
        "assignment_id": inventory.assignment_id,
        "dataset_id": inventory.dataset_id,
        "dataset_role": inventory.dataset_role,
        "business_name": inventory.business_name,
        "source_count": inventory.source_count,
        "providers": inventory.providers,
        "required_providers": inventory.required_providers,
        "optional_sources": inventory.optional_sources,
        "unsupported_sources": inventory.unsupported_sources,
        "missing_required_sources": inventory.missing_required_sources,
        "canonical_roles_expected": inventory.canonical_roles_expected,
        "manifest_fingerprint": inventory.manifest_fingerprint,
        "sources": [item.model_dump(mode="json") for item in inventory.sources],
    }


def _classify_source(
    *,
    relative: str,
    columns: list[str],
    row_count: int,
    digest: str,
    intent: ModelIntent,
) -> SourceDescriptor:
    name = Path(relative).name.lower()
    if any(marker in name for marker in INACTIVITY_NAME_MARKERS):
        return SourceDescriptor(
            source_id=_source_id(relative),
            provider_id=None,
            relative_path=relative,
            date_field=detect_time_field(columns),
            geo_field=detect_geo_field(columns),
            canonical_role=CanonicalRole.INACTIVITY_EVIDENCE,
            required=False,
            mapping_status="identified",
            rows=row_count,
            columns=columns,
            sha256=digest,
        )

    column_set = set(columns)
    paid_providers = {channel.provider for channel in intent.paid_media}
    organic_by_field = {item.field: item.provider for item in intent.organic_media}
    registry_entry = lookup_provider(Path(relative).name)
    registry_id = registry_entry.provider_id if registry_entry is not None else None

    role = CanonicalRole.UNKNOWN
    provider_id = registry_id
    required = False
    channel_hint: str | None = None

    if "population" in column_set and "geo" in column_set and intent.kpi.field not in column_set:
        role = CanonicalRole.POPULATION
        provider_id = intent.population.provider if intent.population else registry_id
        required = True
    elif registry_id in paid_providers or _filename_provider_in(name, paid_providers):
        role = CanonicalRole.PAID_MEDIA
        provider_id = (
            registry_id
            if registry_id in paid_providers
            else _filename_provider(name, paid_providers)
        )
        required = True
        channel_hint = _channel_hint_from_filename(name, intent, provider_id)
    elif intent.kpi.field in column_set:
        role = CanonicalRole.KPI
        provider_id = intent.kpi.provider
        required = True
        if intent.revenue.provider == intent.kpi.provider and intent.revenue.field in column_set:
            pass
    elif intent.revenue.field in column_set:
        role = CanonicalRole.REVENUE
        provider_id = intent.revenue.provider
        required = True
    elif any(field in column_set for field in organic_by_field):
        role = CanonicalRole.ORGANIC_MEDIA
        matched = next(field for field in organic_by_field if field in column_set)
        provider_id = organic_by_field[matched]
        required = True
    elif any(control in column_set for control in intent.controls):
        role = CanonicalRole.CONTROLS
        provider_id = registry_id
        required = False
    elif registry_id is not None:
        role = CanonicalRole.UNKNOWN
        provider_id = registry_id

    supported = role is not CanonicalRole.UNKNOWN or not required
    mapping_status = "identified" if role is not CanonicalRole.UNKNOWN else "unknown"
    if role is CanonicalRole.UNKNOWN and provider_id is None:
        mapping_status = "unidentified"
        supported = False

    return SourceDescriptor(
        source_id=_source_id(relative),
        provider_id=provider_id,
        report_type=registry_entry.report_family if registry_entry is not None else None,
        relative_path=relative,
        date_field=detect_time_field(columns, provider_id),
        geo_field=detect_geo_field(columns),
        canonical_role=role,
        required=required,
        supported=supported,
        mapping_status=mapping_status,
        channel_hint=channel_hint,
        rows=row_count,
        columns=columns,
        sha256=digest,
    )


def _source_id(relative: str) -> str:
    return Path(relative).stem


def _filename_provider_in(name: str, providers: set[str]) -> bool:
    return _filename_provider(name, providers) is not None


def _filename_provider(name: str, providers: set[str]) -> str | None:
    normalized = name.replace("-", "_")
    matches = [provider for provider in providers if provider.replace("-", "_") in normalized]
    if len(matches) == 1:
        return matches[0]
    return None


def _channel_hint_from_filename(
    name: str, intent: ModelIntent, provider_id: str | None
) -> str | None:
    if not provider_id:
        return None
    channels = [channel.channel for channel in intent.paid_media if channel.provider == provider_id]
    if len(channels) == 1:
        return channels[0]
    stem = name.replace("-", "_")
    matches = [channel for channel in channels if channel.split("_")[-1] in stem]
    if len(matches) == 1:
        return matches[0]
    return None
