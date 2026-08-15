"""Dataset A local golden slice through VALIDATING. Does not require BigQuery."""

from __future__ import annotations

from pathlib import Path

from app.core.run_coordinator import RunCoordinator
from app.core.state import RunStage

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_A_RAW = REPO_ROOT / "tests" / "fixtures" / "music_center" / "dataset_a" / "raw"


def test_dataset_a_local_slice_detects_five_issues_and_validates(tmp_path: Path) -> None:
    coordinator = RunCoordinator(DATASET_A_RAW, tmp_path / "artifacts")
    summary = coordinator.run_local()
    assert coordinator.stage is RunStage.VALIDATING
    assert len(coordinator.issues) == 5
    assert {issue.issue_id for issue in coordinator.issues} == {
        "MC-A-001",
        "MC-A-002",
        "MC-A-003",
        "MC-A-004",
        "MC-A-005",
    }
    assert summary["readiness_status"] == "PASS"
    assert coordinator.model_ready_path.exists()
    assert coordinator.manifest_path.exists()
    assert coordinator.provenance_path.exists()
    assert not any("expected_model_ready" in str(path) for path in coordinator.raw_dir.rglob("*"))
