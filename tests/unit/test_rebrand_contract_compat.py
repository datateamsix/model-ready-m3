from __future__ import annotations

import pandas as pd

from app.core.meridian_eda_contracts import MeridianEDAReceipt
from app.core.model_intent import DATASET_A_MODEL_INTENT, MODEL_READY_COLUMNS
from app.core.model_ready_manifest import (
    MANIFEST_STATUS,
    ModelReadyManifest,
    compile_model_ready_manifest,
)
from app.core.state import RunStage
from app.tools.fingerprints import content_fingerprint
from app.tools.schema_compiler import compile_model_consumption_schema
from tests.unit.test_meridian_eda import _receipt
from tests.unit.test_model_ready_manifest import DATASET_A_TRUTH, _issues, _provenance


def test_historical_model_ready_manifest_deserializes() -> None:
    frame = pd.read_csv(DATASET_A_TRUTH)
    schema = compile_model_consumption_schema(intent=DATASET_A_MODEL_INTENT)
    fingerprint = content_fingerprint(
        frame, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"]
    )
    manifest = compile_model_ready_manifest(
        run_id="historical-manifest",
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
    payload = manifest.model_dump(mode="json")
    restored = ModelReadyManifest.model_validate(payload)
    assert restored.status == MANIFEST_STATUS
    assert restored.status != RunStage.MODEL_READY.value
    assert restored.identity.run_id == "historical-manifest"
    assert restored.output.row_count == 524


def test_historical_eda_receipt_deserializes() -> None:
    receipt = _receipt()
    payload = receipt.model_dump(mode="json")
    restored = MeridianEDAReceipt.model_validate(payload)
    assert restored.run_id == "run-eda"
    assert restored.posterior_sampling is False
    assert restored.model_fitted is False
    assert restored.status == "EDA_COMPLETE"
