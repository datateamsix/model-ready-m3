"""Inspect actual BigQuery destinations against a ModelReady Manifest.

Never treat a successful load job as proof. Read metadata and rows back.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from google.cloud import bigquery

from app.core.contracts import ParityCheck
from app.core.model_intent import MODEL_READY_COLUMNS
from app.core.model_ready_manifest import ModelReadyManifest
from app.tools.fingerprints import content_fingerprint
from app.tools.model_frame import coerce_model_frame_types
from app.tools.schema_compiler import (
    ModelConsumptionSchema,
    normalize_bq_type,
    table_layout_metadata,
)


def inspect_model_destination(
    *,
    table_ref: str,
    client: bigquery.Client,
    manifest: ModelReadyManifest,
    schema: ModelConsumptionSchema,
    meridian_required_fields: list[str],
    expected_project: str,
    expected_dataset: str,
    expected_table: str,
    expected_frame: pd.DataFrame | None = None,
) -> list[ParityCheck]:
    table = client.get_table(table_ref)
    published = coerce_model_frame_types(_read_table(client, table_ref))
    return evaluate_destination_checks(
        published=published,
        actual_schema=list(table.schema),
        layout=table_layout_metadata(table),
        manifest=manifest,
        schema=schema,
        meridian_required_fields=meridian_required_fields,
        expected_project=expected_project,
        expected_dataset=expected_dataset,
        expected_table=expected_table,
        actual_project=table.project,
        actual_dataset=table.dataset_id,
        actual_table=table.table_id,
        destination_exists=True,
        expected_frame=expected_frame,
    )


def evaluate_destination_checks(
    *,
    published: pd.DataFrame,
    actual_schema: list[Any],
    layout: dict[str, Any],
    manifest: ModelReadyManifest,
    schema: ModelConsumptionSchema,
    meridian_required_fields: list[str],
    expected_project: str,
    expected_dataset: str,
    expected_table: str,
    actual_project: str,
    actual_dataset: str,
    actual_table: str,
    destination_exists: bool,
    expected_frame: pd.DataFrame | None = None,
) -> list[ParityCheck]:
    expected_fp = manifest.output.expected_artifact_fingerprint
    published_fp = content_fingerprint(
        published, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"]
    )
    expected_cols = list(manifest.output.expected_columns)
    actual_cols = [column for column in MODEL_READY_COLUMNS if column in published.columns]
    actual_keys = _key_set(published)
    expected_keys = _key_set(expected_frame) if expected_frame is not None else actual_keys
    published_nulls = (
        int(published.loc[:, MODEL_READY_COLUMNS].isna().sum().sum())
        if all(column in published.columns for column in MODEL_READY_COLUMNS)
        else -1
    )
    physical = compare_physical_schema(schema, actual_schema)
    descriptions = compare_column_descriptions(schema, actual_schema)
    partition = ParityCheck(
        name="partitioning",
        passed=layout.get("partition_field") == schema.partition_field,
        evidence={
            "expected": schema.partition_field,
            "actual": layout.get("partition_field"),
        },
    )
    clustering = ParityCheck(
        name="clustering",
        passed=list(layout.get("clustering_fields") or []) == list(schema.clustering_fields),
        evidence={
            "expected": list(schema.clustering_fields),
            "actual": layout.get("clustering_fields") or [],
        },
    )
    grain_unique = len(actual_keys) == int(len(published)) if actual_keys else False
    return [
        ParityCheck(
            name="destination_exists",
            passed=destination_exists,
            evidence={"table": f"{actual_project}.{actual_dataset}.{actual_table}"},
        ),
        ParityCheck(
            name="project_matches",
            passed=actual_project == expected_project,
            evidence={"expected": expected_project, "actual": actual_project},
        ),
        ParityCheck(
            name="dataset_matches",
            passed=actual_dataset == expected_dataset,
            evidence={"expected": expected_dataset, "actual": actual_dataset},
        ),
        ParityCheck(
            name="table_matches",
            passed=actual_table == expected_table,
            evidence={"expected": expected_table, "actual": actual_table},
        ),
        ParityCheck(
            name="row_count_matches",
            passed=int(len(published)) == manifest.output.row_count,
            evidence={"expected": manifest.output.row_count, "actual": int(len(published))},
        ),
        ParityCheck(
            name="column_count_matches",
            passed=int(len(published.columns)) == manifest.output.column_count,
            evidence={
                "expected": manifest.output.column_count,
                "actual": int(len(published.columns)),
            },
        ),
        ParityCheck(
            name="column_names_match",
            passed=actual_cols == expected_cols,
            evidence={"expected": expected_cols, "actual": actual_cols},
        ),
        physical,
        descriptions,
        partition,
        clustering,
        ParityCheck(
            name="logical_schema_matches",
            passed=actual_cols == expected_cols,
            evidence={"expected_columns": expected_cols, "actual_columns": actual_cols},
        ),
        ParityCheck(
            name="grain_unique",
            passed=grain_unique,
            evidence={"row_count": int(len(published)), "unique_keys": len(actual_keys)},
        ),
        ParityCheck(
            name="key_set_matches",
            passed=actual_keys == expected_keys and len(actual_keys) == manifest.output.row_count,
            evidence={
                "only_expected": len(expected_keys - actual_keys),
                "only_actual": len(actual_keys - expected_keys),
                "actual_key_count": len(actual_keys),
            },
        ),
        ParityCheck(
            name="null_policy_matches",
            passed=published_nulls == 0,
            evidence={"null_cells": published_nulls, "policy": manifest.output.null_policy},
        ),
        ParityCheck(
            name="content_fingerprint_matches",
            passed=published_fp == expected_fp,
            evidence={"expected": expected_fp, "actual": published_fp},
        ),
        ParityCheck(
            name="artifact_fingerprint_matches",
            passed=published_fp == manifest.identity.canonical_artifact_fingerprint,
            evidence={
                "expected": manifest.identity.canonical_artifact_fingerprint,
                "actual": published_fp,
            },
        ),
        ParityCheck(
            name="meridian_required_fields_present",
            passed=all(field in published.columns for field in meridian_required_fields),
            evidence={"required": meridian_required_fields},
        ),
        ParityCheck(
            name="semantic_families_match",
            passed=_semantics_present(published, manifest),
            evidence={"kpi": manifest.semantics.kpi, "revenue": manifest.semantics.revenue},
        ),
        ParityCheck(
            name="provenance_references_intact",
            passed=bool(manifest.identity.provenance_uri) and bool(manifest.transformations),
            evidence={
                "provenance_uri": manifest.identity.provenance_uri,
                "transformation_count": len(manifest.transformations),
            },
        ),
    ]


def compare_physical_schema(
    expected: ModelConsumptionSchema, actual_schema: list[Any]
) -> ParityCheck:
    actual = {}
    for field in actual_schema:
        name = _schema_field_name(field)
        actual[name] = normalize_bq_type(_schema_field_type(field))
    mismatches: list[dict[str, str]] = []
    for field in expected.fields:
        got = actual.get(field.name)
        if got != normalize_bq_type(field.physical_type):
            mismatches.append(
                {
                    "name": field.name,
                    "expected": field.physical_type,
                    "actual": got or "MISSING",
                }
            )
    return ParityCheck(
        name="physical_schema_matches",
        passed=not mismatches and len(actual) == len(expected.fields),
        evidence={"mismatches": mismatches, "actual_field_count": len(actual)},
    )


def compare_column_descriptions(
    expected: ModelConsumptionSchema, actual_schema: list[Any]
) -> ParityCheck:
    actual = {}
    for field in actual_schema:
        name = _schema_field_name(field)
        actual[name] = _schema_field_description(field)
    missing = [
        field.name
        for field in expected.fields
        if actual.get(field.name) != field.description
    ]
    return ParityCheck(
        name="column_descriptions_match",
        passed=not missing,
        evidence={"mismatched_fields": missing},
    )


def _schema_field_name(field: Any) -> str:
    if isinstance(field, dict):
        return str(field.get("name") or "")
    return str(getattr(field, "name", "") or "")


def _schema_field_type(field: Any) -> str:
    if isinstance(field, dict):
        return str(field.get("physical_type") or field.get("type") or "")
    return str(getattr(field, "field_type", "") or "")


def _schema_field_description(field: Any) -> str:
    if isinstance(field, dict):
        return str(field.get("description") or "")
    return str(getattr(field, "description", None) or "")


def all_checks_passed(checks: list[ParityCheck]) -> bool:
    return all(check.passed for check in checks)


def _read_table(client: bigquery.Client, table_ref: str) -> pd.DataFrame:
    query = f"SELECT * FROM `{table_ref}`"
    return client.query(query).result().to_dataframe(create_bqstorage_client=False)


def _key_set(frame: pd.DataFrame) -> set[tuple[str, str]]:
    if "time" not in frame.columns or "geo" not in frame.columns:
        return set()
    return set(zip(frame["time"].astype(str), frame["geo"].astype(str), strict=False))


def _semantics_present(published: pd.DataFrame, manifest: ModelReadyManifest) -> bool:
    required = [
        manifest.semantics.time,
        manifest.semantics.kpi,
        manifest.semantics.revenue,
        manifest.semantics.revenue_per_kpi,
        *manifest.semantics.organic_media,
        *manifest.semantics.controls,
    ]
    if manifest.semantics.geo:
        required.append(manifest.semantics.geo)
    if manifest.semantics.population:
        required.append(manifest.semantics.population)
    for channel in manifest.semantics.paid_media:
        required.extend([channel["impressions_field"], channel["spend_field"]])
    return all(name in published.columns for name in required)
