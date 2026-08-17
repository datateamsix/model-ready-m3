"""Unit tests for CLOUD_TASKMASTER run-level tools, idempotency, and resumability."""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from app.core.contracts import RemediationClass
from app.core.developer_bootstrap import bind_developer_bootstrap
from app.core.errors import SafetyViolationError
from app.core.legacy_execution import prepare_legacy_dataset_execution
from app.core.run_repository import (
    LocalFilesystemRunRepository,
    assert_runtime_package,
    bind_run_repository,
    reset_run_repository,
)
from app.core.state import RunStage
from app.synthetic.paths import DATASET_A_DIR
from app.tools.run_tools import (
    _allowed_next_actions,
    _scratch_dir,
    apply_safe_remediations,
    complete_dataset_run,
    initialize_dataset_run,
    inspect_dataset_run,
    validate_and_publish_run,
)

DATASET_A_RAW = DATASET_A_DIR / "raw"
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


@contextmanager
def _legacy_run(
    repo: LocalFilesystemRunRepository,
    run_id: str,
    package_uri: str | None = None,
) -> Iterator[None]:
    uri = package_uri or _package_uri(repo)
    with (
        bind_developer_bootstrap(),
        prepare_legacy_dataset_execution(
            package_uri=uri,
            run_id=run_id,
            dataset_id="dataset-a",
        ),
    ):
        yield


