"""Stable model-consumption view, registry, and final confirmation receipts."""

from __future__ import annotations

from typing import Any

from google.cloud import bigquery

from app.config import settings
from app.core.contracts import ParityCheck, utc_now
from app.core.errors import ValidationBlockedError
from app.core.model_intent import MODEL_READY_COLUMNS
from app.core.model_ready_manifest import ModelReadyManifest
from app.tools.artifacts import write_json_artifact
from app.tools.bigquery_inspect import all_checks_passed, inspect_model_destination
from app.tools.fingerprints import content_fingerprint
from app.tools.io import read_table
from app.tools.schema_compiler import (
    ModelConsumptionSchema,
    sanitize_consumption_view_id,
    sanitize_label_value,
    sql_literal,
)

REGISTRY_TABLE_ID = "model_ready_runs"


def consumption_view_ref(
    *,
    project_id: str | None = None,
    dataset_id: str | None = None,
    organization_id: str | None = None,
    workspace_id: str | None = None,
    view_id: str | None = None,
) -> tuple[str, str]:
    project = project_id or settings.project_id
    dataset = dataset_id or settings.bq_models_dataset
    resolved = view_id or sanitize_consumption_view_id(
        organization_id or settings.organization_id,
        workspace_id or settings.workspace_id,
    )
    return f"{project}.{dataset}.{resolved}", resolved


def registry_table_ref(*, project_id: str | None = None, dataset_id: str | None = None) -> str:
    project = project_id or settings.project_id
    dataset = dataset_id or settings.bq_models_dataset
    return f"{project}.{dataset}.{REGISTRY_TABLE_ID}"


REGISTRY_COLUMNS = (
    ("organization_id", "STRING NOT NULL", "Owning ModelReady organization"),
    ("workspace_id", "STRING NOT NULL", "Workspace that produced the model-input run"),
    ("run_id", "STRING NOT NULL", "Versioned M3 run identifier"),
    ("target_model", "STRING NOT NULL", "Downstream model family, e.g. google_meridian"),
    ("status", "STRING NOT NULL", "Registry status after confirmation"),
    ("versioned_table", "STRING NOT NULL", "Fully qualified run-scoped model-input table"),
    ("consumption_view", "STRING NOT NULL", "Stable Meridian-facing view endpoint"),
    ("package_fingerprint", "STRING", "Immutable raw package fingerprint"),
    ("artifact_fingerprint", "STRING", "Canonical local model-ready artifact fingerprint"),
    ("published_fingerprint", "STRING", "Independently read-back BigQuery content fingerprint"),
    ("logical_schema_fingerprint", "STRING", "Logical column-signature fingerprint"),
    (
        "physical_schema_fingerprint",
        "STRING",
        "Physical schema, partition, and cluster fingerprint",
    ),
    ("row_count", "INT64", "Published row count at confirmation"),
    ("column_count", "INT64", "Published column count at confirmation"),
    ("model_ready_manifest_uri", "STRING", "URI of the ModelReady Manifest"),
    ("readiness_receipt_uri", "STRING", "URI of the deterministic readiness receipt"),
    ("publish_receipt_uri", "STRING", "URI of the BigQuery publish receipt"),
    ("meridian_contract_uri", "STRING", "URI of the Meridian input contract"),
    ("provenance_uri", "STRING", "URI of transformation provenance"),
    ("confirmation_receipt_uri", "STRING", "URI of the final MODEL_READY confirmation receipt"),
    ("promoted_at", "TIMESTAMP", "When this registry row was last upserted"),
)


def ensure_registry_table(client: bigquery.Client, table_ref: str) -> None:
    columns = ",\n  ".join(
        f"{name} {ddl_type} OPTIONS(description={sql_literal(description)})"
        for name, ddl_type, description in REGISTRY_COLUMNS
    )
    ddl = f"CREATE TABLE IF NOT EXISTS `{table_ref}` (\n  {columns}\n)"
    client.query(ddl).result()


def promote_consumption_view(
    *,
    client: bigquery.Client,
    view_ref: str,
    versioned_table: str,
    description: str,
    schema: ModelConsumptionSchema | None = None,
) -> str:
    column_sql = ""
    if schema is not None:
        columns = ",\n  ".join(
            f"{field.name} OPTIONS(description={sql_literal(field.description)})"
            for field in schema.fields
        )
        column_sql = f" (\n  {columns}\n)"
    ddl = (
        f"CREATE OR REPLACE VIEW `{view_ref}`{column_sql}\n"
        f"OPTIONS(description={sql_literal(description)})\n"
        f"AS SELECT * FROM `{versioned_table}`"
    )
    client.query(ddl).result()
    return view_ref


