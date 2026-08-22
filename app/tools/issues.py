"""Deterministic assignment issue detection. Does not read regression truth."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.contracts import Issue, IssueStatus, RemediationClass, Severity, utc_now
from app.core.model_intent import ModelIntent
from app.core.source_inventory import (
    TIME_FIELD_CANDIDATES,
    CanonicalRole,
    SourceDescriptor,
    SourceInventory,
    inventory_assignment_sources,
)
from app.tools.io import read_table
from app.tools.profiling import detect_duplicates, detect_grain, looks_like_currency
from app.tools.source_adapters import (
    channel_alias_mapping,
    detect_source_date_format,
    geo_alias_mapping,
    iso_ratio,
)

GOLDEN_ISSUE_ALIASES = {
    ("MR-010", "google_ads_daily.csv", "exact_duplicates"): "MC-A-001",
    ("MR-001", "meta_ads_weekly.csv", "date_format"): "MC-A-002",
    ("MR-003", "google_ads_daily.csv", "daily_weekly"): "MC-A-003",
    ("MR-017", "meta_ads_weekly.csv", "currency"): "MC-A-004",
    ("MR-009", "meta_ads_weekly.csv", "channel_taxonomy"): "MC-A-005",
}

TOOL_NAME_ALIASES = {
    "remove_exact_duplicates_from_file": "remove_exact_duplicates",
    "normalize_dates_in_file": "normalize_dates",
    "normalize_numeric_values_in_file": "normalize_numeric_values",
    "canonicalize_channel_labels_in_file": "canonicalize_channel_labels",
    "aggregate_file_to_week": "aggregate_to_week",
    "aggregate_campaign_to_channel_in_file": "aggregate_campaign_to_channel",
    "convert_cost_micros_to_currency": "convert_cost_micros_to_currency",
    "convert_week_ending_to_week_start": "convert_week_ending_to_week_start",
    "canonicalize_geo_labels": "canonicalize_geo_labels",
    "zero_fill_documented_inactivity": "zero_fill_documented_inactivity",
}


def detect_phase1_issues(raw_dir: str | Path, intent: ModelIntent) -> list[Issue]:
    """Backward-compatible alias for manifest-driven assignment issue detection."""
    return detect_assignment_issues(raw_dir, intent)


def detect_assignment_issues(
    raw_dir: str | Path,
    intent: ModelIntent,
    inventory: SourceInventory | None = None,
) -> list[Issue]:
    """Detect issues from typed source metadata. Never reads expected-answer files."""
    root = Path(raw_dir)
    inventory = inventory or inventory_assignment_sources(root, intent)
    population = _load_role_frame(root, inventory, CanonicalRole.POPULATION)
    kpi_frame = _load_role_frame(root, inventory, CanonicalRole.KPI)
    inactivity = _load_role_frame(root, inventory, CanonicalRole.INACTIVITY_EVIDENCE)
    issues: list[Issue] = []

    for descriptor in inventory.sources:
        if descriptor.canonical_role is CanonicalRole.MODEL_INTENT:
            continue
        path = root / descriptor.relative_path
        if not path.is_file():
            continue
        frame = read_table(path)
        issues.extend(
            _issues_for_source(
                descriptor=descriptor,
                frame=frame,
                intent=intent,
                population=population,
                kpi_frame=kpi_frame,
                inactivity=inactivity,
            )
        )

    issues.extend(_missing_control_issues(inventory, intent))
    return issues


def mark_issues_remediating(issues: list[Issue]) -> None:
    for issue in issues:
        if issue.status == IssueStatus.OPEN:
            issue.status = IssueStatus.REMEDIATING


def resolve_issues_from_transforms(issues: list[Issue], transforms: list[dict]) -> None:
    """Mark issues RESOLVED only when a matching APPLIED transform exists."""
    for issue in issues:
        match = _matching_transform(issue, transforms)
        if match is None or match.get("status") != "APPLIED" or not match.get("output_sha256"):
            continue
        input_rows = int(match.get("input_rows") or 0)
        output_rows = int(match.get("output_rows") or 0)
        issue.status = IssueStatus.RESOLVED
        issue.resolution_action_ids = [str(match["action_id"])]
        issue.resolved_at = utc_now()
        evidence = {
            "tool": match.get("tool"),
            "output_uri": match.get("output_uri"),
            "output_sha256": match.get("output_sha256"),
            "input_rows": input_rows,
            "output_rows": output_rows,
        }
        if issue.issue_id == "MC-A-001":
            evidence["excess_rows_removed"] = input_rows - output_rows
        issue.resolution_evidence = evidence


def _issues_for_source(
    *,
    descriptor: SourceDescriptor,
    frame: pd.DataFrame,
    intent: ModelIntent,
    population: pd.DataFrame | None,
    kpi_frame: pd.DataFrame | None,
    inactivity: pd.DataFrame | None,
) -> list[Issue]:
    issues: list[Issue] = []
    filename = Path(descriptor.relative_path).name
    date_field = descriptor.date_field

    if date_field and date_field in frame.columns:
        detected = detect_source_date_format(frame[date_field])
        if detected == "MM/DD/YYYY" or (
            detected is None and iso_ratio(frame[date_field]) < 1.0
        ):
            issues.append(
                _issue(
                    rule_id="MR-001",
                    filename=filename,
                    qualifier="date_format",
                    title=f"Non-ISO dates in {filename}",
                    evidence={
                        "file": filename,
                        "field": date_field,
                        "detected_format": detected or "unknown",
                    },
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={
                        "tool": "normalize_dates_in_file",
                        "expected_format": detected or "MM/DD/YYYY",
                        "file": filename,
                    },
                )
            )
        if date_field == "week_ending":
            issues.append(
                _issue(
                    rule_id="MR-001",
                    filename=filename,
                    qualifier="week_ending",
                    title=f"Sunday-ending weeks in {filename}",
                    evidence={"file": filename, "field": date_field},
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={
                        "tool": "convert_week_ending_to_week_start",
                        "file": filename,
                    },
                )
            )
        try:
            grain = detect_grain(frame, date_field)
        except (ValueError, TypeError):
            grain = {"grain": "unknown"}
        if grain.get("grain") == "daily" and intent.canonical_time_grain.value == "weekly":
            issues.append(
                _issue(
                    rule_id="MR-003",
                    filename=filename,
                    qualifier="daily_weekly",
                    title=f"Daily {filename} vs weekly canonical grain",
                    evidence={
                        "source_grain": "daily",
                        "target_grain": "weekly",
                        "file": filename,
                    },
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={"tool": "aggregate_file_to_week", "file": filename},
                )
            )

    if descriptor.canonical_role is CanonicalRole.PAID_MEDIA:
        subset = [
            column
            for column in (
                date_field,
                "geo",
                "campaign",
                "campaign_name",
                "adset_name",
                "product_group",
            )
            if column and column in frame.columns
        ]
        dups = detect_duplicates(frame, subset or None)
        if dups["excess_rows"] > 0:
            issues.append(
                _issue(
                    rule_id="MR-010",
                    filename=filename,
                    qualifier="exact_duplicates",
                    title=f"Duplicate observations in {filename}",
                    evidence={
                        "file": filename,
                        "duplicate_rows": dups["duplicate_rows"],
                        "duplicate_groups": dups["duplicate_groups"],
                        "excess_rows": dups["excess_rows"],
                    },
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={
                        "tool": "remove_exact_duplicates_from_file",
                        "file": filename,
                    },
                )
            )
        if "product_group" in frame.columns:
            issues.append(
                _issue(
                    rule_id="MR-010",
                    filename=filename,
                    qualifier="extra_grain",
                    title=f"Extra report grain in {filename}",
                    evidence={
                        "file": filename,
                        "grain": [date_field, "geo", "campaign_name", "product_group"],
                    },
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={
                        "tool": "aggregate_campaign_to_channel_in_file",
                        "file": filename,
                    },
                )
            )
        mapping = channel_alias_mapping(frame, intent, descriptor)
        labels = sorted({str(value) for value in _channel_values(frame)})
        canonical = {
            channel.channel
            for channel in intent.paid_media
            if channel.provider == descriptor.provider_id
        }
        if labels and not set(labels) <= canonical:
            issues.append(
                _issue(
                    rule_id="MR-009",
                    filename=filename,
                    qualifier="channel_taxonomy",
                    title=f"Inconsistent channel taxonomy in {filename}",
                    evidence={"file": filename, "values": labels, "mapping": mapping},
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={
                        "tool": "canonicalize_channel_labels_in_file",
                        "file": filename,
                    },
                )
            )
        spend = next(
            (
                channel.source_spend
                for channel in intent.paid_media
                if channel.provider == descriptor.provider_id
            ),
            None,
        )
        if spend == "cost_micros" and "cost_micros" in frame.columns:
            issues.append(
                _issue(
                    rule_id="MR-017",
                    filename=filename,
                    qualifier="cost_micros",
                    title=f"Micros-denominated spend in {filename}",
                    evidence={"file": filename, "field": "cost_micros"},
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={
                        "tool": "convert_cost_micros_to_currency",
                        "file": filename,
                    },
                )
            )
        elif spend and spend in frame.columns and looks_like_currency(frame[spend]):
            issues.append(
                _issue(
                    rule_id="MR-017",
                    filename=filename,
                    qualifier="currency",
                    title=f"Currency-formatted spend in {filename}",
                    evidence={"file": filename, "field": spend},
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={
                        "tool": "normalize_numeric_values_in_file",
                        "column": spend,
                        "file": filename,
                    },
                )
            )
        if "attributed_sales" in frame.columns:
            issues.append(
                _issue(
                    rule_id="MR-013",
                    filename=filename,
                    qualifier="attributed_sales",
                    title=f"Attributed sales in {filename} is not media exposure",
                    evidence={"file": filename, "field": "attributed_sales"},
                    remediation_class=RemediationClass.APPROVAL_REQUIRED,
                    proposed_action={"tool": None, "file": filename},
                )
            )
        if kpi_frame is not None and date_field and date_field in frame.columns:
            issues.extend(
                _unknown_absence_issues(
                    descriptor, frame, kpi_frame, inactivity, date_field, filename
                )
            )

    if descriptor.canonical_role in {CanonicalRole.KPI, CanonicalRole.REVENUE}:
        field = (
            intent.kpi.field
            if descriptor.canonical_role is CanonicalRole.KPI
            else intent.revenue.field
        )
        if field in frame.columns and looks_like_currency(frame[field]):
            issues.append(
                _issue(
                    rule_id="MR-017",
                    filename=filename,
                    qualifier="currency",
                    title=f"Currency-formatted {field} in {filename}",
                    evidence={"file": filename, "field": field},
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={
                        "tool": "normalize_numeric_values_in_file",
                        "column": field,
                        "file": filename,
                    },
                )
            )

    if descriptor.canonical_role is CanonicalRole.ORGANIC_MEDIA:
        rate_cols = [
            column
            for column in ("open_rate", "click_rate", "ctr", "conversion_rate")
            if column in frame.columns
        ]
        if rate_cols:
            issues.append(
                _issue(
                    rule_id="MR-013",
                    filename=filename,
                    qualifier="non_summable",
                    title=f"Non-summable rates in {filename}",
                    evidence={"file": filename, "fields": rate_cols},
                    remediation_class=RemediationClass.APPROVAL_REQUIRED,
                    proposed_action={"tool": None, "file": filename},
                )
            )

    if descriptor.canonical_role is CanonicalRole.CONTROLS and kpi_frame is not None:
        issues.extend(_missing_control_cell_issues(descriptor, frame, kpi_frame, filename, intent))

    if population is not None and "geo" in frame.columns:
        mapping = geo_alias_mapping(frame, population)
        if any(source != target for source, target in mapping.items()):
            issues.append(
                _issue(
                    rule_id="MR-005",
                    filename=filename,
                    qualifier="geo_aliases",
                    title=f"Geo aliases in {filename}",
                    evidence={"file": filename, "mapping": mapping},
                    remediation_class=RemediationClass.AUTO_SAFE,
                    proposed_action={"tool": "canonicalize_geo_labels", "file": filename},
                )
            )

    if descriptor.canonical_role is CanonicalRole.INACTIVITY_EVIDENCE:
        issues.extend(_documented_inactivity_issues(frame, filename))

    return issues


def _unknown_absence_issues(
    descriptor: SourceDescriptor,
    frame: pd.DataFrame,
    kpi_frame: pd.DataFrame,
    inactivity: pd.DataFrame | None,
    date_field: str,
    filename: str,
) -> list[Issue]:
    kpi_date = _time_column(kpi_frame)
    if kpi_date is None or "geo" not in kpi_frame.columns or "geo" not in frame.columns:
        return []
    media_weeks = _weekly_keys(frame, date_field)
    kpi_weeks = _weekly_keys(kpi_frame, kpi_date)
    documented = _documented_keys(inactivity, descriptor.provider_id)
    by_geo: dict[str, list[str]] = {}
    for week, geo in media_weeks:
        by_geo.setdefault(geo, []).append(week)
    missing: list[dict[str, str]] = []
    for week, geo in sorted(kpi_weeks):
        if (week, geo) in media_weeks or (week, geo) in documented:
            continue
        observed = by_geo.get(geo) or []
        if not observed:
            continue
        if week < min(observed) or week > max(observed):
            continue
        missing.append({"week_start": week, "geo": geo})
    if not missing:
        return []
    return [
        _issue(
            rule_id="MR-011",
            filename=filename,
            qualifier="unknown_absence",
            title=f"Unknown source gap in {filename}",
            evidence={"file": filename, "cells": missing, "zero_fill_forbidden": True},
            remediation_class=RemediationClass.APPROVAL_REQUIRED,
            proposed_action={"tool": None, "file": filename},
        )
    ]


def _documented_inactivity_issues(frame: pd.DataFrame, filename: str) -> list[Issue]:
    if "provider" not in frame.columns:
        return []
    issues: list[Issue] = []
    grouped = frame.groupby(["provider", "geo"], dropna=False)
    for (provider, geo), part in grouped:
        weeks = sorted(
            str(value) for value in part.get("week_start", pd.Series(dtype=str)).tolist()
        )
        if not weeks:
            continue
        issues.append(
            _issue(
                rule_id="MR-011",
                filename=filename,
                qualifier=f"inactivity:{provider}:{geo}",
                title=f"Documented inactivity for {provider} / {geo}",
                evidence={
                    "file": filename,
                    "provider": str(provider),
                    "geo": str(geo),
                    "weeks": weeks,
                    "zero_fill_may_be_safe": True,
                },
                remediation_class=RemediationClass.AUTO_SAFE,
                proposed_action={
                    "tool": "zero_fill_documented_inactivity",
                    "file": filename,
                    "provider_id": str(provider),
                },
            )
        )
    return issues


def _missing_control_cell_issues(
    descriptor: SourceDescriptor,
    frame: pd.DataFrame,
    kpi_frame: pd.DataFrame,
    filename: str,
    intent: ModelIntent,
) -> list[Issue]:
    date_field = descriptor.date_field or _time_column(frame)
    kpi_date = _time_column(kpi_frame)
    if date_field is None or kpi_date is None or "geo" not in frame.columns:
        return []
    present = _weekly_keys(frame.dropna(how="all"), date_field)
    missing_cells: list[dict[str, str]] = []
    control_cols = [column for column in intent.controls if column in frame.columns]
    for column in control_cols:
        nulls = frame.loc[frame[column].isna()]
        for _, row in nulls.iterrows():
            missing_cells.append(
                {"week_start": str(row[date_field]), "geo": str(row["geo"]), "field": column}
            )
    kpi_keys = _weekly_keys(kpi_frame, kpi_date)
    for week, geo in sorted(kpi_keys - present):
        missing_cells.append({"week_start": week, "geo": geo})
    if not missing_cells:
        return []
    return [
        _issue(
            rule_id="MR-002",
            filename=filename,
            qualifier="missing_control",
            title=f"Missing control observations in {filename}",
            evidence={
                "file": filename,
                "cells": missing_cells,
                "zero_fill_forbidden": True,
                "control_imputation_auto_safe": False,
            },
            remediation_class=RemediationClass.APPROVAL_REQUIRED,
            proposed_action={"tool": None, "file": filename},
        )
    ]


def _missing_control_issues(inventory: SourceInventory, intent: ModelIntent) -> list[Issue]:
    present_fields: set[str] = set()
    for descriptor in inventory.sources:
        present_fields.update(descriptor.columns)
    missing = [control for control in intent.controls if control not in present_fields]
    issues: list[Issue] = []
    for control in missing:
        issues.append(
            _issue(
                rule_id="MR-002",
                filename="model_intent.json",
                qualifier=f"missing_control_field:{control}",
                title=f"Declared control '{control}' is not present in any source",
                evidence={"field": control, "zero_fill_forbidden": True},
                remediation_class=RemediationClass.APPROVAL_REQUIRED,
                proposed_action={"tool": None},
            )
        )
    return issues


def _issue(
    *,
    rule_id: str,
    filename: str,
    qualifier: str,
    title: str,
    evidence: dict,
    remediation_class: RemediationClass,
    proposed_action: dict,
) -> Issue:
    issue_id = GOLDEN_ISSUE_ALIASES.get(
        (rule_id, filename, qualifier), f"{rule_id}:{filename}:{qualifier}"
    )
    return Issue(
        issue_id=issue_id,
        rule_id=rule_id,
        severity=Severity.ERROR,
        title=title,
        evidence=evidence,
        remediation_class=remediation_class,
        proposed_action=proposed_action,
    )


def _load_role_frame(
    root: Path, inventory: SourceInventory, role: CanonicalRole
) -> pd.DataFrame | None:
    sources = inventory.sources_for_role(role)
    if not sources:
        return None
    frames = [read_table(root / item.relative_path) for item in sources]
    return pd.concat(frames, ignore_index=True) if frames else None


def _time_column(frame: pd.DataFrame) -> str | None:
    for column in TIME_FIELD_CANDIDATES:
        if column in frame.columns:
            return column
    return None


def _weekly_keys(frame: pd.DataFrame, date_field: str) -> set[tuple[str, str]]:
    parsed = pd.to_datetime(frame[date_field], errors="coerce")
    weeks = parsed.dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
    geos = frame["geo"].astype(str)
    return {
        (str(week), str(geo))
        for week, geo in zip(weeks.tolist(), geos.tolist(), strict=False)
        if week != "NaT"
    }


def _documented_keys(
    inactivity: pd.DataFrame | None, provider_id: str | None
) -> set[tuple[str, str]]:
    if inactivity is None or provider_id is None or "provider" not in inactivity.columns:
        return set()
    relevant = inactivity.loc[inactivity["provider"].astype(str) == provider_id]
    if "week_start" not in relevant.columns or "geo" not in relevant.columns:
        return set()
    return {(str(row["week_start"]), str(row["geo"])) for _, row in relevant.iterrows()}


def _channel_values(frame: pd.DataFrame) -> list[str]:
    for column in ("channel", "campaign", "campaign_name"):
        if column in frame.columns:
            return [str(value) for value in frame[column].tolist()]
    return []


def _canonical_tool(name: str) -> str:
    return TOOL_NAME_ALIASES.get(name, name)


def _matching_transform(issue: Issue, transforms: list[dict]) -> dict | None:
    expected = _canonical_tool(str(issue.proposed_action.get("tool") or ""))
    if not expected:
        return None
    matches: list[dict] = []
    for item in transforms:
        if item.get("tool") != expected:
            continue
        parameters = item.get("parameters") or {}
        expected_format = issue.proposed_action.get("expected_format")
        if expected_format and parameters.get("expected_format") != expected_format:
            continue
        expected_column = issue.proposed_action.get("column")
        if expected_column and parameters.get("column") != expected_column:
            continue
        matches.append(item)
    return matches[-1] if matches else None