def test_initialize_rejects_non_approved_bucket(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    with bind_developer_bootstrap():
        with pytest.raises(SafetyViolationError, match="raw bucket"):
            with prepare_legacy_dataset_execution(
                package_uri="gs://other-bucket/music-center/package/",
                run_id="m3x",
                dataset_id="dataset-a",
            ):
                pass


def test_initialize_rejects_local_paths(run_repo: LocalFilesystemRunRepository) -> None:
    with bind_developer_bootstrap():
        with pytest.raises(SafetyViolationError):
            with prepare_legacy_dataset_execution(
                package_uri=str(DATASET_A_RAW),
                run_id="m3x",
                dataset_id="dataset-a",
            ):
                pass


def test_initialize_requires_execution_context(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    result = initialize_dataset_run()
    assert result["status"] == "FAIL"
    assert result["error_type"] == "ExecutionContextMissingError"


def test_initialize_dataset_a_detects_five_auto_safe_issues(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    with _legacy_run(run_repo, "m3cloudinit01"):
        result = initialize_dataset_run()
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
    with _legacy_run(run_repo, "m3cloudunk01"):
        initialized = initialize_dataset_run()
        assert initialized["status"] == "SUCCESS"
        result = apply_safe_remediations(["NOT-A-REAL-ISSUE"])
        assert result["status"] == "FAIL"
        assert "unknown_issue" in result["error"]


def test_apply_non_auto_safe_issue_fails(run_repo: LocalFilesystemRunRepository) -> None:
    with _legacy_run(run_repo, "m3cloudns01"):
        initialized = initialize_dataset_run()
        assert initialized["status"] == "SUCCESS"
        issues = run_repo.load_issues("m3cloudns01")
        issues[0].remediation_class = RemediationClass.APPROVAL_REQUIRED
        run_repo.save_issues("m3cloudns01", issues)
        result = apply_safe_remediations([issues[0].issue_id])
        assert result["status"] == "FAIL"
        assert "not_auto_safe" in result["error"]


def test_apply_safe_remediations_resolves_selected_dataset_a_issues(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    with _legacy_run(run_repo, "m3cloudrem01"):
        initialized = initialize_dataset_run()
        issue_ids = [item["issue_id"] for item in initialized["issues"]]
        result = apply_safe_remediations(issue_ids)
        assert result["status"] == "SUCCESS"
        assert result["counts"]["resolved"] == 5
        assert result["counts"]["open"] == 0
        assert "validate_and_publish_run" in result["allowed_next_actions"]
        inspected = inspect_dataset_run()
        assert inspected["issue_counts"]["open"] == 0
        assert inspected["stage"] == "REMEDIATING"


def test_validate_with_unresolved_blocker_fails(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    with _legacy_run(run_repo, "m3cloudval01"):
        initialize_dataset_run()
        result = validate_and_publish_run()
        assert result["status"] == "FAIL"
        assert "unresolved_auto_safe" in result["error"]


def test_complete_without_publish_receipt_fails(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    with _legacy_run(run_repo, "m3cloudcmp01"):
        initialize_dataset_run()
        result = complete_dataset_run()
        assert result["status"] == "FAIL"
        assert "publish_receipt.json" in result["error"]


def test_same_run_id_different_fingerprint_fails(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    with _legacy_run(run_repo, "m3cloudfp01"):
        initialize_dataset_run()
    other = run_repo.raw_root / "music-center/mmm-demo/dataset-a/packages/dataset-a-other"
    shutil.copytree(DATASET_A_RAW, other)
    (other / "google_ads_daily.csv").write_text(
        (other / "google_ads_daily.csv").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    other_uri = (
        f"gs://{run_repo.raw_bucket}/music-center/mmm-demo/dataset-a/packages/dataset-a-other/"
    )
    with _legacy_run(run_repo, "m3cloudfp01", package_uri=other_uri):
        result = initialize_dataset_run()
        assert result["status"] == "FAIL"
        assert "different package fingerprint" in result["error"]


def test_completed_run_id_does_not_duplicate_transforms(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    with _legacy_run(run_repo, "m3clouddup01"):
        initialized = initialize_dataset_run()
        apply_safe_remediations([item["issue_id"] for item in initialized["issues"]])
        provenance = run_repo.load_json("m3clouddup01", "provenance.json") or {}
        before = len(provenance.get("records") or [])
        state = run_repo.load_run("m3clouddup01")
        state.stage = RunStage.MODEL_READY
        state.status = "MODEL_READY"
        run_repo.save_run(state)
        result = initialize_dataset_run()
        assert result["status"] == "MODEL_READY"
        assert result["replayed"] is True
        after = run_repo.load_json("m3clouddup01", "provenance.json") or {}
        assert len(after.get("records") or []) == before


def test_initialize_same_in_progress_run_resumes_without_duplicate_provenance(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    with _legacy_run(run_repo, "m3cloudrs01"):
        first = initialize_dataset_run()
        provenance = run_repo.load_json("m3cloudrs01", "provenance.json") or {}
        before = len(provenance.get("records") or [])
        second = initialize_dataset_run()
        assert second["status"] == "SUCCESS"
        assert second["resumed"] is True
        assert second["run_id"] == first["run_id"]
        after = run_repo.load_json("m3cloudrs01", "provenance.json") or {}
        assert len(after.get("records") or []) == before


def test_run_survives_destroyed_local_workspace(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    with _legacy_run(run_repo, "m3cloudmem01"):
        initialized = initialize_dataset_run()
        scratch = _scratch_dir("m3cloudmem01")
        if scratch.exists():
            shutil.rmtree(scratch)
        inspected = inspect_dataset_run()
        assert inspected["status"] == "SUCCESS"
        assert inspected["issue_counts"]["detected"] == 5
        result = apply_safe_remediations(
            [item["issue_id"] for item in initialized["issues"]]
        )
        assert result["status"] == "SUCCESS"
        assert result["counts"]["resolved"] == 5
        assert result["counts"]["open"] == 0


def test_initialize_rejects_regression_truth_file(
    run_repo: LocalFilesystemRunRepository,
) -> None:
    staged = run_repo.raw_root / PACKAGE_REL
    (staged / "expected_model_ready_weekly.csv").write_text("nope\n", encoding="utf-8")
    with _legacy_run(run_repo, "m3cloudtr01"):
        result = initialize_dataset_run()
        assert result["status"] == "FAIL"


def test_assert_runtime_package_rejects_truth_paths() -> None:
    with pytest.raises(SafetyViolationError):
        assert_runtime_package([{"relative": "truth/expected_model_ready_weekly.csv"}])


def test_publishing_allows_eda_not_completion() -> None:
    actions = _allowed_next_actions(RunStage.PUBLISHING, [])
    assert "run_meridian_eda" in actions
    assert "complete_dataset_run" not in actions


def test_exploring_with_passing_eda_allows_completion(tmp_path: Path) -> None:
    html = tmp_path / "meridian_eda_report.html"
    html.write_text("<html>official</html>", encoding="utf-8")
    receipt = tmp_path / "meridian_eda_receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "run_id": "run-eda",
                "html_report_uri": "gs://bucket/eda/meridian_eda_report.html",
                "posterior_sampling": False,
                "model_fitted": False,
                "findings": [
                    {
                        "finding_id": "KPI_INVARIABILITY.OVERALL.VARIABILITY.INFO.01",
                        "check_type": "KPI_INVARIABILITY",
                        "report_category": "individual_variables",
                        "severity": "INFO",
                        "finding_cause": "NONE",
                        "explanation": "KPI varies enough to model.",
                        "analysis_level": "OVERALL",
                    }
                ],
                "severity_summary": {
                    "error_count": 0,
                    "attention_count": 0,
                    "info_count": 1,
                    "max_severity": "INFO",
                },
                "status": "EDA_COMPLETE",
                "model_spec": {
                    "source": "MERIDIAN_DEFAULT",
                    "knots": "MERIDIAN_DEFAULT",
                    "n_knots": "MERIDIAN_DEFAULT",
                    "n_time": 10,
                    "enable_aks": False,
                    "approved_for_final_modeling": False,
                },
                "data_adequacy": {
                    "n_geos": 2,
                    "n_times": 10,
                    "n_knots": 10,
                    "n_controls": 3,
                    "n_treatments": 4,
                    "n_parameters": 20,
                    "n_data_points": 100,
                    "ratio": 0.2,
                },
            }
        ),
        encoding="utf-8",
    )

    class _Coordinator:
        eda_html_path = html
        eda_receipt_path = receipt

        def _load_json_if_exists(self, path):
            return json.loads(path.read_text(encoding="utf-8"))

    actions = _allowed_next_actions(
        RunStage.EXPLORING, [], coordinator=_Coordinator()  # type: ignore[arg-type]
    )
    assert "complete_dataset_run" in actions
    assert "run_meridian_eda" not in actions


def test_inspect_is_read_only(run_repo: LocalFilesystemRunRepository) -> None:
    with _legacy_run(run_repo, "m3cloudro01"):
        initialize_dataset_run()
        before = run_repo.load_run("m3cloudro01")
        inspect_dataset_run()
        after = run_repo.load_run("m3cloudro01")
        assert after.stage == before.stage
        assert after.updated_at == before.updated_at
        assert after.open_issue_ids == before.open_issue_ids
