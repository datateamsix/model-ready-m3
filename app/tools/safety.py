"""Deterministic safety checks for transforms. Prompts are not sufficient."""

from __future__ import annotations

from app.core.errors import ApprovalRequiredError, RegistryTrustError, SafetyViolationError
from app.registry.loader import lookup_provider, require_executable
from app.registry.schema import TrustLevel

DATE_FORMAT_ALIASES = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "MM/DD/YYYY": "%m/%d/%Y",
    "%Y-%m-%d": "%Y-%m-%d",
    "%m/%d/%Y": "%m/%d/%Y",
}

BUILTIN_NON_SUMMABLE = frozenset(
    {
        "ctr",
        "cpc",
        "cpm",
        "roas",
        "aov",
        "average_order_value",
        "engagement_rate",
        "conversion_rate",
        "rpm",
        "frequency",
    }
)

_KNOWN_SEMANTICS = {
    "time",
    "geo",
    "kpi",
    "revenue",
    "revenue_per_kpi",
    "population",
    "media",
    "media_spend",
    "organic_media",
    "control",
    "campaign",
    "media_channel",
    "rate",
    "clicks",
    "sessions",
    "users",
    "kpi_candidate",
}

_SEMANTIC_ALIASES: dict[str, frozenset[str]] = {
    "media_spend": frozenset({"media_spend", "spend", "cost", "amount_spent"}),
    "media": frozenset({"media", "impressions"}),
    "kpi": frozenset({"kpi", "orders", "kpi_orders"}),
    "revenue": frozenset({"revenue", "net_revenue", "kpi_revenue"}),
    "organic_media": frozenset({"organic_media", "organic_sessions"}),
    "time": frozenset({"time", "date", "week_start", "week_start_date"}),
    "geo": frozenset({"geo"}),
    "rate": frozenset({"rate", "ctr", "cpc", "cpm", "roas", "average_order_value"}),
}


def resolve_date_format(expected_format: str) -> str:
    fmt = DATE_FORMAT_ALIASES.get(expected_format)
    if fmt is None:
        raise SafetyViolationError(
            f"Unsupported date format '{expected_format}'. "
            "Provide an explicit source format such as YYYY-MM-DD or MM/DD/YYYY."
        )
    return fmt


def non_summable_names(provider_id: str | None = None) -> set[str]:
    names = {item.lower() for item in BUILTIN_NON_SUMMABLE}
    if not provider_id:
        return names
    entry = lookup_provider(provider_id)
    if entry is None:
        return names
    names.update(hint.lower() for hint in entry.non_summable_rate_hints)
    for field in entry.fields:
        if field.summable is False and field.semantic_concept in {"rate"}:
            names.add(field.source_name.lower())
    return names


def detect_non_summable_metrics(
    columns: list[str],
    provider_id: str | None = None,
) -> dict[str, list[str]]:
    blocked = non_summable_names(provider_id)
    flagged = [column for column in columns if column.lower() in blocked]
    return {
        "provider_id": provider_id,
        "columns": columns,
        "non_summable": flagged,
    }


def assert_summable_columns(columns: list[str], provider_id: str | None = None) -> None:
    flagged = detect_non_summable_metrics(columns, provider_id)["non_summable"]
    if flagged:
        raise SafetyViolationError(f"Non-summable metrics cannot be aggregated (MR-006): {flagged}")
    if provider_id:
        entry = lookup_provider(provider_id)
        if entry is not None:
            field_map = {field.source_name: field for field in entry.fields}
            for column in columns:
                field = field_map.get(column)
                if field is not None and field.summable is False:
                    raise SafetyViolationError(
                        f"Registry marks {column} as not summable for {entry.provider_id}."
                    )


def validate_provider_mapping(provider_id: str, mapping: dict[str, str]) -> None:
    entry = require_executable(provider_id)
    if entry.trust is not TrustLevel.EXECUTABLE:
        raise RegistryTrustError(f"Provider {provider_id} is not executable.")
    fields = {field.source_name: field for field in entry.fields}
    for source, target in mapping.items():
        if source not in fields:
            raise ApprovalRequiredError(
                f"Source field '{source}' is not on the executable {entry.provider_id} card."
            )
        concept = fields[source].semantic_concept
        target_semantic = _semantic_for_name(target)
        if target_semantic is None and target not in fields and target != source:
            if target in _KNOWN_SEMANTICS or _semantic_for_name(target):
                target_semantic = target
            else:
                raise ApprovalRequiredError(
                    f"Mapping {source}->{target} is not a trusted semantic for {entry.provider_id}."
                )
        if target_semantic and target_semantic != concept:
            if not (
                target == source
                or target == concept
                or target in _SEMANTIC_ALIASES.get(concept, frozenset())
            ):
                raise ApprovalRequiredError(
                    f"Mapping {source}->{target} contradicts registry concept '{concept}'."
                )


def _semantic_for_name(name: str) -> str | None:
    lowered = name.lower()
    if lowered in _KNOWN_SEMANTICS:
        return lowered
    for semantic, aliases in _SEMANTIC_ALIASES.items():
        if lowered in aliases:
            return semantic
    return None
