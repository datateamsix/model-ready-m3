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
)


def build_model_ready_frame(
    *,
    google: pd.DataFrame,
    meta: pd.DataFrame,
    shopify: pd.DataFrame,
    ga4: pd.DataFrame,
    controls: pd.DataFrame,
    population: pd.DataFrame,
    intent: ModelIntent,
) -> pd.DataFrame:
    """Independently construct time × geo model input. Never reads regression truth."""
    if intent.kpi.field not in shopify.columns or intent.revenue.field not in shopify.columns:
        raise ValidationBlockedError("Shopify frame is missing the declared KPI/revenue fields.")
    if "average_order_value" in shopify.columns and intent.kpi.field == "average_order_value":
        raise ValidationBlockedError("average_order_value is not a valid KPI.")

    spine = shopify.rename(
        columns={
            "week_start": "time",
            intent.kpi.field: intent.kpi.canonical_field or "kpi_orders",
            intent.revenue.field: intent.revenue.canonical_field or "kpi_revenue",
        }
    ).copy(deep=True)
    kpi_col = intent.kpi.canonical_field or "kpi_orders"
    revenue_col = intent.revenue.canonical_field or "kpi_revenue"
    spine["revenue_per_kpi"] = (spine[revenue_col] / spine[kpi_col]).round(2)
    frame = spine[["time", "geo", kpi_col, revenue_col, "revenue_per_kpi"]].copy()

    for channel in intent.paid_media:
        source = google if channel.provider == "google_ads" else meta
        slice_frame = _channel_metrics(source, channel.channel, channel)
        frame = frame.merge(slice_frame, on=["time", "geo"], how="left")

    organic = intent.organic_media[0] if intent.organic_media else None
    if organic is not None:
        ga4_part = ga4.rename(
            columns={
                "week_start_date": "time",
                organic.field: organic.canonical_field or organic.field,
            }
        )
        organic_col = organic.canonical_field or organic.field
        frame = frame.merge(ga4_part[["time", "geo", organic_col]], on=["time", "geo"], how="left")

    control_cols = ["week_start", "geo", *intent.controls]
    missing_controls = [column for column in intent.controls if column not in controls.columns]
    if missing_controls:
        raise ValidationBlockedError(f"Control columns missing: {missing_controls}")
    control_part = controls.loc[:, control_cols].rename(columns={"week_start": "time"})
    frame = frame.merge(control_part, on=["time", "geo"], how="left")

    pop_field = intent.population.field if intent.population else "population"
    if pop_field not in population.columns:
        raise ValidationBlockedError(f"Population field '{pop_field}' is missing.")
    frame = frame.merge(
        population[["geo", pop_field]].rename(columns={pop_field: "population"}),
        on="geo",
        how="left",
    )

    missing_columns = [column for column in MODEL_READY_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValidationBlockedError(f"Assembled frame missing columns: {missing_columns}")
    result = frame.loc[:, MODEL_READY_COLUMNS].copy(deep=True)
    result = coerce_model_frame_types(result)
    result = result.sort_values(["time", "geo"], kind="mergesort").reset_index(drop=True)
    if int(result.duplicated(subset=["time", "geo"]).sum()) != 0:
        raise ValidationBlockedError("Assembled frame is not unique at time × geo.")
    if int(result.isna().sum().sum()) != 0:
        raise ValidationBlockedError("Assembled frame contains unsupported nulls.")
    return result


def _channel_metrics(frame: pd.DataFrame, channel: str, spec: PaidMediaChannel) -> pd.DataFrame:
    time_col = "week_start" if "week_start" in frame.columns else "time"
    spend_col = spec.source_spend if spec.source_spend in frame.columns else "cost"
    impressions_col = spec.source_impressions
    subset = frame.loc[
        frame["channel"].astype(str) == channel, [time_col, "geo", impressions_col, spend_col]
    ]
    if subset.empty:
        raise ValidationBlockedError(f"No rows found for modeled channel '{channel}'.")
    grouped = subset.groupby([time_col, "geo"], dropna=False, as_index=False)[
        [impressions_col, spend_col]
    ].sum()
    return grouped.rename(
        columns={
            time_col: "time",
            impressions_col: spec.impressions_column,
            spend_col: spec.spend_column,
        }
    )


def coerce_model_frame_types(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy(deep=True)
    result["time"] = pd.to_datetime(result["time"], errors="raise").dt.strftime("%Y-%m-%d")
    result["geo"] = result["geo"].astype(str)
    for column in INTEGER_MODEL_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="raise").round().astype("int64")
    for column in FLOAT_MODEL_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="raise").astype("float64")
    return result
