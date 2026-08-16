"""Reusable verified diagnostic snapshot. One load, many calculators."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from app.core.contracts import utc_now
from app.core.errors import ValidationBlockedError
from app.intelligence.contracts import KnotsSource, SourceMode
from app.tools.meridian_contract import MeridianInputContract


class ChannelSpec(BaseModel):
    channel: str
    impressions_column: str | None = None
    spend_column: str | None = None
    reach_column: str | None = None
    frequency_column: str | None = None
    organic_column: str | None = None
    provider: str | None = None
    is_paid: bool = True
    is_organic: bool = False
    is_rf: bool = False


class KnotsAssumption(BaseModel):
    n_knots: int
    n_knots_source: KnotsSource
    authority: str
    scope: str
    approved_for_final_modeling: bool = False
    rationale: str


class VerifiedEndpoint(BaseModel):
    run_id: str
    project_id: str
    dataset_id: str
    table_id: str
    view_id: str | None = None
    resolved_source: str
    source_mode: SourceMode
    input_fingerprint: str
    schema_fingerprint: str
    expected_fingerprint: str
    row_count: int
    queried_at: datetime = Field(default_factory=utc_now)
    consumption_view: str | None = None


class DiagnosticSnapshot(BaseModel):
    """In-memory verified model-consumption frame plus contract metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    endpoint: VerifiedEndpoint
    contract: MeridianInputContract
    frame: pd.DataFrame
    knots: KnotsAssumption
    time_grain: str = "weekly"
    model_scope: str = "geo"
    confirmed_confounders: list[str] = Field(default_factory=list)
    optional_predictors: list[str] = Field(default_factory=list)
    transformation_provenance: list[dict[str, Any]] = Field(default_factory=list)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    eda_receipt: dict[str, Any] | None = None
    semantic_answers: list[dict[str, Any]] = Field(default_factory=list)
    mapping_confidence: dict[str, str] = Field(default_factory=dict)

    @property
    def channels(self) -> list[ChannelSpec]:
        return channel_specs_from_contract(self.contract)

    @property
    def n_geos(self) -> int:
        if self.contract.fields.geo and self.contract.fields.geo in self.frame.columns:
            return int(self.frame[self.contract.fields.geo].nunique())
        return 1

    @property
    def n_times(self) -> int:
        return int(self.frame[self.contract.fields.time].nunique())

    @property
    def n_treatments(self) -> int:
        return len(self.contract.media) + len(self.contract.organic_media)

    @property
    def n_controls(self) -> int:
        return len(self.contract.controls)

    @property
    def n_paid_media(self) -> int:
        return len(self.contract.media)

    @property
    def kpi_column(self) -> str:
        return self.contract.fields.kpi

    @property
    def geo_column(self) -> str | None:
        return self.contract.fields.geo

    @property
    def time_column(self) -> str:
        return self.contract.fields.time

    @property
    def population_column(self) -> str | None:
        return self.contract.fields.population


def channel_specs_from_contract(contract: MeridianInputContract) -> list[ChannelSpec]:
    specs: list[ChannelSpec] = []
    for channel, impressions in contract.media.items():
        specs.append(
            ChannelSpec(
                channel=channel,
                impressions_column=impressions,
                spend_column=contract.media_spend.get(channel),
                provider=contract.channel_mappings.get(channel),
                is_paid=True,
            )
        )
    for organic in contract.organic_media:
        specs.append(
            ChannelSpec(
                channel=organic,
                organic_column=organic,
                is_paid=False,
                is_organic=True,
            )
        )
    return specs


def resolve_knots_assumption(
    *,
    frame: pd.DataFrame,
    contract: MeridianInputContract,
    eda_receipt: dict[str, Any] | None = None,
    modeler_n_knots: int | None = None,
) -> KnotsAssumption:
    n_times = int(frame[contract.fields.time].nunique())
    if n_times < 1:
        raise ValidationBlockedError("Cannot resolve n_knots: n_times is invalid.")
    if modeler_n_knots is not None:
        if modeler_n_knots < 1:
            raise ValidationBlockedError("modeler-provided n_knots must be >= 1.")
        return KnotsAssumption(
            n_knots=int(modeler_n_knots),
            n_knots_source=KnotsSource.MODELER_PROVIDED,
            authority="MODELER",
            scope="DIAGNOSTIC_ONLY",
            approved_for_final_modeling=False,
            rationale="Explicit modeler-provided diagnostic assumption. Not final ModelSpec.",
        )
    if eda_receipt:
        spec = eda_receipt.get("model_spec") or {}
        adequacy = eda_receipt.get("data_adequacy") or {}
        knots = spec.get("knots")
        if knots is None:
            knots = adequacy.get("n_knots")
        if isinstance(knots, int) and knots >= 1:
            source = (
                KnotsSource.EDA_ONLY_COMPATIBILITY
                if spec.get("source") not in {None, "MERIDIAN_DEFAULT"}
                or spec.get("approved_for_final_modeling") is False
                else KnotsSource.EDA_ONLY_COMPATIBILITY
            )
            return KnotsAssumption(
                n_knots=int(knots),
                n_knots_source=source,
                authority="OFFICIAL_MERIDIAN_EDA_COMPATIBILITY",
                scope="EDA_ONLY",
                approved_for_final_modeling=False,
                rationale=(
                    "Persisted EDA-only compatibility knots. Not a final ModelSpec "
                    "and not approved for posterior sampling."
                ),
            )
    time_only = _time_only_controls(frame, contract)
    if time_only:
        n_knots = max(1, n_times - 1)
        return KnotsAssumption(
            n_knots=n_knots,
            n_knots_source=KnotsSource.PRE_EDA_DIAGNOSTIC_ASSUMPTION,
            authority="PREM3_PRE_EDA_DIAGNOSTIC",
            scope="DIAGNOSTIC_ONLY",
            approved_for_final_modeling=False,
            rationale=(
                "Time-only controls detected. Diagnostic assumption uses n_times-1 "
                "to match official EDA identifiability. Not final ModelSpec."
            ),
        )
    return KnotsAssumption(
        n_knots=n_times,
        n_knots_source=KnotsSource.PRE_EDA_DIAGNOSTIC_ASSUMPTION,
        authority="PREM3_PRE_EDA_DIAGNOSTIC",
        scope="DIAGNOSTIC_ONLY",
        approved_for_final_modeling=False,
        rationale=(
            "No EDA receipt or modeler knots provided. Diagnostic assumption uses "
            "n_times. Not final ModelSpec."
        ),
    )


def _time_only_controls(frame: pd.DataFrame, contract: MeridianInputContract) -> list[str]:
    geo_col = contract.fields.geo
    time_col = contract.fields.time
    if not geo_col or geo_col not in frame.columns:
        return []
    found: list[str] = []
    for column in contract.controls:
        if column not in frame.columns:
            continue
        unique_per_time = frame.groupby(time_col, sort=False)[column].nunique(dropna=False)
        if not unique_per_time.empty and bool((unique_per_time <= 1).all()):
            found.append(column)
    return found
