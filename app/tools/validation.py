"""Deterministic readiness and publish-gate validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.contracts import ReadinessCheck, ReadinessReceipt
from app.core.model_intent import MODEL_READY_COLUMNS, ModelIntent
from app.tools.io import read_table
from app.tools.profiling import detect_grain
from app.tools.safety import BUILTIN_NON_SUMMABLE


@dataclass(frozen=True, slots=True)
class CheckResult:
    rule_id: str
    passed: bool
    message: str
    evidence: dict[str, Any] | None = None


def validate_no_missing(frame: pd.DataFrame, required_columns: list[str]) -> CheckResult:
    missing = {column: int(frame[column].isna().sum()) for column in required_columns}
    failed = {column: count for column, count in missing.items() if count > 0}
    return CheckResult(
        rule_id="MR-002",
        passed=not failed,
        message="No unsupported missing values." if not failed else f"Missing values: {failed}",
        evidence={"missing": missing},
    )


def validate_unique_grain(frame: pd.DataFrame, grain_columns: list[str]) -> CheckResult:
    duplicates = int(frame.duplicated(subset=grain_columns).sum())
    return CheckResult(
        rule_id="MR-010",
        passed=duplicates == 0,
        message=(
            "Canonical grain is unique."
            if duplicates == 0
            else f"Found {duplicates} duplicate observations at canonical grain."
        ),
        evidence={"duplicate_observations": duplicates, "grain_columns": grain_columns},
    )


def all_blocking_checks_pass(results: list[CheckResult]) -> bool:
    return all(result.passed for result in results)


def validate_iso_dates(frame: pd.DataFrame, column: str) -> CheckResult:
    parsed = pd.to_datetime(frame[column], format="%Y-%m-%d", errors="coerce")
    invalid = int(parsed.isna().sum())
    return CheckResult(
        rule_id="MR-001",
        passed=invalid == 0,
        message=(
            "Time values are yyyy-mm-dd."
            if invalid == 0
            else f"{invalid} values in {column} are not yyyy-mm-dd."
        ),
        evidence={"invalid_count": invalid, "column": column},
    )


def validate_weekly_grain(frame: pd.DataFrame, column: str) -> CheckResult:
    grain = detect_grain(frame, column)
    passed = grain["grain"] == "weekly"
    return CheckResult(
        rule_id="MR-003",
        passed=passed,
        message="Temporal grain is weekly."
        if passed
        else f"Grain is {grain['grain']}, expected weekly.",
        evidence=grain,
    )


def validate_non_summable_absent(frame: pd.DataFrame) -> CheckResult:
    present = [column for column in frame.columns if column.lower() in BUILTIN_NON_SUMMABLE]
    return CheckResult(
        rule_id="MR-006",
        passed=not present,
        message=(
            "No non-summable rates used as model execution inputs."
            if not present
            else f"Non-summable columns present: {present}"
        ),
        evidence={"non_summable_columns": present},
    )


def validate_channel_aggregation(frame: pd.DataFrame, intent: ModelIntent) -> CheckResult:
    missing: list[str] = []
    for channel in intent.paid_media:
        for column in (channel.impressions_column, channel.spend_column):
            if column not in frame.columns:
                missing.append(column)
    return CheckResult(
        rule_id="MR-009",
        passed=not missing,
        message="Modeled channel columns are present."
        if not missing
        else f"Missing channel columns: {missing}",
        evidence={"missing": missing},
    )


def validate_numeric_spend(frame: pd.DataFrame, intent: ModelIntent) -> CheckResult:
    non_numeric: list[str] = []
    for channel in intent.paid_media:
        column = channel.spend_column
        if column not in frame.columns:
            non_numeric.append(column)
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if int(numeric.isna().sum()) != 0:
            non_numeric.append(column)
    return CheckResult(
        rule_id="MR-017",
        passed=not non_numeric,
        message="Spend columns are numeric."
        if not non_numeric
        else f"Non-numeric spend: {non_numeric}",
        evidence={"non_numeric": non_numeric},
    )


def validate_provenance_complete(
    manifest: dict[str, Any], required_tools: list[str]
) -> CheckResult:
    transforms = manifest.get("transforms") or manifest.get("records") or []
    tools = {str(item.get("tool")) for item in transforms}
    missing = [tool for tool in required_tools if tool not in tools]
    return CheckResult(
        rule_id="MR-018",
        passed=not missing,
        message="Provenance covers required transforms."
        if not missing
        else f"Missing provenance: {missing}",
        evidence={"present_tools": sorted(tools), "missing_tools": missing},
    )


REQUIRED_DATASET_A_TOOLS = [
    "remove_exact_duplicates",
    "normalize_dates",
    "normalize_numeric_values",
    "canonicalize_channel_labels",
    "aggregate_campaign_to_channel",
    "aggregate_to_week",
    "build_model_ready_frame",
]


def validate_model_ready_artifact(
    frame: pd.DataFrame,
    *,
    run_id: str,
    intent: ModelIntent,
    provenance_manifest: dict[str, Any],
    artifact_uri: str | None = None,
) -> ReadinessReceipt:
    results = [
        validate_iso_dates(frame, "time"),
        validate_no_missing(frame, MODEL_READY_COLUMNS),
        validate_weekly_grain(frame, "time"),
        validate_non_summable_absent(frame),
        validate_channel_aggregation(frame, intent),
        validate_unique_grain(frame, ["time", "geo"]),
        validate_numeric_spend(frame, intent),
        validate_provenance_complete(provenance_manifest, REQUIRED_DATASET_A_TOOLS),
    ]
    checks = [
        ReadinessCheck(
            rule_id=item.rule_id,
            passed=item.passed,
            evidence={"message": item.message, **(item.evidence or {})},
        )
        for item in results
    ]
    passed = all(check.passed for check in checks)
    return ReadinessReceipt(
        run_id=run_id,
        status="PASS" if passed else "FAIL",
        blocking_checks_passed=passed,
        checks=checks,
        artifact_uri=artifact_uri,
    )


def readiness_from_path(
    path: str | Path,
    *,
    run_id: str,
    intent: ModelIntent,
    provenance_manifest: dict[str, Any],
) -> ReadinessReceipt:
    frame = read_table(path)
    return validate_model_ready_artifact(
        frame,
        run_id=run_id,
        intent=intent,
        provenance_manifest=provenance_manifest,
        artifact_uri=str(path),
    )
