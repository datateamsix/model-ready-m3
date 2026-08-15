"""Live BigQuery publish + parity for Dataset A. Skipped without ADC."""

from __future__ import annotations

from pathlib import Path

import google.auth
import pytest

from app.config import settings
from app.core.run_coordinator import RunCoordinator
from app.core.state import RunStage
from app.integrations.bigquery import get_bigquery_client

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_A_RAW = REPO_ROOT / "tests" / "fixtures" / "music_center" / "dataset_a" / "raw"


def _has_adc() -> bool:
    try:
        credentials, _project = google.auth.default()
        return credentials is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _has_adc(), reason="Google ADC is not available")


def test_dataset_a_bigquery_publish_parity_and_model_ready(tmp_path: Path) -> None:
    coordinator = RunCoordinator(DATASET_A_RAW, tmp_path / "artifacts", run_id="pytestgcp001")
    result = coordinator.run()
    client = None
    table_id = None
    try:
        assert result["status"] == "MODEL_READY"
        assert coordinator.stage is RunStage.MODEL_READY
        receipt = result["gate"]
        assert receipt["terminal"]["publish_parity_passed"] is True
        publish = result["summary"]["artifact_uris"]["publish_receipt"]
        assert publish
        table_id = f"model_input_{coordinator.run_id}"
        client = get_bigquery_client()
        table = client.get_table(f"{settings.project_id}.{settings.bq_models_dataset}.{table_id}")
        assert int(table.num_rows) == 524
    finally:
        if client is not None and table_id is not None:
            client.delete_table(
                f"{settings.project_id}.{settings.bq_models_dataset}.{table_id}",
                not_found_ok=True,
            )
