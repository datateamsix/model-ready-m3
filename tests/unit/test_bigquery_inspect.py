from __future__ import annotations

import pandas as pd

from app.core.contracts import Issue, IssueStatus, RemediationClass, Severity
from app.core.model_intent import DATASET_A_MODEL_INTENT, MODEL_READY_COLUMNS
from app.core.model_ready_manifest import compile_model_ready_manifest
from app.tools.bigquery_inspect import evaluate_destination_checks
from app.tools.fingerprints import content_fingerprint
from app.tools.model_consumption import view_selects_table
from app.tools.provenance import FRAME_SOURCE_ROLES
from app.tools.schema_compiler import compile_model_consumption_schema
from app.tools.validation import REQUIRED_DATASET_A_TOOLS


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": ["2024-01-01"],
            "geo": ["CA"],
            "kpi_orders": [1],
            "kpi_revenue": [1.0],
            "revenue_per_kpi": [1.0],
            "population": [1],
            "paid_search_impressions": [1],
            "paid_search_spend": [1.0],
            "shopping_impressions": [1],
            "shopping_spend": [1.0],
            "paid_social_impressions": [1],
            "paid_social_spend": [1.0],
            "organic_sessions": [1],
            "consumer_sentiment_index": [1.0],
            "competitor_discount_index": [0.1],
            "music_center_promo": [0],
        }
    )


def _issues() -> list[Issue]:
    return [
        Issue(
            issue_id=f"MC-A-00{index}",
            rule_id="MR-010",
            severity=Severity.ERROR,
            title=f"issue {index}",
            remediation_class=RemediationClass.AUTO_SAFE,
            proposed_action={"tool": "normalize_dates"},
            status=IssueStatus.RESOLVED,
            resolution_action_ids=[f"act{index}"],
        )
        for index in range(1, 6)
    ]


def _provenance() -> dict:
    records = []
    for tool in REQUIRED_DATASET_A_TOOLS:
        item = {
            "tool": tool,
            "action_id": f"act_{tool}",
            "source_sha256": "a" * 64,
            "output_sha256": "b" * 64,
            "reason": "test",
        }
        if tool == "build_model_ready_frame":
            item["sources"] = [
                {"role": role, "sha256": "c" * 64, "uri": f"gs://bucket/{role}"}
                for role in FRAME_SOURCE_ROLES
            ]
        records.append(item)
    return {"dataset_fingerprint": "d" * 64, "records": records}


def _manifest_and_schema(frame: pd.DataFrame):
    schema = compile_model_consumption_schema(intent=DATASET_A_MODEL_INTENT)
    fingerprint = content_fingerprint(
        frame, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"]
    )
    manifest = compile_model_ready_manifest(
        run_id="run-inspect",
        organization_id="music-center",
        workspace_id="mmm-demo",
        package_uri="gs://raw/package/",
        package_fingerprint="d" * 64,
        intent=DATASET_A_MODEL_INTENT,
        frame=frame,
        issues=_issues(),
        provenance=_provenance(),
        readiness={"status": "PASS"},
        meridian_contract=None,
        canonical_artifact_uri="gs://artifacts/model_ready.csv",
        canonical_artifact_fingerprint=fingerprint,
        schema=schema,
    )
    return manifest, schema


def _actual_schema(schema, *, type_overrides: dict | None = None, drop_descriptions: bool = False):
    records = []
    for field in schema.fields:
        records.append(
            {
                "name": field.name,
                "physical_type": (type_overrides or {}).get(field.name, field.physical_type),
                "mode": field.mode,
                "description": "" if drop_descriptions else field.description,
            }
        )
    return records


def _layout(schema) -> dict:
    return {
        "partition_field": schema.partition_field,
        "partition_type": schema.partition_type,
        "clustering_fields": list(schema.clustering_fields),
        "description": schema.table_description,
    }


def _check_map(checks) -> dict[str, bool]:
    return {item.name: item.passed for item in checks}


def test_physical_string_time_fails_even_when_values_look_like_dates() -> None:
    frame = _frame()
    manifest, schema = _manifest_and_schema(frame)
    checks = evaluate_destination_checks(
        published=frame,
        actual_schema=_actual_schema(schema, type_overrides={"time": "STRING"}),
        layout=_layout(schema),
        manifest=manifest,
        schema=schema,
        meridian_required_fields=["time", "geo", "kpi_orders"],
        expected_project="modelready-m3",
        expected_dataset="modelready_models",
        expected_table="model_input_run",
        actual_project="modelready-m3",
        actual_dataset="modelready_models",
        actual_table="model_input_run",
        destination_exists=True,
        expected_frame=frame,
    )
    by_name = _check_map(checks)
    assert by_name["content_fingerprint_matches"] is True
    assert by_name["physical_schema_matches"] is False


