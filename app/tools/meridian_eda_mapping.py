"""Derive official Meridian InputData mapping from the ModelReady contract.

Generic runtime never hard-codes Music Center column names. Tests may assert
Dataset A mapping produced from ModelIntent / MeridianInputContract.
"""

from __future__ import annotations

from app.core.errors import ValidationBlockedError
from app.core.meridian_eda_contracts import MeridianInputMapping
from app.core.model_intent import ModelIntent, ModelScope
from app.tools.meridian_contract import MeridianInputContract


def derive_kpi_type(intent: ModelIntent) -> tuple[str, str]:
    """Official Meridian kpi_type is 'revenue' or 'non_revenue'.

    Derived from ModelIntent KPI vs revenue canonical fields, not from the
    mere presence of a revenue_per_kpi column.
    """
    kpi = intent.kpi.canonical_field
    revenue = intent.revenue.canonical_field
    if not kpi or not revenue:
        raise ValidationBlockedError("ModelIntent KPI and revenue canonical fields are required.")
    if kpi == revenue:
        return (
            "revenue",
            "ModelIntent KPI canonical_field is the revenue field, so Meridian kpi_type=revenue.",
        )
    return (
        "non_revenue",
        "ModelIntent KPI canonical_field is distinct from revenue, "
        "so Meridian kpi_type=non_revenue.",
    )


def mapping_from_contract(
    *,
    intent: ModelIntent,
    contract: MeridianInputContract,
) -> MeridianInputMapping:
    kpi_type, derivation = derive_kpi_type(intent)
    channels = [channel.channel for channel in intent.paid_media]
    media_cols = [contract.media[channel] for channel in channels]
    spend_cols = [contract.media_spend[channel] for channel in channels]
    organic_cols = list(contract.organic_media)
    geo_col = contract.fields.geo if intent.model_scope is ModelScope.GEO else None
    population_col = (
        contract.fields.population if intent.model_scope is ModelScope.GEO else None
    )
    if intent.model_scope is ModelScope.GEO and (not geo_col or not population_col):
        raise ValidationBlockedError("Geo Meridian EDA requires geo and population fields.")
    if not media_cols or not spend_cols or not channels:
        raise ValidationBlockedError(
            "Meridian EDA requires paid media execution and spend columns."
        )
    if len(media_cols) != len(spend_cols) or len(media_cols) != len(channels):
        raise ValidationBlockedError("Paid media, spend, and channel lists must align.")
    return MeridianInputMapping(
        kpi_type=kpi_type,
        kpi_type_derivation=derivation,
        time_col=contract.fields.time,
        geo_col=geo_col,
        kpi_col=contract.fields.kpi,
        revenue_per_kpi_col=contract.fields.revenue_per_kpi,
        population_col=population_col,
        media_cols=media_cols,
        media_spend_cols=spend_cols,
        media_channels=channels,
        organic_media_cols=organic_cols,
        organic_media_channels=organic_cols,
        control_cols=list(contract.controls),
        model_scope=intent.model_scope.value,
    )
