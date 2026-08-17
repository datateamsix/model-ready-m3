"""Assemble the canonical Meridian model frame from repaired sources + model intent."""

from __future__ import annotations

import pandas as pd

from app.core.errors import ValidationBlockedError
from app.core.model_intent import (
    FLOAT_MODEL_COLUMNS,
    INTEGER_MODEL_COLUMNS,
    MODEL_READY_COLUMNS,
    ModelIntent,
    PaidMediaChannel,
    float_model_columns,
    integer_model_columns,
    model_ready_columns,
)
from app.core.source_inventory import TIME_FIELD_CANDIDATES, CanonicalRole, SourceInventory


def build_model_ready_frame(
    *,
    intent: ModelIntent,
    google: pd.DataFrame | None = None,
    meta: pd.DataFrame | None = None,
    shopify: pd.DataFrame | None = None,
    ga4: pd.DataFrame | None = None,
    controls: pd.DataFrame | None = None,
    population: pd.DataFrame | None = None,
    frames_by_path: dict[str, pd.DataFrame] | None = None,
    inventory: SourceInventory | None = None,
) -> pd.DataFrame:
    """Independently construct time × geo model input. Never reads regression truth."""
    if inventory is not None and frames_by_path is not None:
        kpi_frame = _first_role_frame(inventory, frames_by_path, CanonicalRole.KPI)
        revenue_frame = (
            _first_role_frame(inventory, frames_by_path, CanonicalRole.REVENUE) or kpi_frame
        )
        organic_pairs = _organic_frames(inventory, frames_by_path, intent)
        control_frames = _role_frames(inventory, frames_by_path, CanonicalRole.CONTROLS)
        population_frame = _first_role_frame(inventory, frames_by_path, CanonicalRole.POPULATION)
        paid_pairs = _paid_media_frames(inventory, frames_by_path, intent)
    else:
        if shopify is None or google is None or meta is None or ga4 is None:
            raise ValidationBlockedError(
                "Legacy frame assembly requires shopify, google, meta, and ga4."
            )
        if controls is None or population is None:
            raise ValidationBlockedError("Legacy frame assembly requires controls and population.")
        kpi_frame = shopify
        revenue_frame = shopify
        organic_pairs = list(
            zip(intent.organic_media, [ga4] * len(intent.organic_media), strict=False)
        )
        control_frames = [controls]
        population_frame = population
        paid_pairs = []
        for channel in intent.paid_media:
            source = google if channel.provider == "google_ads" else meta
            paid_pairs.append((channel, source))

    if kpi_frame is None or revenue_frame is None or population_frame is None:
        raise ValidationBlockedError("KPI, revenue, and population sources are required.")
    if intent.kpi.field not in kpi_frame.columns:
        raise ValidationBlockedError("KPI source is missing the declared KPI field.")
    if intent.revenue.field not in revenue_frame.columns:
        raise ValidationBlockedError("Revenue source is missing the declared revenue field.")
    if "average_order_value" in kpi_frame.columns and intent.kpi.field == "average_order_value":
        raise ValidationBlockedError("average_order_value is not a valid KPI.")

    kpi_col = intent.kpi.canonical_field or "kpi_orders"
    revenue_col = intent.revenue.canonical_field or "kpi_revenue"
    spine = _rename_time(kpi_frame).copy(deep=True)
    spine = spine.rename(columns={intent.kpi.field: kpi_col})
    if intent.revenue.field in spine.columns:
        spine = spine.rename(columns={intent.revenue.field: revenue_col})
    else:
        revenue_part = _rename_time(revenue_frame).rename(
            columns={intent.revenue.field: revenue_col}
        )
        spine = spine.merge(
            revenue_part[["time", "geo", revenue_col]], on=["time", "geo"], how="left"
        )
    spine["revenue_per_kpi"] = (spine[revenue_col] / spine[kpi_col]).round(2)
    frame = spine[["time", "geo", kpi_col, revenue_col, "revenue_per_kpi"]].copy()

    for channel, source in paid_pairs:
        slice_frame = _channel_metrics(source, channel.channel, channel)
        frame = frame.merge(slice_frame, on=["time", "geo"], how="left")

    for organic, organic_frame in organic_pairs:
        organic_col = organic.canonical_field or organic.field
        part = _rename_time(organic_frame).rename(columns={organic.field: organic_col})
        if organic_col not in part.columns:
            raise ValidationBlockedError(f"Organic field '{organic.field}' is missing.")
        frame = frame.merge(part[["time", "geo", organic_col]], on=["time", "geo"], how="left")

    if intent.controls:
        control_part = _merge_control_frames(control_frames, intent.controls)
        frame = frame.merge(control_part, on=["time", "geo"], how="left")

    pop_field = intent.population.field if intent.population else "population"
    if pop_field not in population_frame.columns:
        raise ValidationBlockedError(f"Population field '{pop_field}' is missing.")
    frame = frame.merge(
        population_frame[["geo", pop_field]].rename(columns={pop_field: "population"}),
        on="geo",
        how="left",
    )

    columns = model_ready_columns(intent)
    missing_columns = [column for column in columns if column not in frame.columns]
    if missing_columns:
        raise ValidationBlockedError(f"Assembled frame missing columns: {missing_columns}")
    result = frame.loc[:, columns].copy(deep=True)
    result = coerce_model_frame_types(result, intent=intent)
    result = result.sort_values(["time", "geo"], kind="mergesort").reset_index(drop=True)
    if int(result.duplicated(subset=["time", "geo"]).sum()) != 0:
        raise ValidationBlockedError("Assembled frame is not unique at time × geo.")
    if int(result.isna().sum().sum()) != 0:
        raise ValidationBlockedError("Assembled frame contains unsupported nulls.")
    return result


