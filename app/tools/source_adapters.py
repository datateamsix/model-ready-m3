"""Provider/report adapters: deterministic mechanics, not causal judgment."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.errors import AssignmentInitError
from app.core.model_intent import ModelIntent, PaidMediaChannel
from app.core.source_inventory import (
    CanonicalRole,
    InitFailureReason,
    SourceDescriptor,
    detect_time_field,
)
from app.tools.adk_tools import (
    aggregate_campaign_to_channel_in_file,
    aggregate_file_to_week,
    canonicalize_channel_labels_in_file,
    normalize_dates_in_file,
    normalize_numeric_values_in_file,
    remove_exact_duplicates_from_file,
)
from app.tools.io import read_table, write_table
from app.tools.profiling import detect_duplicates, detect_grain, looks_like_currency
from app.tools.provenance import record_transform
from app.tools.remediation import (
    canonicalize_geo_labels,
    convert_cost_micros_to_currency,
    convert_week_ending_to_week_start,
)
from app.tools.safety import assert_summable_columns, non_summable_names

SUMMABLE_CANDIDATES = (
    "impressions",
    "clicks",
    "cost",
    "spend",
    "amount_spent",
    "sessions",
    "users",
    "organic_sessions",
    "send_count",
    "delivered",
    "unique_opens",
    "unique_clicks",
    "orders",
    "net_revenue",
    "bookings",
    "booking_revenue",
    "successful_charges",
)
CAMPAIGN_GRAIN_COLUMNS = ("campaign", "campaign_name", "adset_name", "product_group", "ad_group")


def iso_ratio(series: pd.Series) -> float:
    parsed = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
    return float((~parsed.isna()).mean()) if len(series) else 0.0


def format_ratio(series: pd.Series, fmt: str) -> float:
    parsed = pd.to_datetime(series, format=fmt, errors="coerce")
    return float((~parsed.isna()).mean()) if len(series) else 0.0


def detect_source_date_format(series: pd.Series) -> str | None:
    if iso_ratio(series) == 1.0:
        return "YYYY-MM-DD"
    if format_ratio(series, "%m/%d/%Y") == 1.0:
        return "MM/DD/YYYY"
    return None


def population_geo_map(population: pd.DataFrame) -> dict[str, str]:
    """Canonical geos from the assignment population file, plus labels when present."""
    mapping: dict[str, str] = {}
    if "geo" not in population.columns:
        return mapping
    for _, row in population.iterrows():
        geo = str(row["geo"])
        mapping[geo] = geo
        if "geo_label" in population.columns and not pd.isna(row["geo_label"]):
            mapping[str(row["geo_label"])] = geo
    return mapping


def resolve_geo_value(value: str, canonical: set[str], labels: dict[str, str]) -> str | None:
    if value in canonical:
        return value
    if value in labels:
        return labels[value]
    matches: list[str] = []
    for geo in canonical:
        if value.startswith(geo + " ") or value.startswith(geo + "-"):
            matches.append(geo)
    if len(matches) == 1:
        return matches[0]
    value_tokens = set(value.lower().replace("-", " ").split())
    token_hits: list[str] = []
    for label, geo in labels.items():
        label_tokens = set(label.lower().replace("-", " ").split())
        if value_tokens & label_tokens:
            token_hits.append(geo)
    unique = sorted(set(token_hits))
    if len(unique) == 1:
        return unique[0]
    return None


def geo_alias_mapping(frame: pd.DataFrame, population: pd.DataFrame) -> dict[str, str]:
    if "geo" not in frame.columns or "geo" not in population.columns:
        return {}
    canonical = {str(value) for value in population["geo"].tolist()}
    labels = population_geo_map(population)
    mapping: dict[str, str] = {}
    for value in {str(item) for item in frame["geo"].tolist()}:
        resolved = resolve_geo_value(value, canonical, labels)
        if resolved is not None:
            mapping[value] = resolved
    return mapping


def channel_alias_mapping(
    frame: pd.DataFrame,
    intent: ModelIntent,
    descriptor: SourceDescriptor,
) -> dict[str, str]:
    channels = [
        channel.channel
        for channel in intent.paid_media
        if channel.provider == descriptor.provider_id
    ]
    if not channels:
        return {}
    column = _channel_source_column(frame)
    if column is None:
        return {}
    mapping: dict[str, str] = {}
    for value in {str(item) for item in frame[column].tolist()}:
        if value in channels:
            mapping[value] = value
            continue
        lowered = value.lower()
        token_hits = [channel for channel in channels if channel.split("_")[-1] in lowered]
        if len(token_hits) == 1:
            mapping[value] = token_hits[0]
            continue
        if len(channels) == 1:
            mapping[value] = channels[0]
    return mapping


def extra_grain_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in CAMPAIGN_GRAIN_COLUMNS if column in frame.columns]


def summable_columns(frame: pd.DataFrame, provider_id: str | None) -> list[str]:
    blocked = non_summable_names(provider_id)
    present = [
        column
        for column in SUMMABLE_CANDIDATES
        if column in frame.columns and column.lower() not in blocked
    ]
    assert_summable_columns(present, provider_id)
    return present


def currency_columns(
    frame: pd.DataFrame, intent: ModelIntent, descriptor: SourceDescriptor
) -> list[str]:
    candidates: list[str] = []
    if descriptor.canonical_role is CanonicalRole.PAID_MEDIA:
        for channel in intent.paid_media:
            if channel.provider == descriptor.provider_id and channel.source_spend in frame.columns:
                candidates.append(channel.source_spend)
        for name in ("amount_spent", "spend", "cost", "booking_revenue", "net_revenue"):
            if name in frame.columns:
                candidates.append(name)
    if descriptor.canonical_role in {CanonicalRole.KPI, CanonicalRole.REVENUE}:
        for name in (intent.kpi.field, intent.revenue.field, "net_revenue", "booking_revenue"):
            if name in frame.columns:
                candidates.append(name)
    unique: list[str] = []
    for column in candidates:
        if column not in unique and looks_like_currency(frame[column]):
            unique.append(column)
    return unique


def repair_source_file(
    *,
    source_path: str,
    descriptor: SourceDescriptor,
    intent: ModelIntent,
    transform_dir: str | Path,
    population: pd.DataFrame | None = None,
    inactivity: pd.DataFrame | None = None,
) -> str:
    """Apply deterministic adapter steps for one source. Does not assign causal roles."""
    transform_root = Path(transform_dir)
    transform_root.mkdir(parents=True, exist_ok=True)
    current = source_path
    stem = descriptor.source_id

    frame = read_table(current)
    date_field = descriptor.date_field or detect_time_field(
        list(frame.columns), descriptor.provider_id
    )
    if date_field and date_field in frame.columns:
        detected = detect_source_date_format(frame[date_field])
        expected = detected or "YYYY-MM-DD"
        dated = str(transform_root / f"{stem}_dates.csv")
        normalize_dates_in_file(current, date_field, dated, expected)
        current = dated
        frame = read_table(current)
        if date_field == "week_ending":
            converted = convert_week_ending_to_week_start(frame, "week_ending")
            written = transform_root / f"{stem}_week_start.csv"
            write_table(converted, written)
            record_transform(
                tool="convert_week_ending_to_week_start",
                rule_id="MR-001",
                source_uri=current,
                output_uri=str(written),
                input_rows=int(len(frame)),
                output_rows=int(len(converted)),
                parameters={"column": "week_ending"},
                reason="Align Sunday-ending weeks to Monday-start week_start.",
            )
            current = str(written)
            frame = converted
            date_field = "week_start"

    for column in currency_columns(frame, intent, descriptor):
        numeric = str(transform_root / f"{stem}_{column}_numeric.csv")
        normalize_numeric_values_in_file(current, column, numeric)
        current = numeric
        frame = read_table(current)

    spend_field = _spend_field(intent, descriptor)
    if spend_field == "cost_micros" and "cost_micros" in frame.columns:
        converted = convert_cost_micros_to_currency(frame, "cost_micros")
        written = transform_root / f"{stem}_currency.csv"
        write_table(converted, written)
        record_transform(
            tool="convert_cost_micros_to_currency",
            rule_id="MR-017",
            source_uri=current,
            output_uri=str(written),
            input_rows=int(len(frame)),
            output_rows=int(len(converted)),
            parameters={"column": "cost_micros"},
            reason="Convert Google Ads cost_micros to currency units.",
        )
        current = str(written)
        frame = converted

    if population is not None and "geo" in frame.columns:
        mapping = geo_alias_mapping(frame, population)
        if any(source != target for source, target in mapping.items()):
            rewritten = canonicalize_geo_labels(frame, "geo", mapping)
            written = transform_root / f"{stem}_geo.csv"
            write_table(rewritten, written)
            record_transform(
                tool="canonicalize_geo_labels",
                rule_id="MR-005",
                source_uri=current,
                output_uri=str(written),
                input_rows=int(len(frame)),
                output_rows=int(len(rewritten)),
                parameters={"column": "geo", "mapping": mapping},
                reason="Map geo aliases onto the assignment's canonical geo set.",
            )
            current = str(written)
            frame = rewritten

    if descriptor.canonical_role is CanonicalRole.PAID_MEDIA:
        channel_map = channel_alias_mapping(frame, intent, descriptor)
        channel_col = _channel_source_column(frame)
        if channel_col is None:
            frame = frame.copy(deep=True)
            hint = descriptor.channel_hint or _single_channel(intent, descriptor.provider_id)
            if hint is None:
                raise AssignmentInitError(
                    f"Cannot determine modeled channel for {descriptor.relative_path}.",
                    reason=InitFailureReason.AMBIGUOUS_SOURCE_ROLE.value,
                    source=descriptor.relative_path,
                    recoverability="USER_REQUIRED",
                    owner="user",
                )
            frame["channel"] = hint
            written = transform_root / f"{stem}_channel_assigned.csv"
            write_table(frame, written)
            record_transform(
                tool="assign_modeled_channel",
                rule_id="MR-009",
                source_uri=current,
                output_uri=str(written),
                input_rows=int(len(frame)),
                output_rows=int(len(frame)),
                parameters={"channel": hint, "provider_id": descriptor.provider_id},
                reason="Assign the modeled channel declared for this provider/report.",
            )
            current = str(written)
            channel_col = "channel"
        elif channel_map and any(source != target for source, target in channel_map.items()):
            if channel_col != "channel":
                frame = frame.copy(deep=True)
                frame["channel"] = frame[channel_col]
                channel_col = "channel"
                written = transform_root / f"{stem}_channel_col.csv"
                write_table(frame, written)
                current = str(written)
            labeled = str(transform_root / f"{stem}_channels.csv")
            canonicalize_channel_labels_in_file(current, channel_col, channel_map, labeled)
            current = labeled
            frame = read_table(current)
        elif channel_col != "channel":
            frame = frame.copy(deep=True)
            frame["channel"] = frame[channel_col].map(
                lambda value: channel_map.get(str(value), str(value))
            )
            written = transform_root / f"{stem}_channel_col.csv"
            write_table(frame, written)
            current = str(written)
            frame = read_table(current)

        dups = detect_duplicates(frame)
        if dups["excess_rows"] > 0:
            deduped = str(transform_root / f"{stem}_deduped.csv")
            remove_exact_duplicates_from_file(current, deduped)
            current = deduped
            frame = read_table(current)

        if descriptor.date_field and descriptor.date_field in frame.columns:
            date_field = descriptor.date_field
        else:
            date_field = detect_time_field(list(frame.columns), descriptor.provider_id)
        if date_field == "week_ending" and "week_start" in frame.columns:
            date_field = "week_start"
        grain_cols = [
            column
            for column in (date_field, "geo", "channel")
            if column and column in frame.columns
        ]
        extra = extra_grain_columns(frame)
        sums = summable_columns(frame, descriptor.provider_id)
        if extra or (date_field and "channel" in frame.columns):
            channeled = str(transform_root / f"{stem}_channel.csv")
            aggregate_campaign_to_channel_in_file(
                current,
                grain_cols,
                sums,
                channeled,
                provider_id=descriptor.provider_id,
            )
            current = channeled
            frame = read_table(current)
            date_field = detect_time_field(list(frame.columns), descriptor.provider_id)

        if date_field and date_field in frame.columns:
            grain = detect_grain(frame, date_field)
            if grain["grain"] == "daily" and intent.canonical_time_grain.value == "weekly":
                weekly = str(transform_root / f"{stem}_weekly.csv")
                group_cols = [column for column in ("geo", "channel") if column in frame.columns]
                aggregate_file_to_week(
                    current,
                    date_field,
                    group_cols,
                    summable_columns(frame, descriptor.provider_id),
                    weekly,
                    provider_id=descriptor.provider_id,
                )
                current = weekly
                frame = read_table(current)
                date_field = "week_start"

        if inactivity is not None and descriptor.provider_id:
            filled = _zero_fill_documented_inactivity(
                frame,
                inactivity=inactivity,
                provider_id=descriptor.provider_id,
                date_field=detect_time_field(list(frame.columns), descriptor.provider_id)
                or "week_start",
            )
            if filled is not None:
                written = transform_root / f"{stem}_inactivity.csv"
                write_table(filled, written)
                record_transform(
                    tool="zero_fill_documented_inactivity",
                    rule_id="MR-011",
                    source_uri=current,
                    output_uri=str(written),
                    input_rows=int(len(frame)),
                    output_rows=int(len(filled)),
                    parameters={"provider_id": descriptor.provider_id},
                    reason="Zero-fill only weeks with confirmed inactivity evidence.",
                )
                current = str(written)

    elif detect_duplicates(frame)["excess_rows"] > 0:
        deduped = str(transform_root / f"{stem}_deduped.csv")
        remove_exact_duplicates_from_file(current, deduped)
        current = deduped

    return current


def bind_paid_media_frame(
    descriptor: SourceDescriptor,
    frame: pd.DataFrame,
    channel: PaidMediaChannel,
) -> pd.DataFrame:
    if descriptor.channel_hint and descriptor.channel_hint != channel.channel:
        return frame.iloc[0:0].copy()
    if "channel" in frame.columns:
        return frame.loc[frame["channel"].astype(str) == channel.channel].copy(deep=True)
    return frame.copy(deep=True)


def _channel_source_column(frame: pd.DataFrame) -> str | None:
    for column in ("channel", "campaign", "campaign_name"):
        if column in frame.columns:
            return column
    return None


def _single_channel(intent: ModelIntent, provider_id: str | None) -> str | None:
    channels = [channel.channel for channel in intent.paid_media if channel.provider == provider_id]
    if len(channels) == 1:
        return channels[0]
    return None


def _spend_field(intent: ModelIntent, descriptor: SourceDescriptor) -> str | None:
    for channel in intent.paid_media:
        if channel.provider == descriptor.provider_id:
            return channel.source_spend
    return None


def _zero_fill_documented_inactivity(
    frame: pd.DataFrame,
    *,
    inactivity: pd.DataFrame,
    provider_id: str,
    date_field: str,
) -> pd.DataFrame | None:
    if "provider" not in inactivity.columns:
        return None
    relevant = inactivity.loc[
        inactivity["provider"].astype(str) == provider_id
    ]
    if "zero_fill_may_be_safe" in relevant.columns:
        relevant = relevant.loc[relevant["zero_fill_may_be_safe"].astype(str).str.lower() == "true"]
    if relevant.empty or date_field not in frame.columns or "geo" not in frame.columns:
        return None
    existing = {(str(row[date_field]), str(row["geo"])) for _, row in frame.iterrows()}
    additions: list[dict[str, object]] = []
    template = {
        column: 0
        for column in frame.columns
        if column not in {date_field, "geo", "channel"}
    }
    if "channel" in frame.columns:
        channels = sorted({str(value) for value in frame["channel"].tolist()})
    else:
        channels = [None]
    week_col = "week_start" if "week_start" in relevant.columns else date_field
    for _, row in relevant.iterrows():
        week = str(row[week_col])
        geo = str(row["geo"])
        for channel in channels:
            key = (week, geo)
            if key in existing:
                continue
            item = dict(template)
            item[date_field] = week
            item["geo"] = geo
            if channel is not None:
                item["channel"] = channel
            additions.append(item)
            existing.add(key)
    if not additions:
        return None
    extra = pd.DataFrame(additions)
    combined = pd.concat([frame, extra], ignore_index=True)
    return combined.sort_values([date_field, "geo"], kind="mergesort").reset_index(drop=True)