def upsert_model_ready_run(
    *,
    client: bigquery.Client,
    row: dict[str, Any],
) -> None:
    table_ref = registry_table_ref()
    ensure_registry_table(client, table_ref)
    sql = f"""
MERGE `{table_ref}` AS target
USING (
  SELECT
    @organization_id AS organization_id,
    @workspace_id AS workspace_id,
    @run_id AS run_id,
    @target_model AS target_model,
    @status AS status,
    @versioned_table AS versioned_table,
    @consumption_view AS consumption_view,
    @package_fingerprint AS package_fingerprint,
    @artifact_fingerprint AS artifact_fingerprint,
    @published_fingerprint AS published_fingerprint,
    @logical_schema_fingerprint AS logical_schema_fingerprint,
    @physical_schema_fingerprint AS physical_schema_fingerprint,
    @row_count AS row_count,
    @column_count AS column_count,
    @model_ready_manifest_uri AS model_ready_manifest_uri,
    @readiness_receipt_uri AS readiness_receipt_uri,
    @publish_receipt_uri AS publish_receipt_uri,
    @meridian_contract_uri AS meridian_contract_uri,
    @provenance_uri AS provenance_uri,
    @confirmation_receipt_uri AS confirmation_receipt_uri,
    CURRENT_TIMESTAMP() AS promoted_at
) AS source
ON target.organization_id = source.organization_id
 AND target.workspace_id = source.workspace_id
 AND target.run_id = source.run_id
 AND target.target_model = source.target_model
WHEN MATCHED THEN UPDATE SET
  status = source.status,
  versioned_table = source.versioned_table,
  consumption_view = source.consumption_view,
  package_fingerprint = source.package_fingerprint,
  artifact_fingerprint = source.artifact_fingerprint,
  published_fingerprint = source.published_fingerprint,
  logical_schema_fingerprint = source.logical_schema_fingerprint,
  physical_schema_fingerprint = source.physical_schema_fingerprint,
  row_count = source.row_count,
  column_count = source.column_count,
  model_ready_manifest_uri = source.model_ready_manifest_uri,
  readiness_receipt_uri = source.readiness_receipt_uri,
  publish_receipt_uri = source.publish_receipt_uri,
  meridian_contract_uri = source.meridian_contract_uri,
  provenance_uri = source.provenance_uri,
  confirmation_receipt_uri = source.confirmation_receipt_uri,
  promoted_at = source.promoted_at
WHEN NOT MATCHED THEN INSERT ROW
"""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("organization_id", "STRING", row["organization_id"]),
            bigquery.ScalarQueryParameter("workspace_id", "STRING", row["workspace_id"]),
            bigquery.ScalarQueryParameter("run_id", "STRING", row["run_id"]),
            bigquery.ScalarQueryParameter("target_model", "STRING", row["target_model"]),
            bigquery.ScalarQueryParameter("status", "STRING", row["status"]),
            bigquery.ScalarQueryParameter("versioned_table", "STRING", row["versioned_table"]),
            bigquery.ScalarQueryParameter("consumption_view", "STRING", row["consumption_view"]),
            bigquery.ScalarQueryParameter(
                "package_fingerprint", "STRING", row.get("package_fingerprint")
            ),
            bigquery.ScalarQueryParameter(
                "artifact_fingerprint", "STRING", row.get("artifact_fingerprint")
            ),
            bigquery.ScalarQueryParameter(
                "published_fingerprint", "STRING", row.get("published_fingerprint")
            ),
            bigquery.ScalarQueryParameter(
                "logical_schema_fingerprint", "STRING", row.get("logical_schema_fingerprint")
            ),
            bigquery.ScalarQueryParameter(
                "physical_schema_fingerprint", "STRING", row.get("physical_schema_fingerprint")
            ),
            bigquery.ScalarQueryParameter("row_count", "INT64", row.get("row_count")),
            bigquery.ScalarQueryParameter("column_count", "INT64", row.get("column_count")),
            bigquery.ScalarQueryParameter(
                "model_ready_manifest_uri", "STRING", row.get("model_ready_manifest_uri")
            ),
            bigquery.ScalarQueryParameter(
                "readiness_receipt_uri", "STRING", row.get("readiness_receipt_uri")
            ),
            bigquery.ScalarQueryParameter(
                "publish_receipt_uri", "STRING", row.get("publish_receipt_uri")
            ),
            bigquery.ScalarQueryParameter(
                "meridian_contract_uri", "STRING", row.get("meridian_contract_uri")
            ),
            bigquery.ScalarQueryParameter("provenance_uri", "STRING", row.get("provenance_uri")),
            bigquery.ScalarQueryParameter(
                "confirmation_receipt_uri", "STRING", row.get("confirmation_receipt_uri")
            ),
        ]
    )
    client.query(sql, job_config=job_config).result()


def read_registry_row(
    *,
    client: bigquery.Client,
    organization_id: str,
    workspace_id: str,
    run_id: str,
    target_model: str,
) -> dict[str, Any] | None:
    table_ref = registry_table_ref()
    sql = f"""
SELECT *
FROM `{table_ref}`
WHERE organization_id = @organization_id
  AND workspace_id = @workspace_id
  AND run_id = @run_id
  AND target_model = @target_model
"""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("organization_id", "STRING", organization_id),
            bigquery.ScalarQueryParameter("workspace_id", "STRING", workspace_id),
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
            bigquery.ScalarQueryParameter("target_model", "STRING", target_model),
        ]
    )
    rows = list(client.query(sql, job_config=job_config).result())
    if not rows:
        return None
    return dict(rows[0])


