"""Compile an explicit BigQuery physical schema for model consumption.

Gemini does not choose types, partition fields, clustering, or descriptions.
Unknown fields fail closed instead of silently becoming STRING.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from google.cloud import bigquery
from pydantic import BaseModel, Field

from app.core.errors import ValidationBlockedError
from app.core.model_intent import (
    FLOAT_MODEL_COLUMNS,
    INTEGER_MODEL_COLUMNS,
    MODEL_READY_COLUMNS,
    ModelIntent,
    ModelScope,
)
from app.tools.meridian_contract import MeridianInputContract

_LABEL_SAFE = re.compile(r"[^a-z0-9_-]+")
PARTITION_FIELD = "time"
CLUSTERING_FIELDS = ("geo",)
_BQ_TYPE_ALIASES = {
    "INTEGER": "INT64",
    "INT64": "INT64",
    "FLOAT": "FLOAT64",
    "FLOAT64": "FLOAT64",
    "BOOLEAN": "BOOL",
    "BOOL": "BOOL",
}


class SchemaFieldSpec(BaseModel):
    name: str
    semantic_family: str
    physical_type: str
    mode: str = "REQUIRED"
    description: str

    @property
    def logical_semantic(self) -> str:
        return self.semantic_family


class ModelConsumptionSchema(BaseModel):
    fields: list[SchemaFieldSpec]
    partition_field: str = PARTITION_FIELD
    partition_type: str = "DAY"
    clustering_fields: list[str] = Field(default_factory=lambda: list(CLUSTERING_FIELDS))
    table_description: str = ""

    def field_map(self) -> dict[str, SchemaFieldSpec]:
        return {field.name: field for field in self.fields}

    def physical_schema_fingerprint(self) -> str:
        payload = [
            {
                "name": field.name,
                "physical_type": field.physical_type,
                "mode": field.mode,
                "description": field.description,
            }
            for field in self.fields
        ]
        layout = {
            "fields": payload,
            "partition_field": self.partition_field,
            "partition_type": self.partition_type,
            "clustering_fields": self.clustering_fields,
        }
        encoded = json.dumps(layout, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_bq_schema(self) -> list[bigquery.SchemaField]:
        return [
            bigquery.SchemaField(
                field.name,
                field.physical_type,
                mode=field.mode,
                description=field.description,
            )
            for field in self.fields
        ]

    def to_create_ddl(self, table_ref: str, *, labels: dict[str, str] | None = None) -> str:
        columns = ",\n  ".join(
            f"{field.name} {field.physical_type}"
            f"{' NOT NULL' if field.mode == 'REQUIRED' else ''} "
            f"OPTIONS(description={_sql_string(field.description)})"
            for field in self.fields
        )
        label_sql = _labels_sql(labels or {})
        options = [f"description={_sql_string(self.table_description)}"]
        if label_sql:
            options.append(f"labels=[{label_sql}]")
        cluster_clause = ""
        if self.clustering_fields:
            cluster_clause = f"CLUSTER BY {', '.join(self.clustering_fields)}\n"
        return (
            f"CREATE OR REPLACE TABLE `{table_ref}` (\n  {columns}\n)\n"
            f"PARTITION BY {self.partition_field}\n"
            f"{cluster_clause}"
            f"OPTIONS({', '.join(options)})"
        )


def compile_model_consumption_schema(
    *,
    intent: ModelIntent,
    meridian_contract: MeridianInputContract | None = None,
    columns: list[str] | None = None,
    table_description: str = "",
) -> ModelConsumptionSchema:
    ordered = list(columns or MODEL_READY_COLUMNS)
    fields: list[SchemaFieldSpec] = []
    del meridian_contract
    for name in ordered:
        semantic, physical = classify_model_field(name, intent)
        fields.append(
            SchemaFieldSpec(
                name=name,
                semantic_family=semantic,
                physical_type=physical,
                mode="REQUIRED",
                description=compile_field_description(name, semantic, physical, intent),
            )
        )
    if intent.model_scope is ModelScope.GEO and "geo" not in {field.name for field in fields}:
        raise ValidationBlockedError("Geo models require a geo column in the compiled schema.")
    return ModelConsumptionSchema(
        fields=fields,
        partition_field=PARTITION_FIELD,
        partition_type="DAY",
        clustering_fields=list(CLUSTERING_FIELDS),
        table_description=table_description
        or "ModelReady canonical time x geo model-input artifact for Google Meridian.",
    )


def classify_model_field(name: str, intent: ModelIntent) -> tuple[str, str]:
    """Return (semantic_family, BigQuery physical type). Unknown fields fail closed."""
    if name == "time":
        return "time", "DATE"
    if name == "geo":
        return "geo", "STRING"
    kpi = intent.kpi.canonical_field or ""
    revenue = intent.revenue.canonical_field or ""
    if name == kpi:
        return "kpi", "INT64"
    if name == revenue:
        return "revenue", "FLOAT64"
    if name == "revenue_per_kpi":
        return "revenue_per_kpi", "FLOAT64"
    if name == "population":
        return "population", "INT64"
    for channel in intent.paid_media:
        if name == channel.impressions_column:
            return "media", "INT64"
        if name == channel.spend_column:
            return "media_spend", "FLOAT64"
    organic_names = {
        item.canonical_field or item.field for item in intent.organic_media if item.field
    }
    if name in organic_names:
        return "organic_media", "INT64"
    if name in intent.controls:
        return "controls", "FLOAT64"
    if name in INTEGER_MODEL_COLUMNS:
        return "metric", "INT64"
    if name in FLOAT_MODEL_COLUMNS:
        return "metric", "FLOAT64"
    raise ValidationBlockedError(
        f"Unsupported model-consumption field {name!r}: fail closed (no STRING cast)."
    )


def compile_field_description(
    name: str,
    semantic_family: str,
    physical_type: str,
    intent: ModelIntent,
) -> str:
    """Compile a BigQuery description from the ModelIntent semantic contract.

    Descriptions are not a second per-column dictionary. They are derived from
    semantic family, physical type, channel identity, and declared grain/scope.
    """
    grain = f"{intent.canonical_time_grain.value} {intent.model_scope.value} grain"
    kpi = intent.kpi.canonical_field or "kpi"
    revenue = intent.revenue.canonical_field or "revenue"
    if semantic_family == "time":
        return f"Canonical model week start as BigQuery {physical_type} at {grain}."
    if semantic_family == "geo":
        return f"Modeled geography key at {grain}."
    if semantic_family == "kpi":
        return f"KPI {name} for {intent.target.value} at {grain}."
    if semantic_family == "revenue":
        return f"Revenue {name} associated with KPI {kpi} at {grain}."
    if semantic_family == "revenue_per_kpi":
        return f"Revenue per KPI ({revenue} / {kpi}) at {grain}."
    if semantic_family == "population":
        return f"Population used to scale geo models at {grain}."
    if semantic_family == "media":
        return f"{_display_channel(_channel_label(name, intent))} media impressions at {grain}."
    if semantic_family == "media_spend":
        return f"{_display_channel(_channel_label(name, intent))} media spend in USD at {grain}."
    if semantic_family == "organic_media":
        return f"Organic media exposure {name} at {grain}."
    if semantic_family == "controls":
        return f"Control variable {name} at {grain}."
    raise ValidationBlockedError(
        f"No description compiler for semantic family {semantic_family!r} ({name})."
    )


def schema_as_records(schema: ModelConsumptionSchema) -> list[dict[str, Any]]:
    return [field.model_dump(mode="json") for field in schema.fields]


def inspect_table_schema_records(table: bigquery.Table) -> list[dict[str, str]]:
    return [
        {
            "name": field.name,
            "physical_type": field.field_type,
            "mode": field.mode or "NULLABLE",
            "description": field.description or "",
        }
        for field in table.schema
    ]


def table_layout_metadata(table: bigquery.Table) -> dict[str, Any]:
    partitioning = table.time_partitioning
    clustering = table.clustering_fields or []
    return {
        "partition_field": partitioning.field if partitioning else None,
        "partition_type": str(partitioning.type_) if partitioning and partitioning.type_ else None,
        "clustering_fields": list(clustering),
        "description": table.description or "",
    }


def sanitize_consumption_view_id(organization_id: str, workspace_id: str) -> str:
    raw = f"meridian_input_{organization_id}_{workspace_id}"
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip().lower()).strip("_")
    if not cleaned:
        raise ValidationBlockedError("organization/workspace produced an empty view id.")
    if cleaned[0].isdigit():
        cleaned = f"v_{cleaned}"
    return cleaned[:1024]


def sanitize_label_value(value: str) -> str:
    cleaned = _LABEL_SAFE.sub("-", value.strip().lower()).strip("-")
    return (cleaned or "none")[:63]


def _channel_for_column(name: str, intent: ModelIntent):
    for channel in intent.paid_media:
        if name in {channel.impressions_column, channel.spend_column}:
            return channel
    return None


def _channel_label(name: str, intent: ModelIntent) -> str:
    channel = _channel_for_column(name, intent)
    return channel.channel if channel else name


def _display_channel(channel_id: str) -> str:
    return channel_id.replace("_", " ").title()


def normalize_bq_type(value: str) -> str:
    token = str(value or "").upper()
    return _BQ_TYPE_ALIASES.get(token, token)


def sql_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _sql_string(value: str) -> str:
    return sql_literal(value)


def _labels_sql(labels: dict[str, str]) -> str:
    parts = []
    for key, value in labels.items():
        label_key = _sql_string(sanitize_label_value(key))
        label_value = _sql_string(sanitize_label_value(value))
        parts.append(f"({label_key}, {label_value})")
    return ", ".join(parts)
