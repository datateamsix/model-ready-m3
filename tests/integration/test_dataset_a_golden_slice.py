"""Dataset A local golden slice through VALIDATING. Does not require BigQuery."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.contracts import IssueStatus
from app.core.run_coordinator import RunCoordinator
from app.core.state import RunStage
from app.synthetic.paths import DATASET_A_DIR
from app.tools.provenance import FRAME_SOURCE_ROLES
from app.tools.validation import REQUIRED_DATASET_A_TOOLS, validate_provenance_complete

DATASET_A_RAW = DATASET_A_DIR / "raw"


def test_dataset_a_local_slice_detects_five_issues_and_validates(tmp_path: Path) -> None:
    coordinator = RunCoordinator(DATASET_A_RAW, tmp_path / "artifacts")
    summary = coordinator.run_local()
    assert coordinator.stage is RunStage.VALIDATING
    assert summary["detected_issue_count"] == 5
    assert summary["resolved_issue_count"] == 5
    assert summary["open_issue_count"] == 0
    assert {issue.issue_id for issue in coordinator.issues} == {
        "MC-A-001",
        "MC-A-002",
        "MC-A-003",
        "MC-A-004",
        "MC-A-005",
    }
    assert all(issue.status is IssueStatus.RESOLVED for issue in coordinator.issues)
    assert all(issue.resolution_action_ids for issue in coordinator.issues)
    assert summary["readiness"]["status"] == "PASS"
    assert coordinator.model_ready_path.exists()
    assert coordinator.manifest_path.exists()
    assert coordinator.provenance_path.exists()
    assert not any("expected_model_ready" in str(path) for path in coordinator.raw_dir.rglob("*"))

    manifest = json.loads(coordinator.manifest_path.read_text(encoding="utf-8"))
    provenance = json.loads(coordinator.provenance_path.read_text(encoding="utf-8"))
    mr018 = validate_provenance_complete(manifest, REQUIRED_DATASET_A_TOOLS)
    assert mr018.passed is True
    frame = next(
        item for item in manifest["transforms"] if item["tool"] == "build_model_ready_frame"
    )
    roles = {source["role"] for source in frame["sources"]}
    assert roles == set(FRAME_SOURCE_ROLES)
    assert all(source["sha256"] for source in frame["sources"])
    assert provenance["dataset_fingerprint"] == summary["dataset_fingerprint"]
    assert frame["output_sha256"]
    assert summary["model_artifact"]["fingerprint"]
    assert summary["transformation_count"] >= len(REQUIRED_DATASET_A_TOOLS)