def test_integer_alias_does_not_fail_physical_schema() -> None:
    frame = _frame()
    manifest, schema = _manifest_and_schema(frame)
    checks = evaluate_destination_checks(
        published=frame,
        actual_schema=_actual_schema(schema, type_overrides={"kpi_orders": "INTEGER"}),
        layout=_layout(schema),
        manifest=manifest,
        schema=schema,
        meridian_required_fields=["time", "geo", "kpi_orders"],
        expected_project="modelready-m3",
        expected_dataset="modelready_models",
        expected_table="model_input_run",
        actual_project="modelready-m3",
        actual_dataset="modelready_models",
        actual_table="model_input_run",
        destination_exists=True,
        expected_frame=frame,
    )
    assert _check_map(checks)["physical_schema_matches"] is True


def test_missing_column_descriptions_fail() -> None:
    frame = _frame()
    manifest, schema = _manifest_and_schema(frame)
    checks = evaluate_destination_checks(
        published=frame,
        actual_schema=_actual_schema(schema, drop_descriptions=True),
        layout=_layout(schema),
        manifest=manifest,
        schema=schema,
        meridian_required_fields=["time"],
        expected_project="modelready-m3",
        expected_dataset="modelready_models",
        expected_table="model_input_run",
        actual_project="modelready-m3",
        actual_dataset="modelready_models",
        actual_table="model_input_run",
        destination_exists=True,
        expected_frame=frame,
    )
    assert _check_map(checks)["column_descriptions_match"] is False


def test_partition_and_cluster_mismatches_fail() -> None:
    frame = _frame()
    manifest, schema = _manifest_and_schema(frame)
    checks = evaluate_destination_checks(
        published=frame,
        actual_schema=_actual_schema(schema),
        layout={"partition_field": None, "clustering_fields": [], "partition_type": None},
        manifest=manifest,
        schema=schema,
        meridian_required_fields=["time"],
        expected_project="modelready-m3",
        expected_dataset="modelready_models",
        expected_table="model_input_run",
        actual_project="modelready-m3",
        actual_dataset="modelready_models",
        actual_table="model_input_run",
        destination_exists=True,
        expected_frame=frame,
    )
    by_name = _check_map(checks)
    assert by_name["partitioning"] is False
    assert by_name["clustering"] is False


def test_content_and_key_mismatches_fail() -> None:
    frame = _frame()
    other = frame.copy()
    other.loc[0, "kpi_orders"] = 99
    other_keys = pd.concat([frame, frame.assign(geo="TX")], ignore_index=True)
    manifest, schema = _manifest_and_schema(frame)
    content_checks = evaluate_destination_checks(
        published=other,
        actual_schema=_actual_schema(schema),
        layout=_layout(schema),
        manifest=manifest,
        schema=schema,
        meridian_required_fields=["time"],
        expected_project="modelready-m3",
        expected_dataset="modelready_models",
        expected_table="model_input_run",
        actual_project="modelready-m3",
        actual_dataset="modelready_models",
        actual_table="model_input_run",
        destination_exists=True,
        expected_frame=frame,
    )
    key_checks = evaluate_destination_checks(
        published=other_keys,
        actual_schema=_actual_schema(schema),
        layout=_layout(schema),
        manifest=manifest,
        schema=schema,
        meridian_required_fields=["time"],
        expected_project="modelready-m3",
        expected_dataset="modelready_models",
        expected_table="model_input_run",
        actual_project="modelready-m3",
        actual_dataset="modelready_models",
        actual_table="model_input_run",
        destination_exists=True,
        expected_frame=frame,
    )
    assert _check_map(content_checks)["content_fingerprint_matches"] is False
    assert _check_map(key_checks)["key_set_matches"] is False


def test_view_pointing_at_wrong_table_fails() -> None:
    assert view_selects_table(
        "SELECT * FROM `modelready-m3.modelready_models.model_input_good`",
        "modelready-m3.modelready_models.model_input_good",
    )
    assert not view_selects_table(
        "SELECT * FROM `modelready-m3.modelready_models.model_input_other`",
        "modelready-m3.modelready_models.model_input_good",
    )
