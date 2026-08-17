"""Provider-agnostic coordinator qualification for Datasets A, B, and C."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.contracts import RemediationClass
from app.core.errors import AssignmentInitError, SafetyViolationError
from app.core.model_intent import (
    DATASET_A_MODEL_INTENT,
    DATASET_C_MODEL_INTENT,
    MODEL_READY_COLUMNS,
    model_ready_columns,
)
from app.core.run_coordinator import RunCoordinator
from app.core.run_repository import assert_runtime_package
from app.core.source_inventory import (
    CanonicalRole,
    InitFailureReason,
    SourceDescriptor,
    assert_required_sources_present,
    inventory_assignment_sources,
)
from app.core.state import RunStage
from app.mel.assignment import resolve_assignment_identity
from app.mel.holdout import MelError, reject_holdout_training
from app.mel.models import DatasetRole
from app.response.run_bundle import build_run_presentation_bundle
from app.synthetic.paths import DATASET_A_DIR, DATASET_B_DIR, DATASET_C_DIR
from app.tools.fingerprints import content_fingerprint
from app.tools.io import read_table
from app.tools.issues import detect_assignment_issues
from app.tools.model_frame import coerce_model_frame_types
from app.tools.provenance import FRAME_SOURCE_ROLES, frame_source_roles
from app.tools.safety import assert_summable_columns
from app.tools.source_adapters import repair_source_file
from tests.unit.test_dataset_c_generator import DATASET_C_PACKAGE_FP

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "app"
EXPECTED_CONTRACT_NAMES = (
    "expected_issues.json",
    "expected_safe_actions.json",
    "expected_forbidden_actions.json",
    "expected_semantic_triggers.json",
)
COORDINATOR_PATHS = (
    APP_ROOT / "core" / "run_coordinator.py",
    APP_ROOT / "core" / "source_inventory.py",
    APP_ROOT / "tools" / "issues.py",
    APP_ROOT / "tools" / "source_adapters.py",
    APP_ROOT / "tools" / "model_frame.py",
)
FORBIDDEN_BRANCHES = (
    'dataset_id == "dataset_a"',
    'dataset_id == "dataset_b"',
    'dataset_id == "dataset_c"',
    'business_name == "Music Center"',
    'business_name == "Stride & Field"',
    'business_name == "Summit & Pine"',
)


def test_dataset_a_columns_match_golden_contract() -> None:
    assert model_ready_columns(DATASET_A_MODEL_INTENT) == MODEL_READY_COLUMNS
    assert frame_source_roles(DATASET_A_MODEL_INTENT) == FRAME_SOURCE_ROLES


def test_dataset_a_inventory_is_manifest_driven() -> None:
    inventory = inventory_assignment_sources(DATASET_A_DIR / "raw", DATASET_A_MODEL_INTENT)
    assert_required_sources_present(inventory)
    providers = set(inventory.providers)
    assert "google_ads" in providers
    assert "meta_ads" in providers
    assert inventory.missing_required_sources == []
    roles = {item.canonical_role for item in inventory.sources}
    assert CanonicalRole.PAID_MEDIA in roles
    assert CanonicalRole.KPI in roles


def test_dataset_a_detects_golden_issue_ids() -> None:
    issues = detect_assignment_issues(DATASET_A_DIR / "raw", DATASET_A_MODEL_INTENT)
    assert {issue.issue_id for issue in issues} == {
        "MC-A-001",
        "MC-A-002",
        "MC-A-003",
        "MC-A-004",
        "MC-A-005",
    }
    assert all(issue.remediation_class is RemediationClass.AUTO_SAFE for issue in issues)


def test_dataset_b_initialize_does_not_require_music_center_files(tmp_path: Path) -> None:
    coordinator = RunCoordinator(
        DATASET_B_DIR / "raw",
        tmp_path / "artifacts",
        dataset_id="dataset_b_stride_and_field",
        dataset_role=DatasetRole.LEARNING_EVIDENCE.value,
    )
    coordinator.prepare_workspace()
    coordinator.profile_and_map()
    coordinator.assess()
    assert coordinator.inventory is not None
    names = {Path(item.relative_path).name for item in coordinator.inventory.sources}
    assert "google_ads_daily.csv" not in names
    assert "controls_weekly.csv" not in names
    assert "microsoft_ads_daily.csv" in names
    assert "tiktok_ads_daily.csv" in names
    assert "amazon_ads_weekly.csv" in names
    assert coordinator.inventory.missing_required_sources == []
    assert {item.provider_id for item in coordinator.inventory.sources} >= {
        "microsoft_ads",
        "tiktok_ads",
        "amazon_ads",
        "shopify",
        "ga4",
        "klaviyo",
    }
    assert coordinator.stage is RunStage.ASSESSING
    assert all(
        "google_ads_daily.csv" not in str(issue.evidence)
        or issue.evidence.get("file") != "google_ads_daily.csv"
        for issue in coordinator.issues
    )


def test_dataset_c_initialize_preserves_holdout_role(tmp_path: Path) -> None:
    coordinator = RunCoordinator(
        DATASET_C_DIR / "raw",
        tmp_path / "artifacts",
        dataset_id="dataset_c_summit_and_pine",
        dataset_role=DatasetRole.SEALED_HOLDOUT.value,
        qualification_mode="HOLDOUT_QUALIFICATION_ONLY",
    )
    coordinator.prepare_workspace()
    coordinator.profile_and_map()
    coordinator.assess()
    assert coordinator.dataset_role == DatasetRole.SEALED_HOLDOUT.value
    assert coordinator.qualification_mode == "HOLDOUT_QUALIFICATION_ONLY"
    assert coordinator.inventory is not None
    names = {Path(item.relative_path).name for item in coordinator.inventory.sources}
    assert "pms_bookings_weekly.csv" in names
    assert "stripe_weekly.csv" in names
    assert "pinterest_ads_daily.csv" in names
    assert coordinator.inventory.missing_required_sources == []
    providers = {item.provider_id for item in coordinator.inventory.sources}
    assert "synthetic_pms" in providers
    assert "stripe" in providers
    assert "pinterest_ads" in providers


def test_dataset_c_package_fingerprint_unchanged() -> None:
    sealed = json.loads((DATASET_C_DIR / "package_manifest.json").read_text(encoding="utf-8"))
    assert sealed["package_fingerprint"] == DATASET_C_PACKAGE_FP


def test_missing_required_source_fails_closed(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "model_intent.json").write_text(
        (DATASET_A_DIR / "raw" / "model_intent.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    inventory = inventory_assignment_sources(raw, DATASET_A_MODEL_INTENT)
    try:
        assert_required_sources_present(inventory)
        raise AssertionError("expected missing required source")
    except AssignmentInitError as exc:
        assert exc.reason == InitFailureReason.MISSING_REQUIRED_SOURCE.value


def test_optional_inactivity_source_may_be_absent() -> None:
    inventory = inventory_assignment_sources(DATASET_A_DIR / "raw", DATASET_A_MODEL_INTENT)
    assert_required_sources_present(inventory)
    assert not any(
        item.canonical_role is CanonicalRole.INACTIVITY_EVIDENCE for item in inventory.sources
    )


def test_assert_runtime_package_requires_intent_not_music_center_filenames() -> None:
    names = assert_runtime_package(
        [{"relative": "model_intent.json"}, {"relative": "microsoft_ads_daily.csv"}]
    )
    assert "model_intent.json" in names
    assert "microsoft_ads_daily.csv" in names


def test_runtime_does_not_read_expected_contracts() -> None:
    leaked: list[str] = []
    runtime_paths = (
        *COORDINATOR_PATHS,
        APP_ROOT / "tools" / "run_tools.py",
        APP_ROOT / "tools" / "adk_tools.py",
        APP_ROOT / "tools" / "validation.py",
        APP_ROOT / "tools" / "remediation.py",
    )
    for path in runtime_paths:
        text = path.read_text(encoding="utf-8")
        for name in EXPECTED_CONTRACT_NAMES:
            if name in text and path.name != "source_inventory.py":
                leaked.append(f"{path.relative_to(REPO_ROOT)}:{name}")
    assert leaked == []


def test_core_coordinator_has_no_business_identity_branches() -> None:
    hits: list[str] = []
    for path in COORDINATOR_PATHS:
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_BRANCHES:
            if pattern in text:
                hits.append(f"{path.name}:{pattern}")
    assert hits == []


def test_dataset_a_in_memory_fingerprint_uses_parity_normalization() -> None:
    frame = read_table(DATASET_A_DIR / "truth" / "expected_model_ready_weekly.csv")
    coerced = coerce_model_frame_types(frame)
    left = content_fingerprint(
        coerced, columns=list(MODEL_READY_COLUMNS), key_columns=["time", "geo"]
    )
    right = content_fingerprint(
        frame, columns=list(MODEL_READY_COLUMNS), key_columns=["time", "geo"]
    )
    assert left == right


def test_holdout_role_is_not_learning_eligible() -> None:
    assert DatasetRole.SEALED_HOLDOUT.value == "SEALED_HOLDOUT"
    assert DatasetRole.SEALED_HOLDOUT is not DatasetRole.LEARNING_EVIDENCE
    assert DatasetRole.SEALED_HOLDOUT is not DatasetRole.TRAINING_EXPERIENCE


def test_dataset_b_run_local_stops_for_user_required(tmp_path: Path) -> None:
    coordinator = RunCoordinator(
        DATASET_B_DIR / "raw",
        tmp_path / "artifacts",
        dataset_id="dataset_b_stride_and_field",
        dataset_role=DatasetRole.LEARNING_EVIDENCE.value,
    )
    summary = coordinator.run_local()
    assert coordinator.stage is RunStage.WAITING_FOR_APPROVAL
    assert summary["final_state"] == "WAITING_FOR_APPROVAL"
    assert summary["detected_issue_count"] >= 1
    assert any(
        issue.remediation_class is RemediationClass.APPROVAL_REQUIRED
        for issue in coordinator.issues
    )
    unknown = [
        issue
        for issue in coordinator.issues
        if str(issue.evidence.get("zero_fill_forbidden")) == "True"
        or issue.evidence.get("zero_fill_forbidden") is True
    ]
    assert unknown
    assert coordinator.inventory is not None
    assert "google_ads_daily.csv" not in {
        Path(item.relative_path).name for item in coordinator.inventory.sources
    }


def test_dataset_c_run_local_holdout_qualification(tmp_path: Path) -> None:
    coordinator = RunCoordinator(
        DATASET_C_DIR / "raw",
        tmp_path / "artifacts",
        dataset_id="dataset_c_summit_and_pine",
        dataset_role=DatasetRole.SEALED_HOLDOUT.value,
        qualification_mode="HOLDOUT_QUALIFICATION_ONLY",
    )
    summary = coordinator.run_local()
    assert coordinator.dataset_role == DatasetRole.SEALED_HOLDOUT.value
    assert coordinator.qualification_mode == "HOLDOUT_QUALIFICATION_ONLY"
    assert summary["final_state"] in {"WAITING_FOR_APPROVAL", "VALIDATING", "FAILED"}
    assert coordinator.inventory is not None
    names = {Path(item.relative_path).name for item in coordinator.inventory.sources}
    assert "google_ads_daily.csv" in names
    assert "controls_weekly.csv" not in names
    assert "pms_bookings_weekly.csv" in names


def test_unknown_required_provider_fails_closed() -> None:
    inventory = inventory_assignment_sources(
        DATASET_A_DIR / "raw", DATASET_A_MODEL_INTENT
    )
    inventory.missing_required_sources = []
    inventory.sources.append(
        SourceDescriptor(
            source_id="unknown_ads",
            provider_id="not_a_real_provider_xyz",
            relative_path="not_a_real_provider_xyz.csv",
            canonical_role=CanonicalRole.PAID_MEDIA,
            required=True,
            supported=True,
        )
    )
    try:
        assert_required_sources_present(inventory)
        raise AssertionError("expected unsupported provider")
    except AssignmentInitError as exc:
        assert exc.reason == InitFailureReason.UNSUPPORTED_PROVIDER.value


def test_unsupported_report_type_fails_closed() -> None:
    inventory = inventory_assignment_sources(
        DATASET_A_DIR / "raw", DATASET_A_MODEL_INTENT
    )
    inventory.missing_required_sources = []
    paid = next(
        item
        for item in inventory.sources
        if item.canonical_role is CanonicalRole.PAID_MEDIA
    )
    paid.supported = False
    paid.required = True
    paid.report_type = "unknown_report"
    try:
        assert_required_sources_present(inventory)
        raise AssertionError("expected unsupported report type")
    except AssignmentInitError as exc:
        assert exc.reason == InitFailureReason.UNSUPPORTED_REPORT_TYPE.value


def test_ambiguous_paid_channel_does_not_guess(tmp_path: Path) -> None:
    source = tmp_path / "meta_ads_weekly.csv"
    source.write_text(
        "week_start,geo,impressions,amount_spent\n2024-01-01,NE,10,1.00\n",
        encoding="utf-8",
    )
    descriptor = SourceDescriptor(
        source_id="meta_ads_weekly",
        provider_id="meta_ads",
        relative_path="meta_ads_weekly.csv",
        date_field="week_start",
        canonical_role=CanonicalRole.PAID_MEDIA,
        required=True,
        channel_hint=None,
    )
    try:
        repair_source_file(
            source_path=str(source),
            descriptor=descriptor,
            intent=DATASET_C_MODEL_INTENT,
            transform_dir=tmp_path / "tx",
        )
        raise AssertionError("expected ambiguous channel")
    except AssignmentInitError as exc:
        assert exc.reason == InitFailureReason.AMBIGUOUS_SOURCE_ROLE.value


def test_non_summable_metric_cannot_be_aggregated() -> None:
    try:
        assert_summable_columns(["impressions", "ctr"], "meta_ads")
        raise AssertionError("expected non-summable rejection")
    except SafetyViolationError:
        pass


def test_sealed_holdout_cannot_become_learning_evidence() -> None:
    class _Holdout:
        holdout = True
        dataset_role = DatasetRole.SEALED_HOLDOUT

    try:
        reject_holdout_training(_Holdout(), action="candidate extraction")
        raise AssertionError("expected holdout firewall")
    except MelError as exc:
        assert "REJECTED_HOLDOUT_INPUT" in str(exc)


def test_catalog_resolves_holdout_qualification_mode() -> None:
    dataset_id, role, mode = resolve_assignment_identity(
        dataset_id="dataset_c_summit_and_pine"
    )
    assert dataset_id == "dataset_c_summit_and_pine"
    assert role == DatasetRole.SEALED_HOLDOUT.value
    assert mode == "HOLDOUT_QUALIFICATION_ONLY"


def test_presentation_bundle_does_not_compute_model_ready() -> None:
    bundle = build_run_presentation_bundle(
        summary={
            "final_state": "WAITING_FOR_APPROVAL",
            "detected_issue_count": 1,
            "run_id": "m3example",
        },
        issues=[
            {
                "issue_id": "MR-000",
                "title": "User required",
                "rule_id": "MR-000",
                "status": "OPEN",
                "remediation_class": RemediationClass.APPROVAL_REQUIRED.value,
                "proposed_action": {"tool": "none"},
            }
        ],
    )
    assert bundle["contract"] == "RunPresentationBundle"
    assert bundle["findings"]
    assert bundle["actions"]
    assert bundle["model_ready"]["computed_by_presentation"] is False
    assert bundle["model_ready"]["terminal"] == "WAITING_FOR_APPROVAL"
