"""Deterministic readiness and publish-gate validation helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class CheckResult:
    rule_id: str
    passed: bool
    message: str


def validate_no_missing(frame: pd.DataFrame, required_columns: list[str]) -> CheckResult:
    missing = {column: int(frame[column].isna().sum()) for column in required_columns}
    failed = {column: count for column, count in missing.items() if count > 0}
    return CheckResult(
        rule_id="MR-002",
        passed=not failed,
        message="No unsupported missing values." if not failed else f"Missing values: {failed}",
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
    )


def all_blocking_checks_pass(results: list[CheckResult]) -> bool:
    return all(result.passed for result in results)
