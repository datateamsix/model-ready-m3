"""Deterministic Dataset A issue detection. Does not read regression truth."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.contracts import Issue, RemediationClass, Severity
from app.core.model_intent import ModelIntent
from app.tools.io import read_table
from app.tools.profiling import detect_duplicates, detect_grain, looks_like_currency


def detect_phase1_issues(raw_dir: str | Path, intent: ModelIntent) -> list[Issue]:
    root = Path(raw_dir)
    google_path = root / "google_ads_daily.csv"
    meta_path = root / "meta_ads_weekly.csv"
    google = read_table(google_path)
    meta = read_table(meta_path)
    issues: list[Issue] = []

    dups = detect_duplicates(google, ["date", "geo", "campaign"])
    if dups["excess_rows"] > 0:
        issues.append(
            Issue(
                issue_id="MC-A-001",
                rule_id="MR-010",
                severity=Severity.ERROR,
                title="Duplicate Google Ads campaign observation",
                evidence={
                    "file": "google_ads_daily.csv",
                    "duplicate_rows": dups["duplicate_rows"],
                    "duplicate_groups": dups["duplicate_groups"],
                    "excess_rows": dups["excess_rows"],
                },
                remediation_class=RemediationClass.AUTO_SAFE,
                proposed_action={"tool": "remove_exact_duplicates_from_file"},
            )
        )

    google_iso = _iso_ratio(google["date"])
    meta_iso = _iso_ratio(meta["week_start"])
    meta_us = _format_ratio(meta["week_start"], "%m/%d/%Y")
    if google_iso == 1.0 and meta_iso < 1.0 and meta_us == 1.0:
        issues.append(
            Issue(
                issue_id="MC-A-002",
                rule_id="MR-001",
                severity=Severity.ERROR,
                title="Google/Meta date-format mismatch",
                evidence={
                    "google_format": "YYYY-MM-DD",
                    "meta_format": "MM/DD/YYYY",
                    "files": ["google_ads_daily.csv", "meta_ads_weekly.csv"],
                },
                remediation_class=RemediationClass.AUTO_SAFE,
                proposed_action={
                    "tool": "normalize_dates_in_file",
                    "expected_format": "MM/DD/YYYY",
                },
            )
        )

    grain = detect_grain(google, "date")
    if grain["grain"] == "daily" and intent.canonical_time_grain.value == "weekly":
        issues.append(
            Issue(
                issue_id="MC-A-003",
                rule_id="MR-003",
                severity=Severity.ERROR,
                title="Daily Google Ads vs weekly canonical grain",
                evidence={
                    "source_grain": "daily",
                    "target_grain": "weekly",
                    "file": "google_ads_daily.csv",
                },
                remediation_class=RemediationClass.AUTO_SAFE,
                proposed_action={"tool": "aggregate_file_to_week"},
            )
        )

    if looks_like_currency(meta["amount_spent"]):
        issues.append(
            Issue(
                issue_id="MC-A-004",
                rule_id="MR-017",
                severity=Severity.ERROR,
                title="Currency-formatted Meta spend",
                evidence={"file": "meta_ads_weekly.csv", "field": "amount_spent"},
                remediation_class=RemediationClass.AUTO_SAFE,
                proposed_action={
                    "tool": "normalize_numeric_values_in_file",
                    "column": "amount_spent",
                },
            )
        )

    labels = sorted({str(value) for value in meta["channel"].tolist()})
    if len(labels) > 1:
        issues.append(
            Issue(
                issue_id="MC-A-005",
                rule_id="MR-009",
                severity=Severity.ERROR,
                title="Inconsistent Meta channel taxonomy",
                evidence={
                    "file": "meta_ads_weekly.csv",
                    "values": labels,
                    "canonical_channel": "paid_social",
                },
                remediation_class=RemediationClass.AUTO_SAFE,
                proposed_action={"tool": "canonicalize_channel_labels_in_file"},
            )
        )
    return issues


def _iso_ratio(series: pd.Series) -> float:
    parsed = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
    return float((~parsed.isna()).mean()) if len(series) else 0.0


def _format_ratio(series: pd.Series, fmt: str) -> float:
    parsed = pd.to_datetime(series, format=fmt, errors="coerce")
    return float((~parsed.isna()).mean()) if len(series) else 0.0
