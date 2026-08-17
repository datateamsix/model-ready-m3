"""User/workflow model-intent contract. This is runtime input, not regression truth."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.core.errors import ValidationBlockedError


class ModelTarget(StrEnum):
    GOOGLE_MERIDIAN = "google_meridian"


class ModelScope(StrEnum):
    GEO = "geo"
    NATIONAL = "national"


class TimeGrain(StrEnum):
    WEEKLY = "weekly"
    DAILY = "daily"
    MONTHLY = "monthly"


class FieldRef(BaseModel):
    provider: str
    field: str
    canonical_field: str | None = None


class PaidMediaChannel(BaseModel):
    provider: str
    channel: str
    impressions_column: str
    spend_column: str
    source_impressions: str = "impressions"
    source_spend: str


class ModelIntent(BaseModel):
    target: ModelTarget
    model_scope: ModelScope
    canonical_time_grain: TimeGrain
    kpi: FieldRef
    revenue: FieldRef
    population: FieldRef | None = None
    organic_media: list[FieldRef] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    paid_media: list[PaidMediaChannel] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_consistency(self) -> ModelIntent:
        if self.model_scope is ModelScope.GEO and self.population is None:
            raise ValueError("Geo models require a population field reference.")
        if self.canonical_time_grain is not TimeGrain.WEEKLY:
            raise ValueError("Phase 1 ModelReady runs require weekly canonical time grain.")
        if self.kpi.canonical_field is None:
            raise ValueError("KPI must declare canonical_field.")
        if self.revenue.canonical_field is None:
            raise ValueError("Revenue must declare canonical_field.")
        if self.kpi.canonical_field == self.revenue.canonical_field:
            raise ValueError("KPI and revenue canonical fields must be distinct.")
        if not self.paid_media:
            raise ValueError("At least one paid media channel is required.")
        channels = [item.channel for item in self.paid_media]
        if len(channels) != len(set(channels)):
            raise ValueError("paid_media channels must be unique.")
        return self

    def revenue_per_kpi_field(self) -> str:
        return "revenue_per_kpi"


def load_model_intent(payload: dict[str, Any]) -> ModelIntent:
    try:
        return ModelIntent.model_validate(payload)
    except Exception as exc:
        raise ValidationBlockedError(f"Invalid model_intent: {exc}") from exc


DATASET_A_MODEL_INTENT = ModelIntent(
    target=ModelTarget.GOOGLE_MERIDIAN,
    model_scope=ModelScope.GEO,
    canonical_time_grain=TimeGrain.WEEKLY,
    kpi=FieldRef(provider="shopify", field="orders", canonical_field="kpi_orders"),
    revenue=FieldRef(provider="shopify", field="net_revenue", canonical_field="kpi_revenue"),
    population=FieldRef(provider="synthetic_reference", field="population"),
    organic_media=[
        FieldRef(provider="ga4", field="organic_sessions", canonical_field="organic_sessions")
    ],
    controls=[
        "consumer_sentiment_index",
        "competitor_discount_index",
        "music_center_promo",
    ],
    paid_media=[
        PaidMediaChannel(
            provider="google_ads",
            channel="paid_search",
            impressions_column="paid_search_impressions",
            spend_column="paid_search_spend",
            source_impressions="impressions",
            source_spend="cost",
        ),
        PaidMediaChannel(
            provider="google_ads",
            channel="shopping",
            impressions_column="shopping_impressions",
            spend_column="shopping_spend",
            source_impressions="impressions",
            source_spend="cost",
        ),
        PaidMediaChannel(
            provider="meta_ads",
            channel="paid_social",
            impressions_column="paid_social_impressions",
            spend_column="paid_social_spend",
            source_impressions="impressions",
            source_spend="amount_spent",
        ),
    ],
)

DATASET_B_MODEL_INTENT = ModelIntent(
    target=ModelTarget.GOOGLE_MERIDIAN,
    model_scope=ModelScope.GEO,
    canonical_time_grain=TimeGrain.WEEKLY,
    kpi=FieldRef(provider="shopify", field="orders", canonical_field="kpi_orders"),
    revenue=FieldRef(provider="shopify", field="net_revenue", canonical_field="kpi_revenue"),
    population=FieldRef(provider="synthetic_reference", field="population"),
    organic_media=[
        FieldRef(provider="ga4", field="organic_sessions", canonical_field="organic_sessions"),
        FieldRef(provider="klaviyo", field="send_count", canonical_field="email_sends"),
    ],
    controls=[
        "weather_index",
        "competitor_price_index",
        "promotional_event",
        "holiday_flag",
    ],
    paid_media=[
        PaidMediaChannel(
            provider="microsoft_ads",
            channel="paid_search",
            impressions_column="paid_search_impressions",
            spend_column="paid_search_spend",
            source_impressions="impressions",
            source_spend="spend",
        ),
        PaidMediaChannel(
            provider="tiktok_ads",
            channel="paid_social_video",
            impressions_column="paid_social_video_impressions",
            spend_column="paid_social_video_spend",
            source_impressions="impressions",
            source_spend="spend",
        ),
        PaidMediaChannel(
            provider="amazon_ads",
            channel="retail_media",
            impressions_column="retail_media_impressions",
            spend_column="retail_media_spend",
            source_impressions="impressions",
            source_spend="cost",
        ),
    ],
)

DATASET_C_MODEL_INTENT = ModelIntent(
    target=ModelTarget.GOOGLE_MERIDIAN,
    model_scope=ModelScope.GEO,
    canonical_time_grain=TimeGrain.WEEKLY,
    kpi=FieldRef(provider="synthetic_pms", field="bookings", canonical_field="kpi_bookings"),
    revenue=FieldRef(
        provider="stripe", field="booking_revenue", canonical_field="kpi_revenue"
    ),
    population=FieldRef(provider="synthetic_reference", field="population"),
    organic_media=[
        FieldRef(provider="ga4", field="organic_sessions", canonical_field="organic_sessions"),
        FieldRef(provider="klaviyo", field="send_count", canonical_field="email_sends"),
    ],
    controls=[
        "availability_index",
        "snowfall_index",
        "holiday_flag",
        "adr_price_index",
        "promotional_package",
    ],
    paid_media=[
        PaidMediaChannel(
            provider="google_ads",
            channel="paid_search",
            impressions_column="paid_search_impressions",
            spend_column="paid_search_spend",
            source_impressions="impressions",
            source_spend="cost_micros",
        ),
        PaidMediaChannel(
            provider="pinterest_ads",
            channel="paid_social_upper",
            impressions_column="paid_social_upper_impressions",
            spend_column="paid_social_upper_spend",
            source_impressions="impressions",
            source_spend="spend",
        ),
        PaidMediaChannel(
            provider="meta_ads",
            channel="paid_social_prospecting",
            impressions_column="paid_social_prospecting_impressions",
            spend_column="paid_social_prospecting_spend",
            source_impressions="impressions",
            source_spend="amount_spent",
        ),
        PaidMediaChannel(
            provider="meta_ads",
            channel="paid_social_retargeting",
            impressions_column="paid_social_retargeting_impressions",
            spend_column="paid_social_retargeting_spend",
            source_impressions="impressions",
            source_spend="amount_spent",
        ),
    ],
)

def model_ready_columns(intent: ModelIntent) -> list[str]:
    """Canonical model-frame column order derived from model intent, not filenames."""
    kpi = intent.kpi.canonical_field or intent.kpi.field
    revenue = intent.revenue.canonical_field or intent.revenue.field
    columns = ["time", "geo", kpi, revenue, "revenue_per_kpi", "population"]
    for channel in intent.paid_media:
        columns.append(channel.impressions_column)
        columns.append(channel.spend_column)
    for organic in intent.organic_media:
        columns.append(organic.canonical_field or organic.field)
    columns.extend(intent.controls)
    return columns


def integer_model_columns(intent: ModelIntent) -> list[str]:
    """Integer-typed model columns: counts, impressions, flags, and promo indicators."""
    names = [intent.kpi.canonical_field or intent.kpi.field, "population"]
    names.extend(channel.impressions_column for channel in intent.paid_media)
    names.extend(organic.canonical_field or organic.field for organic in intent.organic_media)
    for control in intent.controls:
        lowered = control.lower()
        if lowered.endswith("_flag") or "promo" in lowered:
            names.append(control)
    return names


def float_model_columns(intent: ModelIntent) -> list[str]:
    skip = {"time", "geo", *integer_model_columns(intent)}
    return [column for column in model_ready_columns(intent) if column not in skip]


MODEL_READY_COLUMNS = model_ready_columns(DATASET_A_MODEL_INTENT)

INTEGER_MODEL_COLUMNS = integer_model_columns(DATASET_A_MODEL_INTENT)

FLOAT_MODEL_COLUMNS = float_model_columns(DATASET_A_MODEL_INTENT)
