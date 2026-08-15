from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.core.contracts import Issue, IssueStatus, RemediationClass, Severity
from app.core.errors import ValidationBlockedError
from app.core.model_intent import DATASET_A_MODEL_INTENT, MODEL_READY_COLUMNS
from app.core.model_ready_manifest import MANIFEST_STATUS, compile_model_ready_manifest
from app.tools.fingerprints import content_fingerprint
from app.tools.provenance import FRAME_SOURCE_ROLES
from app.tools.schema_compiler import compile_model_consumption_schema
from app.tools.validation import REQUIRED_DATASET_A_TOOLS

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_A_TRUTH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "music_center"
    / "dataset_a"
    / "truth"
    / "expected_model_ready_weekly.csv"
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


def _provenance(*, extra_transforms: int = 2) -> dict:
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
    for index in range(extra_transforms):
        records.append(
            {
                "tool": "normalize_dates",
                "action_id": f"act_extra_{index}",
                "source_sha256": "a" * 64,
                "output_sha256": "b" * 64,
                "reason": "second provider date repair",
            }
        )
    return {"dataset_fingerprint": "d" * 64, "records": records}


def test_manifest_compiles_dataset_a_contract_without_claiming_model_ready() -> None:
    frame = pd.read_csv(DATASET_A_TRUTH)
    schema = compile_model_consumption_schema(intent=DATASET_A_MODEL_INTENT)
    fingerprint = content_fingerprint(
        frame, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"]
    )
    manifest = compile_model_ready_manifest(
        run_id="run-manifest",
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
    assert manifest.status == MANIFEST_STATUS
    assert manifest.status != "MODEL_READY"
    assert len(manifest.issues) == 5
    assert all(item.final_status == "RESOLVED" for item in manifest.issues)
    assert len(manifest.transformations) == 9
    assert manifest.output.row_count == 524
    assert manifest.output.column_count == 16
    assert manifest.output.expected_columns == MODEL_READY_COLUMNS
    assert manifest.output.partition_field == "time"
    assert manifest.output.clustering_fields == ["geo"]
    assert manifest.identity.canonical_artifact_fingerprint == fingerprint
    assert {source.role for source in manifest.sources} == set(FRAME_SOURCE_ROLES)
    assert manifest.semantics.kpi == "kpi_orders"
    assert manifest.semantics.revenue == "kpi_revenue"
    assert len(manifest.semantics.paid_media) == 3
    assert "music_center_promo" in manifest.semantics.controls


def test_manifest_requires_pass_readiness() -> None:
    frame = pd.DataFrame({"time": ["2024-01-01"], "geo": ["CA"]})
    with pytest.raises(ValidationBlockedError, match="PASS readiness"):
        compile_model_ready_manifest(
            run_id="run-fail",
            organization_id="music-center",
            workspace_id="mmm-demo",
            package_uri="gs://raw/package/",
            package_fingerprint="d" * 64,
            intent=DATASET_A_MODEL_INTENT,
            frame=frame,
            issues=[],
            provenance=_provenance(),
            readiness={"status": "FAIL"},
            meridian_contract=None,
            canonical_artifact_uri="gs://artifacts/model_ready.csv",
        )
