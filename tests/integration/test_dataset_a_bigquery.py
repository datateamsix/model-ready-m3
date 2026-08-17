"""Live BigQuery publish + consumption proof for Dataset A. Skipped without ADC."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import google.auth
import pytest
from google.cloud import bigquery

from app.config import settings
from app.core.developer_bootstrap import bind_developer_bootstrap
from app.core.model_intent import DATASET_A_MODEL_INTENT, MODEL_READY_COLUMNS
from app.core.run_coordinator import RunCoordinator
from app.core.state import RunStage
from app.core.tenancy import require_tenant, require_workspace
from app.integrations.bigquery import get_bigquery_client
from app.synthetic.paths import DATASET_A_DIR
from app.tools.bigquery_publish import read_bigquery_table, sanitize_table_id
from app.tools.fingerprints import content_fingerprint
from app.tools.model_consumption import read_registry_row
from app.tools.model_frame import coerce_model_frame_types
from app.tools.schema_compiler import compile_model_consumption_schema, normalize_bq_type

DATASET_A_RAW = DATASET_A_DIR / "raw"
DEMO_VIEW_ID = "meridian_input_music_center_mmm_demo"


def _has_adc() -> bool:
    try:
        credentials, _project = google.auth.default()
        return credentials is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _has_adc(), reason="Google ADC is not available")


def test_dataset_a_bigquery_publish_parity_and_model_ready(tmp_path: Path) -> None:
    with bind_developer_bootstrap():
        _dataset_a_bigquery_publish_parity_and_model_ready(tmp_path)


def _dataset_a_bigquery_publish_parity_and_model_ready(tmp_path: Path) -> None:
    run_id = f"pytestg{uuid4().hex[:8]}"
    view_id = f"meridian_input_test_{run_id}"
    table_id = sanitize_table_id(run_id)
    table_ref = f"{settings.project_id}.{settings.bq_models_dataset}.{table_id}"
    view_ref = f"{settings.project_id}.{settings.bq_models_dataset}.{view_id}"
    coordinator = RunCoordinator(
        DATASET_A_RAW,
        tmp_path / "artifacts",
        run_id=run_id,
        stable_view_id=view_id,
    )
    client = get_bigquery_client()
    try:
        result = coordinator.run()
        assert result["status"] == "MODEL_READY"
        assert coordinator.stage is RunStage.MODEL_READY
        assert result["summary"]["detected_issue_count"] == 5
        assert result["summary"]["resolved_issue_count"] == 5
        assert result["summary"]["open_issue_count"] == 0
        gate = result["gate"]
        assert gate["terminal"]["publish_parity_passed"] is True
        assert gate["terminal"]["physical_bigquery_schema_passed"] is True
        assert gate["terminal"]["partitioned_by_time"] is True
        assert gate["terminal"]["clustered_by_geo"] is True
        assert gate["terminal"]["column_descriptions_present"] is True

        expected = compile_model_consumption_schema(intent=DATASET_A_MODEL_INTENT)
        table = client.get_table(table_ref)
        assert int(table.num_rows) == 524
        assert table.time_partitioning is not None
        assert table.time_partitioning.field == "time"
        assert list(table.clustering_fields or []) == ["geo"]
        actual_types = {field.name: normalize_bq_type(field.field_type) for field in table.schema}
        actual_descriptions = {field.name: field.description or "" for field in table.schema}
        assert len(table.schema) == 16
        for field in expected.fields:
            assert actual_types[field.name] == field.physical_type
            assert actual_descriptions[field.name] == field.description

        published = coerce_model_frame_types(read_bigquery_table(table_ref, client=client))
        view_rows = coerce_model_frame_types(read_bigquery_table(view_ref, client=client))
        expected_fp = content_fingerprint(
            published, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"]
        )
        view_fp = content_fingerprint(
            view_rows, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"]
        )
        assert len(published) == 524
        assert len(view_rows) == 524
        assert expected_fp == view_fp
        assert published["time"].notna().all()
        assert published["geo"].notna().all()

        manifest = coordinator._load_json_if_exists(coordinator.model_ready_manifest_path)
        confirmation = coordinator._load_json_if_exists(coordinator.confirmation_path)
        consumption = coordinator._load_json_if_exists(coordinator.consumption_receipt_path)
        assert manifest is not None
        assert manifest["status"] == "VALIDATED_FOR_PUBLICATION"
        assert manifest["output"]["expected_artifact_fingerprint"] == expected_fp
        assert confirmation["status"] == "MODEL_READY"
        assert consumption["status"] == "PROMOTION_VERIFIED"
        assert coordinator.consumption_view == view_ref
        assert view_id != DEMO_VIEW_ID

        recorded = read_registry_row(
            client=client,
            organization_id=require_tenant().tenant_id,
            workspace_id=require_workspace().workspace_id,
            run_id=run_id,
            target_model="google_meridian",
        )
        assert recorded is not None
        assert recorded["versioned_table"] == table_ref
        assert recorded["consumption_view"] == view_ref
        assert recorded["status"] == "MODEL_READY"
    finally:
        client.delete_table(table_ref, not_found_ok=True)
        client.delete_table(view_ref, not_found_ok=True)
        registry = f"{settings.project_id}.{settings.bq_models_dataset}.model_ready_runs"
        try:
            client.query(
                f"DELETE FROM `{registry}` WHERE run_id = @run_id",
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("run_id", "STRING", run_id)
                    ]
                ),
            ).result()
        except Exception:
            pass