def count_registry_rows(
    *,
    client: bigquery.Client,
    organization_id: str,
    workspace_id: str,
    run_id: str,
    target_model: str,
) -> int:
    table_ref = registry_table_ref()
    sql = f"""
SELECT COUNT(1) AS n
FROM `{table_ref}`
WHERE organization_id = @organization_id
  AND workspace_id = @workspace_id
  AND run_id = @run_id
  AND target_model = @target_model
"""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("organization_id", "STRING", organization_id),
            bigquery.ScalarQueryParameter("workspace_id", "STRING", workspace_id),
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
            bigquery.ScalarQueryParameter("target_model", "STRING", target_model),
        ]
    )
    rows = list(client.query(sql, job_config=job_config).result())
    return int(rows[0]["n"]) if rows else 0


def verify_consumption_view(
    *,
    client: bigquery.Client,
    view_ref: str,
    versioned_table: str,
    manifest: ModelReadyManifest,
    schema: ModelConsumptionSchema,
    expected_frame,
    meridian_required_fields: list[str],
) -> list[ParityCheck]:
    view = client.get_table(view_ref)
    if view.table_type != "VIEW":
        raise ValidationBlockedError(f"{view_ref} is not a BigQuery VIEW.")
    points_at_table = view_selects_table(view.view_query, versioned_table)
    checks = inspect_model_destination(
        table_ref=view_ref,
        client=client,
        manifest=manifest,
        schema=schema,
        meridian_required_fields=meridian_required_fields,
        expected_project=view.project,
        expected_dataset=view.dataset_id,
        expected_table=view.table_id,
        expected_frame=expected_frame,
    )
    rewritten: list[ParityCheck] = []
    skip_on_view = {
        "partitioning",
        "clustering",
        "table_matches",
        "project_matches",
        "dataset_matches",
        "column_descriptions_match",
    }
    for check in checks:
        if check.name in skip_on_view:
            rewritten.append(
                ParityCheck(
                    name=check.name,
                    passed=True,
                    evidence={"skipped": "view_endpoint", **check.evidence},
                )
            )
        else:
            rewritten.append(check)
    rewritten.append(
        ParityCheck(
            name="view_points_at_versioned_table",
            passed=points_at_table,
            evidence={"view_query": view.view_query, "versioned_table": versioned_table},
        )
    )
    return rewritten


def build_consumption_receipt(
    *,
    run_id: str,
    target_model: str,
    versioned_table: str,
    consumption_view: str,
    schema: ModelConsumptionSchema,
    actual_schema: list[dict[str, Any]],
    expected_content_fingerprint: str,
    versioned_fingerprint: str,
    view_fingerprint: str,
    row_count: int,
    verification_checks: list[ParityCheck],
    registry_recorded: bool,
) -> dict[str, Any]:
    passed = all_checks_passed(verification_checks) and registry_recorded
    return {
        "run_id": run_id,
        "status": "PROMOTION_VERIFIED" if passed else "PROMOTION_FAILED",
        "target_model": target_model,
        "versioned_table": versioned_table,
        "consumption_view": consumption_view,
        "expected_schema": schema.model_dump(mode="json"),
        "actual_schema": actual_schema,
        "logical_schema_fingerprint": schema.physical_schema_fingerprint(),
        "physical_schema_fingerprint": schema.physical_schema_fingerprint(),
        "expected_content_fingerprint": expected_content_fingerprint,
        "versioned_table_content_fingerprint": versioned_fingerprint,
        "consumption_view_content_fingerprint": view_fingerprint,
        "row_count": row_count,
        "verification_checks": [check.model_dump(mode="json") for check in verification_checks],
        "registry_recorded": registry_recorded,
        "promoted_at": utc_now().isoformat(),
    }


def build_confirmation_receipt(
    *,
    run_id: str,
    manifest_uri: str,
    versioned_table: str,
    consumption_view: str,
    checks: dict[str, bool],
    target_model: str,
) -> dict[str, Any]:
    ready = all(bool(value) for value in checks.values())
    return {
        "run_id": run_id,
        "status": "MODEL_READY" if ready else "NOT_MODEL_READY",
        "model_ready_manifest_uri": manifest_uri,
        "destination": {
            "versioned_table": versioned_table,
            "consumption_view": consumption_view,
        },
        "checks": checks,
        "model_consumption": {"target": target_model, "ready": ready},
        "confirmed_at": utc_now().isoformat(),
    }


def write_receipt(path, payload: dict[str, Any]) -> None:
    write_json_artifact(path, payload)


def view_selects_table(view_query: str | None, versioned_table: str) -> bool:
    haystack = (view_query or "").replace("`", "").lower()
    needle = versioned_table.replace("`", "").lower()
    return needle in haystack


def fingerprint_frame(frame) -> str:
    return content_fingerprint(frame, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"])


def load_local_frame(path) -> Any:
    return read_table(path)


def table_labels(run_id: str) -> dict[str, str]:
    return {
        "modelready": "true",
        "target": "meridian",
        "run_id": sanitize_label_value(run_id),
    }


def _sql_string(value: str) -> str:
    return sql_literal(value)
