"""Unit tests for CLOUD_TASKMASTER run-level tools, idempotency, and resumability."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.core.contracts import RemediationClass
from app.core.errors import SafetyViolationError
from app.core.run_repository import (
    LocalFilesystemRunRepository,
    assert_runtime_package,
    bind_run_repository,
    reset_run_repository,
)
from app.core.state import RunStage
from app.tools.run_tools import (
    _scratch_dir,
    apply_safe_remediations,
    complete_dataset_run,
    initialize_dataset_run,
    inspect_dataset_run,
    validate_and_publish_run,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_A_RAW = REPO_ROOT / "tests" / "fixtures" / "music_center" / "dataset_a" / "raw"
PACKAGE_REL = "music-center/mmm-demo/dataset-a/packages/dataset-a-v1"


@pytest.fixture
def run_repo(tmp_path: Path):
    repo = LocalFilesystemRunRepository(
        root=tmp_path / "durable",
        raw_bucket="test-raw-bucket",
        artifact_bucket="test-artifact-bucket",
    )
    staged = repo.raw_root / PACKAGE_REL
    shutil.copytree(DATASET_A_RAW, staged)
    token = bind_run_repository(repo)
    try:
        yield repo
    finally:
        reset_run_repository(token)


def _package_uri(repo: LocalFilesystemRunRepository) -> str:
    return f"gs://{repo.raw_bucket}/{PACKAGE_REL}/"


def test_initialize_rejects_non_approved_bucket(run_repo: LocalFilesystemRunRepository) -> None:
    result = initialize_dataset_run("gs://other-bucket/music-center/package/")
    assert result["status"] == "FAIL"
    assert "raw bucket" in result["error"]


def test_initialize_rejects_local_paths(run_repo: LocalFilesystemRunRepository) -> None:
    result = initialize_dataset_run(str(DATASET_A_RAW))
    assert result["status"] == "FAIL"
    assert result["error_type"] == "SafetyViolationError"


def test_initialize_dataset_a_detects_five_auto_safe_issues(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    result = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudinit01")
    assert result["status"] == "SUCCESS"
    assert result["stage"] == "ASSESSING"
    assert result["package"]["input_file_count"] == 7
    assert result["issue_counts"]["detected"] == 5
    assert result["issue_counts"]["auto_safe"] == 5
    assert result["issue_counts"]["open"] == 5
    assert {item["issue_id"] for item in result["issues"]} == {
        "MC-A-001",
        "MC-A-002",
        "MC-A-003",
        "MC-A-004",
        "MC-A-005",
    }
    assert "apply_safe_remediations" in result["allowed_next_actions"]
    assert run_repo.run_exists("m3cloudinit01")


def test_apply_unknown_issue_fails(run_repo: LocalFilesystemRunRepository) -> None:
    initialized = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudunk01")
    assert initialized["status"] == "SUCCESS"
    result = apply_safe_remediations("m3cloudunk01", ["NOT-A-REAL-ISSUE"])
    assert result["status"] == "FAIL"
    assert "unknown_issue" in result["error"]


def test_apply_non_auto_safe_issue_fails(run_repo: LocalFilesystemRunRepository) -> None:
    initialized = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudns01")
    assert initialized["status"] == "SUCCESS"
    issues = run_repo.load_issues("m3cloudns01")
    issues[0].remediation_class = RemediationClass.APPROVAL_REQUIRED
    run_repo.save_issues("m3cloudns01", issues)
    result = apply_safe_remediations("m3cloudns01", [issues[0].issue_id])
    assert result["status"] == "FAIL"
    assert "not_auto_safe" in result["error"]


def test_apply_safe_remediations_resolves_selected_dataset_a_issues(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    initialized = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudrem01")
    issue_ids = [item["issue_id"] for item in initialized["issues"]]
    result = apply_safe_remediations("m3cloudrem01", issue_ids)
    assert result["status"] == "SUCCESS"
    assert result["counts"]["resolved"] == 5
    assert result["counts"]["open"] == 0
    assert "validate_and_publish_run" in result["allowed_next_actions"]
    inspected = inspect_dataset_run("m3cloudrem01")
    assert inspected["issue_counts"]["open"] == 0
    assert inspected["stage"] == "REMEDIATING"


def test_validate_with_unresolved_blocker_fails(run_repo: LocalFilesystemRunRepository) -> None:
    initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudval01")
    result = validate_and_publish_run("m3cloudval01")
    assert result["status"] == "FAIL"
    assert "unresolved_auto_safe" in result["error"]


def test_complete_without_publish_receipt_fails(run_repo: LocalFilesystemRunRepository) -> None:
    initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudcmp01")
    result = complete_dataset_run("m3cloudcmp01")
    assert result["status"] == "FAIL"
    assert "publish_receipt.json" in result["error"]


def test_same_run_id_different_fingerprint_fails(
    run_repo: LocalFilesystemRunRepository, tmp_path: Path
) -> None:
    initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudfp01")
    other = run_repo.raw_root / "music-center/mmm-demo/dataset-a/packages/dataset-a-other"
    shutil.copytree(DATASET_A_RAW, other)
    (other / "google_ads_daily.csv").write_text(
        (other / "google_ads_daily.csv").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    result = initialize_dataset_run(
        f"gs://{run_repo.raw_bucket}/music-center/mmm-demo/dataset-a/packages/dataset-a-other/",
        requested_run_id="m3cloudfp01",
    )
    assert result["status"] == "FAIL"
    assert "different package fingerprint" in result["error"]


def test_completed_run_id_does_not_duplicate_transforms(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    initialized = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3clouddup01")
    apply_safe_remediations(
        "m3clouddup01", [item["issue_id"] for item in initialized["issues"]]
    )
    provenance = run_repo.load_json("m3clouddup01", "provenance.json") or {}
    before = len(provenance.get("records") or [])
    state = run_repo.load_run("m3clouddup01")
    state.stage = RunStage.MODEL_READY
    state.status = "MODEL_READY"
    run_repo.save_run(state)
    result = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3clouddup01")
    assert result["status"] == "MODEL_READY"
    assert result["replayed"] is True
    after = run_repo.load_json("m3clouddup01", "provenance.json") or {}
    assert len(after.get("records") or []) == before


def test_initialize_same_in_progress_run_resumes_without_duplicate_provenance(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    first = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudrs01")
    provenance = run_repo.load_json("m3cloudrs01", "provenance.json") or {}
    before = len(provenance.get("records") or [])
    second = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudrs01")
    assert second["status"] == "SUCCESS"
    assert second["resumed"] is True
    assert second["run_id"] == first["run_id"]
    after = run_repo.load_json("m3cloudrs01", "provenance.json") or {}
    assert len(after.get("records") or []) == before


def test_run_survives_destroyed_local_workspace(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    initialized = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudmem01")
    scratch = _scratch_dir("m3cloudmem01")
    if scratch.exists():
        shutil.rmtree(scratch)
    inspected = inspect_dataset_run("m3cloudmem01")
    assert inspected["status"] == "SUCCESS"
    assert inspected["issue_counts"]["detected"] == 5
    result = apply_safe_remediations(
        "m3cloudmem01", [item["issue_id"] for item in initialized["issues"]]
    )
    assert result["status"] == "SUCCESS"
    assert result["counts"]["resolved"] == 5
    assert result["counts"]["open"] == 0


def test_initialize_rejects_regression_truth_file(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    staged = run_repo.raw_root / PACKAGE_REL
    (staged / "expected_model_ready_weekly.csv").write_text("nope\n", encoding="utf-8")
    result = initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudtr01")
    assert result["status"] == "FAIL"


def test_assert_runtime_package_rejects_truth_paths() -> None:
    with pytest.raises(SafetyViolationError):
        assert_runtime_package([{"relative": "truth/expected_model_ready_weekly.csv"}])


def test_inspect_is_read_only(run_repo: LocalFilesystemRunRepository) -> None:
    initialize_dataset_run(_package_uri(run_repo), requested_run_id="m3cloudro01")
    before = run_repo.load_run("m3cloudro01")
    inspect_dataset_run("m3cloudro01")
    after = run_repo.load_run("m3cloudro01")
    assert after.stage == before.stage
    assert after.updated_at == before.updated_at
    assert after.open_issue_ids == before.open_issue_ids
