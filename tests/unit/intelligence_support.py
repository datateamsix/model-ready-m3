"""Helpers for PreM3 run-intelligence unit tests."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from app.core.model_intent import (
    DATASET_A_MODEL_INTENT,
    DATASET_B_MODEL_INTENT,
    DATASET_C_MODEL_INTENT,
)
from app.intelligence.snapshot import DiagnosticSnapshot
from app.intelligence.source import (
    FixtureAdapter,
    fingerprint_frame,
    load_verified_snapshot,
    schema_fingerprint_for,
)
from app.synthetic.paths import DATASET_A_DIR, DATASET_B_DIR, DATASET_C_DIR
from app.tools.meridian_contract import MeridianInputContract, generate_meridian_input_contract

DATASET_A_TRUTH = DATASET_A_DIR / "truth" / "expected_model_ready_weekly.csv"
DATASET_B_TRUTH = DATASET_B_DIR / "truth" / "expected_model_ready_weekly.csv"
DATASET_C_TRUTH = DATASET_C_DIR / "truth" / "expected_model_ready_weekly.csv"


def dataset_a_snapshot(run_id: str = "dataset-a-intel") -> DiagnosticSnapshot:
    frame = pd.read_csv(DATASET_A_TRUTH)
    contract = generate_meridian_input_contract(
        run_id=run_id,
        intent=DATASET_A_MODEL_INTENT,
        frame=frame,
        project_id="fixture-project",
        dataset_id="fixture_dataset",
        table_id="fixture_table",
    )
    return snapshot_from_frame(run_id, frame, contract)


def dataset_b_snapshot(run_id: str = "dataset-b-intel") -> DiagnosticSnapshot:
    frame = pd.read_csv(DATASET_B_TRUTH)
    contract = generate_meridian_input_contract(
        run_id=run_id,
        intent=DATASET_B_MODEL_INTENT,
        frame=frame,
        project_id="fixture-project",
        dataset_id="fixture_dataset",
        table_id="fixture_table",
    )
    return snapshot_from_frame(run_id, frame, contract)


def dataset_c_snapshot(run_id: str = "dataset-c-intel") -> DiagnosticSnapshot:
    frame = pd.read_csv(DATASET_C_TRUTH)
    contract = generate_meridian_input_contract(
        run_id=run_id,
        intent=DATASET_C_MODEL_INTENT,
        frame=frame,
        project_id="fixture-project",
        dataset_id="fixture_dataset",
        table_id="fixture_table",
    )
    return snapshot_from_frame(run_id, frame, contract)


def snapshot_from_frame(
    run_id: str,
    frame: pd.DataFrame,
    contract: MeridianInputContract,
    *,
    confirmed_confounders: list[str] | None = None,
    optional_predictors: list[str] | None = None,
    transformation_provenance: list[dict] | None = None,
    issues: list[dict] | None = None,
    eda_receipt: dict | None = None,
    modeler_n_knots: int | None = None,
) -> DiagnosticSnapshot:
    fp = fingerprint_frame(frame, contract)
    schema_fp = schema_fingerprint_for(frame, contract)
    adapter = FixtureAdapter(
        run_id=run_id,
        frame=frame,
        contract=contract,
        expected_fingerprint=fp,
        schema_fingerprint=schema_fp,
        confirmed_confounders=confirmed_confounders,
        optional_predictors=optional_predictors,
        transformation_provenance=transformation_provenance,
        issues=issues,
        eda_receipt=eda_receipt,
        modeler_n_knots=modeler_n_knots,
    )
    return load_verified_snapshot(run_id, adapter=adapter)


def weekly_frame(
    *,
    geos: list[str],
    periods: int,
    start: date = date(2024, 1, 1),
    treatments: int = 2,
    controls: int = 1,
    include_promo: bool = False,
    include_price: bool = False,
    gqv: bool = False,
    remarketing: bool = False,
    flat_channel: str | None = None,
) -> tuple[pd.DataFrame, MeridianInputContract]:
    rows: list[dict] = []
    for geo_index, geo in enumerate(geos):
        for week in range(periods):
            day = start + timedelta(days=7 * week)
            row: dict = {
                "time": day.isoformat(),
                "geo": geo,
                "kpi_orders": 100 + week + geo_index,
                "kpi_revenue": 1000 + week,
                "revenue_per_kpi": 10.0,
                "population": 1_000_000 * (geo_index + 1),
            }
            for idx in range(treatments):
                spend = 10.0 * (idx + 1) * (week + 1)
                impressions = spend * 100
                if flat_channel == f"ch{idx}":
                    spend = 5.0
                    impressions = 500.0
                row[f"ch{idx}_impressions"] = impressions
                row[f"ch{idx}_spend"] = spend
            if remarketing:
                row["retargeting_impressions"] = 50 + week
                row["retargeting_spend"] = 8.0
            row["organic_sessions"] = 20 + week
            for idx in range(controls):
                row[f"control_{idx}"] = 1.0 + (week * 0.01)
            if include_promo:
                row["music_center_promo"] = 1 if week % 13 == 0 else 0
            if include_price:
                row["competitor_discount_index"] = 0.1 + week * 0.001
            if gqv:
                row["branded_search_volume"] = 200 + week * 3
            rows.append(row)
    frame = pd.DataFrame(rows)
    media = {f"ch{idx}": f"ch{idx}_impressions" for idx in range(treatments)}
    spend = {f"ch{idx}": f"ch{idx}_spend" for idx in range(treatments)}
    if remarketing:
        media["retargeting"] = "retargeting_impressions"
        spend["retargeting"] = "retargeting_spend"
    control_cols = [f"control_{idx}" for idx in range(controls)]
    if include_promo:
        control_cols.append("music_center_promo")
    if include_price:
        control_cols.append("competitor_discount_index")
    contract = MeridianInputContract(
        run_id="synthetic",
        target="google_meridian",
        model_scope="geo" if len(geos) > 1 else "national",
        source={"project_id": "p", "dataset_id": "d", "table_id": "t"},
        fields={
            "time": "time",
            "geo": "geo",
            "kpi": "kpi_orders",
            "revenue_per_kpi": "revenue_per_kpi",
            "population": "population",
        },
        media=media,
        media_spend=spend,
        organic_media=["organic_sessions"],
        controls=control_cols,
        channel_mappings={name: "test" for name in media},
        status="COMPLETE",
    )
    return frame, contract
