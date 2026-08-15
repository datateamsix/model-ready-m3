"""Deterministic Meridian handoff contract (MR-020). Does not choose priors."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from app.core.errors import ValidationBlockedError
from app.core.model_intent import ModelIntent, ModelScope


class MeridianSource(BaseModel):
    project_id: str
    dataset_id: str
    table_id: str


class MeridianFields(BaseModel):
    time: str
    geo: str | None = None
    kpi: str
    revenue_per_kpi: str
    population: str | None = None


class MeridianInputContract(BaseModel):
    run_id: str
    target: str
    model_scope: str
    source: MeridianSource
    fields: MeridianFields
    media: dict[str, str] = Field(default_factory=dict)
    media_spend: dict[str, str] = Field(default_factory=dict)
    organic_media: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    channel_mappings: dict[str, str] = Field(default_factory=dict)
    status: str


def generate_meridian_input_contract(
    *,
    run_id: str,
    intent: ModelIntent,
    frame: pd.DataFrame,
    project_id: str,
    dataset_id: str,
    table_id: str,
) -> MeridianInputContract:
    columns = set(frame.columns)
    kpi = intent.kpi.canonical_field or "kpi_orders"
    required = {"time", kpi}
    if intent.model_scope is ModelScope.GEO:
        required.update({"geo", "population"})
    media = {channel.channel: channel.impressions_column for channel in intent.paid_media}
    spend = {channel.channel: channel.spend_column for channel in intent.paid_media}
    organic = [
        item.canonical_field or item.field
        for item in intent.organic_media
        if item.canonical_field or item.field
    ]
    missing = sorted(name for name in required if name not in columns)
    for column in [*media.values(), *spend.values(), *organic, *intent.controls, "revenue_per_kpi"]:
        if column not in columns:
            missing.append(column)
    complete = (
        bool(project_id) and bool(dataset_id) and bool(table_id) and not missing and kpi in columns
    )
    if not complete:
        raise ValidationBlockedError(
            "Meridian input contract is incomplete: "
            f"missing_fields={sorted(set(missing))} source={project_id}.{dataset_id}.{table_id}"
        )
    return MeridianInputContract(
        run_id=run_id,
        target=intent.target.value,
        model_scope=intent.model_scope.value,
        source=MeridianSource(project_id=project_id, dataset_id=dataset_id, table_id=table_id),
        fields=MeridianFields(
            time="time",
            geo="geo" if intent.model_scope is ModelScope.GEO else None,
            kpi=kpi,
            revenue_per_kpi="revenue_per_kpi",
            population="population" if intent.model_scope is ModelScope.GEO else None,
        ),
        media=media,
        media_spend=spend,
        organic_media=organic,
        controls=list(intent.controls),
        channel_mappings={channel.channel: channel.provider for channel in intent.paid_media},
        status="COMPLETE",
    )


def contract_to_json(contract: MeridianInputContract) -> dict[str, Any]:
    return contract.model_dump(mode="json")