def _channel_metrics(frame: pd.DataFrame, channel: str, spec: PaidMediaChannel) -> pd.DataFrame:
    timed = _rename_time(frame)
    spend_col = spec.source_spend if spec.source_spend in timed.columns else _fallback_spend(timed)
    impressions_col = spec.source_impressions
    if "channel" in timed.columns:
        subset = timed.loc[
            timed["channel"].astype(str) == channel, ["time", "geo", impressions_col, spend_col]
        ]
    else:
        subset = timed[["time", "geo", impressions_col, spend_col]]
    if subset.empty:
        raise ValidationBlockedError(f"No rows found for modeled channel '{channel}'.")
    grouped = subset.groupby(["time", "geo"], dropna=False, as_index=False)[
        [impressions_col, spend_col]
    ].sum()
    return grouped.rename(
        columns={
            impressions_col: spec.impressions_column,
            spend_col: spec.spend_column,
        }
    )


def coerce_model_frame_types(
    frame: pd.DataFrame, intent: ModelIntent | None = None
) -> pd.DataFrame:
    result = frame.copy(deep=True)
    result["time"] = pd.to_datetime(result["time"], errors="raise").dt.strftime("%Y-%m-%d")
    result["geo"] = result["geo"].astype(str)
    if intent is not None:
        integers = integer_model_columns(intent)
        floats = float_model_columns(intent)
    elif all(column in result.columns for column in MODEL_READY_COLUMNS):
        integers = INTEGER_MODEL_COLUMNS
        floats = FLOAT_MODEL_COLUMNS
    else:
        integers = [column for column in INTEGER_MODEL_COLUMNS if column in result.columns]
        floats = [column for column in FLOAT_MODEL_COLUMNS if column in result.columns]
    for column in integers:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="raise").round().astype("int64")
    for column in floats:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="raise").astype("float64")
    return result


def _rename_time(frame: pd.DataFrame) -> pd.DataFrame:
    if "time" in frame.columns:
        return frame.copy(deep=True)
    for column in TIME_FIELD_CANDIDATES:
        if column in frame.columns:
            return frame.rename(columns={column: "time"})
    raise ValidationBlockedError("Source frame is missing a time column.")


def _fallback_spend(frame: pd.DataFrame) -> str:
    for column in ("cost", "spend", "amount_spent"):
        if column in frame.columns:
            return column
    raise ValidationBlockedError("Paid media frame is missing a spend column.")


def _first_role_frame(
    inventory: SourceInventory,
    frames_by_path: dict[str, pd.DataFrame],
    role: CanonicalRole,
) -> pd.DataFrame | None:
    frames = _role_frames(inventory, frames_by_path, role)
    return frames[0] if frames else None


def _role_frames(
    inventory: SourceInventory,
    frames_by_path: dict[str, pd.DataFrame],
    role: CanonicalRole,
) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    for descriptor in inventory.sources_for_role(role):
        frame = frames_by_path.get(descriptor.relative_path)
        if frame is not None:
            frames.append(frame)
    return frames


def _organic_frames(
    inventory: SourceInventory,
    frames_by_path: dict[str, pd.DataFrame],
    intent: ModelIntent,
) -> list[tuple]:
    pairs: list[tuple] = []
    organic_sources = inventory.sources_for_role(CanonicalRole.ORGANIC_MEDIA)
    for organic in intent.organic_media:
        match = next(
            (
                item
                for item in organic_sources
                if item.provider_id == organic.provider and organic.field in item.columns
            ),
            None,
        )
        if match is None:
            raise ValidationBlockedError(f"Organic source for {organic.provider} is missing.")
        pairs.append((organic, frames_by_path[match.relative_path]))
    return pairs


def _paid_media_frames(
    inventory: SourceInventory,
    frames_by_path: dict[str, pd.DataFrame],
    intent: ModelIntent,
) -> list[tuple[PaidMediaChannel, pd.DataFrame]]:
    pairs: list[tuple[PaidMediaChannel, pd.DataFrame]] = []
    paid_sources = inventory.sources_for_role(CanonicalRole.PAID_MEDIA)
    for channel in intent.paid_media:
        matches = [item for item in paid_sources if item.provider_id == channel.provider]
        if not matches:
            raise ValidationBlockedError(f"Paid media source for {channel.provider} is missing.")
        hinted = [item for item in matches if item.channel_hint == channel.channel]
        chosen = hinted[0] if len(hinted) == 1 else matches[0]
        if not hinted and len(matches) > 1:
            with_channel = [
                item
                for item in matches
                if "channel" in item.columns or item.channel_hint is None
            ]
            chosen = with_channel[0] if with_channel else matches[0]
        pairs.append((channel, frames_by_path[chosen.relative_path]))
    return pairs


def _merge_control_frames(frames: list[pd.DataFrame], controls: list[str]) -> pd.DataFrame:
    if not frames:
        raise ValidationBlockedError(f"Control columns missing: {controls}")
    merged: pd.DataFrame | None = None
    present: set[str] = set()
    for frame in frames:
        part = _rename_time(frame)
        keep = ["time", "geo", *[column for column in controls if column in part.columns]]
        present.update(column for column in controls if column in part.columns)
        sliced = part.loc[:, keep]
        merged = sliced if merged is None else merged.merge(sliced, on=["time", "geo"], how="outer")
    missing = [column for column in controls if column not in present]
    if missing:
        raise ValidationBlockedError(f"Control columns missing: {missing}")
    if merged is None:
        raise ValidationBlockedError(f"Control columns missing: {controls}")
    return merged
