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

MODEL_READY_COLUMNS = [
    "time",
    "geo",
    "kpi_orders",
    "kpi_revenue",
    "revenue_per_kpi",
    "population",
    "paid_search_impressions",
    "paid_search_spend",
    "shopping_impressions",
    "shopping_spend",
    "paid_social_impressions",
    "paid_social_spend",
    "organic_sessions",
    "consumer_sentiment_index",
    "competitor_discount_index",
    "music_center_promo",
]
