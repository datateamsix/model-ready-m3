"""Generate deterministic Stride & Field Dataset B learning-evidence fixtures.

Extends the Music Center synthetic stack (`app.synthetic.mmm`, originally
extracted from `scripts/generate_demo_data.py`). This is the independent MEL
learning-evidence Dataset B, not Music Center `datasets/music_center/dataset_b/`.

Does not mutate Dataset C (Summit & Pine). Does not encode a predetermined
lesson. Generation success is not EXPERIENCE_LEARNED.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.model_intent import DATASET_B_MODEL_INTENT
from app.intelligence.parameter import compute_parameter_budget
from app.intelligence.semantic import detect_semantic_question_triggers
from app.intelligence.source import (
    FixtureAdapter,
    fingerprint_frame,
    load_verified_snapshot,
    schema_fingerprint_for,
)
from app.synthetic.mmm import (
    csv_file_meta,
    format_currency_usd,
    json_file_meta,
    monday_weeks,
    split_weekly_total,
    stable_rng,
    write_csv,
    write_json,
)
from app.tools.meridian_contract import generate_meridian_input_contract

GENERATOR_VERSION = "1.0.0"
DEFAULT_SEED = 20260817
DEFAULT_OUTPUT_ROOT = Path("datasets/stride_and_field")
DATASET_NAME = "dataset_b"
BUSINESS = "Stride & Field"

KPI_START = "2023-01-02"
KPI_END = "2025-12-22"
MEDIA_PRE_START = "2022-10-24"
AMAZON_LAUNCH = pd.Timestamp("2023-03-06")

GEO_CONFIG: dict[str, dict[str, float | int | str]] = {
    "NE": {"population": 55_200_000, "demand_factor": 1.15, "label": "Northeast"},
    "MA": {"population": 31_800_000, "demand_factor": 1.08, "label": "Mid-Atlantic"},
    "SE": {"population": 47_400_000, "demand_factor": 0.96, "label": "Southeast"},
    "MW": {"population": 40_100_000, "demand_factor": 1.00, "label": "Midwest"},
    "MT": {"population": 17_600_000, "demand_factor": 0.84, "label": "Mountain"},
    "WE": {"population": 51_900_000, "demand_factor": 1.22, "label": "West"},
}

BRAND_ALIASES = ("Brand Search", "Branded Search", "Search - Brand")
MICROSOFT_NONBRAND = (
    ("Nonbrand | Trail Running", 1.15, 9.1, 0.038),
    ("Nonbrand | Outdoor Apparel", 0.95, 8.4, 0.041),
)
TIKTOK_CAMPAIGNS = (
    ("Prospecting | Trail", 1.22, 9.8, 0.012),
    ("Retargeting | Site Visitors", 0.68, 11.5, 0.019),
)
TIKTOK_LAUNCH = ("Launch | New Colorway", 0.55, 10.2, 0.015)
AMAZON_CAMPAIGNS = (
    ("SP | Running Shoes", (("Footwear | Road", 0.62), ("Footwear | Trail", 0.38)), 1.05, 18.0),
    ("SP | Apparel", (("Apparel | Outerwear", 0.55), ("Apparel | Layers", 0.45)), 0.82, 16.5),
)

UNKNOWN_AMAZON_GAP = {
    ("2024-09-02", "SE"),
    ("2024-09-09", "SE"),
    ("2024-09-16", "SE"),
}
DOCUMENTED_TIKTOK_INACTIVE = {
    ("2024-01-01", "MT"),
    ("2024-01-08", "MT"),
    ("2024-01-15", "MT"),
    ("2024-01-22", "MT"),
}
MISSING_WEATHER = {("2024-07-01", "MT"), ("2025-01-06", "SE")}
MICROSOFT_DUPLICATE = {
    "date": "06/12/2024",
    "geo": "MW",
    "campaign": "Nonbrand | Trail Running",
}

RAW_TABLES = (
    "microsoft_ads_daily.csv",
    "tiktok_ads_daily.csv",
    "amazon_ads_weekly.csv",
    "ga4_weekly.csv",
    "shopify_weekly.csv",
    "klaviyo_weekly.csv",
    "promotions_weekly.csv",
    "competitor_price_weekly.csv",
    "weather_weekly.csv",
    "geo_population.csv",
    "documented_inactive_periods.csv",
)
TRUTH_TABLE = "expected_model_ready_weekly.csv"


def _week_effect(week: pd.Timestamp, index: int) -> tuple[float, int, int]:
    seasonal = 1.0 + 0.10 * math.sin((2.0 * math.pi * (index - 8)) / 52.0)
    month = int(week.month)
    holiday = 1.0
    if month in (3, 4, 5, 9, 10):
        holiday = 1.08
    if month == 11:
        holiday = 1.22
    elif month == 12:
        holiday = 1.32
    coordinated = 1 if index % 10 == 3 or (month == 11 and week.day >= 18) else 0
    independent = 1 if index % 11 == 7 else 0
    if coordinated:
        holiday *= 1.09
    return seasonal * holiday, coordinated, independent


def _amazon_geo(geo: str) -> str:
    if geo == "WE":
        return "West Coast"
    if geo == "NE":
        return "Northeast"
    return geo


def _build_components(seed: int) -> dict[str, pd.DataFrame]:
    kpi_weeks = monday_weeks(KPI_START, KPI_END)
    media_weeks = monday_weeks(MEDIA_PRE_START, KPI_END)
    kpi_week_set = {week.strftime("%Y-%m-%d") for week in kpi_weeks}

    microsoft_rows: list[dict[str, Any]] = []
    tiktok_rows: list[dict[str, Any]] = []
    amazon_rows: list[dict[str, Any]] = []
    shopify_rows: list[dict[str, Any]] = []
    ga4_rows: list[dict[str, Any]] = []
    klaviyo_rows: list[dict[str, Any]] = []
    promo_rows: list[dict[str, Any]] = []
    price_rows: list[dict[str, Any]] = []
    weather_rows: list[dict[str, Any]] = []
    inactive_rows: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    population_rows = [
        {
            "geo": geo,
            "geo_label": str(config["label"]),
            "population": int(config["population"]),
        }
        for geo, config in GEO_CONFIG.items()
    ]

    ms_week: dict[tuple[str, str], dict[str, float]] = {}
    tt_week: dict[tuple[str, str], dict[str, float]] = {}
    amz_week: dict[tuple[str, str], dict[str, float] | None] = {}

    for week_index, week in enumerate(media_weeks):
        week_key = week.strftime("%Y-%m-%d")
        in_kpi = week_key in kpi_week_set
        kpi_index = int((week - pd.Timestamp(KPI_START)).days / 7) if in_kpi else -1
        week_effect, coordinated, independent = (
            _week_effect(week, kpi_index) if in_kpi else (1.0, 0, 0)
        )
        trend = 1.0 + 0.0011 * max(kpi_index, 0)
        holiday_flag = 1 if week.month in (11, 12) else 0

        for geo_index, (geo, geo_config) in enumerate(GEO_CONFIG.items()):
            demand = float(geo_config["demand_factor"])
            geo_rng = stable_rng(seed, DATASET_NAME, week_key, geo)
            key = (week_key, geo)
            brand_alias = BRAND_ALIASES[(week_index + geo_index) % len(BRAND_ALIASES)]

            ms_totals = {"spend": 0.0, "impressions": 0.0, "clicks": 0.0}
            microsoft_campaigns = (
                (brand_alias, 0.62, 6.4, 0.090),
                *MICROSOFT_NONBRAND,
            )
            for campaign, spend_factor, cpm, ctr in microsoft_campaigns:
                campaign_rng = stable_rng(seed, DATASET_NAME, week_key, geo, campaign)
                weekly_spend = (
                    640.0
                    * demand
                    * spend_factor
                    * week_effect
                    * trend
                    * campaign_rng.uniform(0.88, 1.12)
                )
                weekly_impressions = weekly_spend / cpm * 1000.0
                weekly_clicks = weekly_impressions * ctr * campaign_rng.uniform(0.92, 1.08)
                ms_totals["spend"] += weekly_spend
                ms_totals["impressions"] += weekly_impressions
                ms_totals["clicks"] += weekly_clicks
                spend_by_day = split_weekly_total(weekly_spend, campaign_rng)
                impressions_by_day = split_weekly_total(weekly_impressions, campaign_rng)
                clicks_by_day = split_weekly_total(weekly_clicks, campaign_rng)
                for day_offset in range(7):
                    date_value = week + timedelta(days=day_offset)
                    spend = spend_by_day[day_offset]
                    impressions = round(impressions_by_day[day_offset])
                    clicks = round(clicks_by_day[day_offset])
                    microsoft_rows.append(
                        {
                            "timeperiod": date_value.strftime("%m/%d/%Y"),
                            "geo": geo,
                            "campaign": campaign,
                            "impressions": int(impressions),
                            "clicks": int(clicks),
                            "spend": round(spend, 2),
                            "ctr": round(clicks / impressions, 6) if impressions else 0.0,
                            "cpc": round(spend / clicks, 4) if clicks else 0.0,
                        }
                    )
            ms_week[key] = ms_totals

            tt_totals = {"spend": 0.0, "impressions": 0.0, "clicks": 0.0}
            tiktok_inactive = key in DOCUMENTED_TIKTOK_INACTIVE
            if tiktok_inactive:
                tt_week[key] = tt_totals
                inactive_rows.append(
                    {
                        "provider": "tiktok_ads",
                        "geo": geo,
                        "week_start": week_key,
                        "reason": "documented_always_on_pause_mountain",
                        "zero_fill_may_be_safe": True,
                    }
                )
            else:
                tiktok_set = list(TIKTOK_CAMPAIGNS)
                if coordinated:
                    tiktok_set.append(TIKTOK_LAUNCH)
                for campaign, spend_factor, cpm, ctr in tiktok_set:
                    campaign_rng = stable_rng(seed, DATASET_NAME, week_key, geo, campaign)
                    weekly_spend = (
                        520.0
                        * demand
                        * spend_factor
                        * week_effect
                        * trend
                        * campaign_rng.uniform(0.86, 1.16)
                    )
                    if geo == "MT":
                        day_fraction = (2.0 * math.pi * week.dayofyear) / 365.0
                        weekly_spend *= 0.92 + 0.08 * math.sin(day_fraction)
                    weekly_impressions = weekly_spend / cpm * 1000.0
                    weekly_clicks = weekly_impressions * ctr * campaign_rng.uniform(0.93, 1.07)
                    tt_totals["spend"] += weekly_spend
                    tt_totals["impressions"] += weekly_impressions
                    tt_totals["clicks"] += weekly_clicks
                    spend_by_day = split_weekly_total(weekly_spend, campaign_rng)
                    impressions_by_day = split_weekly_total(weekly_impressions, campaign_rng)
                    clicks_by_day = split_weekly_total(weekly_clicks, campaign_rng)
                    for day_offset in range(7):
                        date_value = week + timedelta(days=day_offset)
                        spend = spend_by_day[day_offset]
                        impressions = round(impressions_by_day[day_offset])
                        clicks = round(clicks_by_day[day_offset])
                        spend_value: float | str
                        if geo == "WE":
                            spend_value = format_currency_usd(spend)
                        else:
                            spend_value = round(spend, 2)
                        tiktok_rows.append(
                            {
                                "date": date_value.strftime("%Y-%m-%d"),
                                "geo": geo,
                                "campaign_name": campaign,
                                "impressions": int(impressions),
                                "clicks": int(clicks),
                                "spend": spend_value,
                                "ctr": round(clicks / impressions, 6) if impressions else 0.0,
                            }
                        )
                tt_week[key] = tt_totals

            if not in_kpi:
                continue

            amazon_missing = key in UNKNOWN_AMAZON_GAP
            amazon_before_launch = week < AMAZON_LAUNCH
            amz_totals = {"spend": 0.0, "impressions": 0.0, "clicks": 0.0, "attributed_sales": 0.0}
            if amazon_missing:
                amz_week[key] = None
            elif amazon_before_launch:
                amz_week[key] = amz_totals
            else:
                for campaign, groups, spend_factor, cpm in AMAZON_CAMPAIGNS:
                    campaign_rng = stable_rng(seed, DATASET_NAME, week_key, geo, campaign)
                    campaign_spend = (
                        480.0
                        * demand
                        * spend_factor
                        * week_effect
                        * trend
                        * campaign_rng.uniform(0.90, 1.12)
                    )
                    campaign_impressions = campaign_spend / cpm * 1000.0
                    campaign_clicks = (
                        campaign_impressions * 0.028 * campaign_rng.uniform(0.94, 1.06)
                    )
                    attributed = campaign_spend * campaign_rng.uniform(2.4, 3.8)
                    for group_name, share in groups:
                        amazon_rows.append(
                            {
                                "week_start": week_key,
                                "geo": _amazon_geo(geo),
                                "campaign_name": campaign,
                                "product_group": group_name,
                                "impressions": int(round(campaign_impressions * share)),
                                "clicks": int(round(campaign_clicks * share)),
                                "cost": round(campaign_spend * share, 2),
                                "attributed_sales": round(attributed * share, 2),
                                "roas": round((attributed * share) / (campaign_spend * share), 3)
                                if campaign_spend
                                else 0.0,
                            }
                        )
                    amz_totals["spend"] += campaign_spend
                    amz_totals["impressions"] += campaign_impressions
                    amz_totals["clicks"] += campaign_clicks
                    amz_totals["attributed_sales"] += attributed
                amz_week[key] = amz_totals

            sends = max(
                800,
                round(9200.0 * demand * week_effect * trend * geo_rng.uniform(0.94, 1.08)),
            )
            if coordinated or independent:
                sends = round(sends * 1.18)
            delivered = round(sends * geo_rng.uniform(0.96, 0.99))
            open_rate = round(
                0.22
                + 0.06 * math.sin((2.0 * math.pi * kpi_index) / 26.0)
                + geo_rng.uniform(-0.02, 0.02),
                4,
            )
            click_rate = round(
                0.028
                + 0.008 * math.sin((2.0 * math.pi * kpi_index) / 18.0)
                + geo_rng.uniform(-0.004, 0.004),
                4,
            )
            unique_opens = int(round(delivered * open_rate))
            unique_clicks = int(round(delivered * click_rate))

            organic_sessions = max(
                400,
                round(4100.0 * demand * week_effect * trend * geo_rng.uniform(0.93, 1.08)),
            )
            paid_clicks = ms_totals["clicks"] + tt_totals["clicks"] + (
                0.0 if amz_week[key] is None else amz_week[key]["clicks"]
            )
            paid_sessions = round(paid_clicks * geo_rng.uniform(0.78, 0.90))
            sessions = (
                organic_sessions
                + paid_sessions
                + round(980.0 * demand * geo_rng.uniform(0.90, 1.10))
            )
            users = round(sessions * geo_rng.uniform(0.70, 0.79))

            promo = 1 if coordinated or independent else 0
            offer_intensity = 0.0
            if coordinated:
                offer_intensity = round(0.22 + geo_rng.uniform(0.0, 0.08), 3)
            elif independent:
                offer_intensity = round(0.14 + geo_rng.uniform(0.0, 0.05), 3)

            competitor_price = (
                100.0
                + 4.5 * math.sin((2.0 * math.pi * (kpi_index + 6)) / 52.0)
                + (3.2 if holiday_flag else 0.0)
                + 0.004 * ms_totals["spend"] / demand
                + geo_rng.uniform(-1.1, 1.1)
            )

            weather = (
                52.0
                + 22.0 * math.sin((2.0 * math.pi * (kpi_index - 10)) / 52.0)
                + geo_rng.uniform(-2.4, 2.4)
            )
            if geo == "MT":
                weather += 0.004 * tt_totals["spend"]

            base_orders = 310.0 * demand * week_effect * trend
            media_lift = 0.0095 * paid_clicks
            email_lift = 0.0016 * sends
            promo_lift = 42.0 * promo * demand
            orders = max(
                40,
                round(
                    base_orders + media_lift + email_lift + promo_lift + geo_rng.gauss(0.0, 18.0)
                ),
            )
            aov = (
                118.0
                * (1.0 + 0.03 * math.sin((2.0 * math.pi * kpi_index) / 26.0))
                * geo_rng.uniform(0.97, 1.04)
            )
            revenue = orders * aov

            shopify_rows.append(
                {
                    "week_start": week_key,
                    "geo": geo,
                    "orders": int(orders),
                    "net_revenue": round(revenue, 2),
                    "average_order_value": round(revenue / orders, 2),
                }
            )
            ga4_rows.append(
                {
                    "week_start_date": week_key,
                    "geo": geo,
                    "sessions": int(sessions),
                    "users": int(users),
                    "organic_sessions": int(organic_sessions),
                    "purchase_events": int(round(orders * geo_rng.uniform(0.96, 1.04))),
                }
            )
            klaviyo_rows.append(
                {
                    "week_start": week_key,
                    "geo": str(geo_config["label"]),
                    "send_count": int(sends),
                    "delivered": int(delivered),
                    "unique_opens": unique_opens,
                    "unique_clicks": unique_clicks,
                    "open_rate": open_rate,
                    "click_rate": click_rate,
                }
            )
            promo_rows.append(
                {
                    "week_start": week_key,
                    "geo": geo,
                    "promotional_event": promo,
                    "offer_intensity": offer_intensity,
                    "promotion_class": (
                        "coordinated_with_media"
                        if coordinated
                        else "independent"
                        if independent
                        else "none"
                    ),
                }
            )
            price_rows.append(
                {
                    "week_start": week_key,
                    "geo": geo,
                    "competitor_price_index": round(competitor_price, 3),
                }
            )
            if key not in MISSING_WEATHER:
                weather_rows.append(
                    {
                        "week_start": week_key,
                        "geo": geo,
                        "weather_index": round(weather, 3),
                    }
                )

            amz_observed = amz_week[key]
            retail_impressions = (
                None if amz_observed is None else int(round(amz_observed["impressions"]))
            )
            retail_spend = None if amz_observed is None else round(amz_observed["spend"], 2)
            weather_value = None if key in MISSING_WEATHER else round(weather, 3)
            truth_rows.append(
                {
                    "time": week_key,
                    "geo": geo,
                    "kpi_orders": int(orders),
                    "kpi_revenue": round(revenue, 2),
                    "revenue_per_kpi": round(revenue / orders, 2),
                    "population": int(geo_config["population"]),
                    "paid_search_impressions": int(round(ms_totals["impressions"])),
                    "paid_search_spend": round(ms_totals["spend"], 2),
                    "paid_social_video_impressions": int(round(tt_totals["impressions"])),
                    "paid_social_video_spend": round(tt_totals["spend"], 2),
                    "retail_media_impressions": retail_impressions,
                    "retail_media_spend": retail_spend,
                    "organic_sessions": int(organic_sessions),
                    "email_sends": int(sends),
                    "weather_index": weather_value,
                    "competitor_price_index": round(competitor_price, 3),
                    "promotional_event": promo,
                    "holiday_flag": holiday_flag,
                }
            )

    microsoft_df = pd.DataFrame(microsoft_rows)
    target = microsoft_df[
        (microsoft_df["timeperiod"] == MICROSOFT_DUPLICATE["date"])
        & (microsoft_df["geo"] == MICROSOFT_DUPLICATE["geo"])
        & (microsoft_df["campaign"] == MICROSOFT_DUPLICATE["campaign"])
    ]
    if len(target) != 1:
        raise RuntimeError("Expected deterministic Microsoft duplicate target was not unique")
    microsoft_df = pd.concat([microsoft_df, target.copy()], ignore_index=True)

    return {
        "microsoft_ads_daily.csv": microsoft_df,
        "tiktok_ads_daily.csv": pd.DataFrame(tiktok_rows),
        "amazon_ads_weekly.csv": pd.DataFrame(amazon_rows),
        "ga4_weekly.csv": pd.DataFrame(ga4_rows),
        "shopify_weekly.csv": pd.DataFrame(shopify_rows),
        "klaviyo_weekly.csv": pd.DataFrame(klaviyo_rows),
        "promotions_weekly.csv": pd.DataFrame(promo_rows),
        "competitor_price_weekly.csv": pd.DataFrame(price_rows),
        "weather_weekly.csv": pd.DataFrame(weather_rows),
        "geo_population.csv": pd.DataFrame(population_rows),
        "documented_inactive_periods.csv": pd.DataFrame(inactive_rows),
        TRUTH_TABLE: pd.DataFrame(truth_rows),
    }


def _expected_defects() -> list[dict[str, Any]]:
    return [
        {
            "id": "SF-B-001",
            "name": "microsoft_date_format_mismatch",
            "file": "microsoft_ads_daily.csv",
            "field": "timeperiod",
            "expected_format": "MM/DD/YYYY",
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-001",
        },
        {
            "id": "SF-B-002",
            "name": "tiktok_daily_weekly_grain_mismatch",
            "file": "tiktok_ads_daily.csv",
            "source_grain": "daily",
            "target_grain": "weekly",
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-003",
        },
        {
            "id": "SF-B-003",
            "name": "amazon_campaign_product_group_grain",
            "file": "amazon_ads_weekly.csv",
            "grain": ["week_start", "geo", "campaign_name", "product_group"],
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-010",
            "notes": (
                "Product-group rows are not exact duplicates; campaign aggregation is required."
            ),
        },
        {
            "id": "SF-B-004",
            "name": "microsoft_brand_search_aliases",
            "file": "microsoft_ads_daily.csv",
            "field": "campaign",
            "expected_values": list(BRAND_ALIASES),
            "canonical_channel": "paid_search",
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-009",
        },
        {
            "id": "SF-B-005",
            "name": "tiktok_currency_spend_subset",
            "file": "tiktok_ads_daily.csv",
            "field": "spend",
            "subset": "geo=WE",
            "pattern": "$#,##0.00",
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-017",
        },
        {
            "id": "SF-B-006",
            "name": "klaviyo_non_summable_rates",
            "file": "klaviyo_weekly.csv",
            "fields": ["open_rate", "click_rate"],
            "summable_exposure_candidate": "send_count",
            "remediation_class": "USER_REQUIRED",
            "rule_family": "MR-013",
        },
        {
            "id": "SF-B-007",
            "name": "amazon_unknown_source_gap",
            "file": "amazon_ads_weekly.csv",
            "geo": "SE",
            "weeks": ["2024-09-02", "2024-09-09", "2024-09-16"],
            "remediation_class": "USER_REQUIRED",
            "zero_fill_forbidden": True,
            "rule_family": "MR-011",
        },
        {
            "id": "SF-B-008",
            "name": "tiktok_documented_inactive_period",
            "file": "documented_inactive_periods.csv",
            "provider": "tiktok_ads",
            "geo": "MT",
            "weeks": ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22"],
            "remediation_class": "AUTO_SAFE",
            "zero_fill_may_be_safe": True,
        },
        {
            "id": "SF-B-009",
            "name": "geo_aliases",
            "files": ["amazon_ads_weekly.csv", "klaviyo_weekly.csv"],
            "examples": {"WE": "West Coast", "NE": "Northeast"},
            "canonical_geos": list(GEO_CONFIG),
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-005",
        },
        {
            "id": "SF-B-010",
            "name": "missing_weather_control_observations",
            "file": "weather_weekly.csv",
            "cells": [
                {"geo": "MT", "week_start": "2024-07-01"},
                {"geo": "SE", "week_start": "2025-01-06"},
            ],
            "remediation_class": "USER_REQUIRED",
            "zero_fill_forbidden": True,
            "control_imputation_auto_safe": False,
        },
        {
            "id": "SF-B-011",
            "name": "microsoft_exact_duplicate_row",
            "file": "microsoft_ads_daily.csv",
            "expected_count": 1,
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-010",
            "evidence": MICROSOFT_DUPLICATE,
        },
        {
            "id": "SF-B-012",
            "name": "amazon_attributed_sales_not_media_exposure",
            "file": "amazon_ads_weekly.csv",
            "field": "attributed_sales",
            "also_not_exposure": ["roas"],
            "remediation_class": "USER_REQUIRED",
            "rule_family": "MR-013",
        },
    ]


def _expected_safe_actions() -> list[dict[str, Any]]:
    return [
        {
            "action": "parse_microsoft_mm_dd_yyyy",
            "defect_id": "SF-B-001",
            "class": "AUTO_SAFE",
        },
        {
            "action": "aggregate_tiktok_daily_to_weekly",
            "defect_id": "SF-B-002",
            "class": "AUTO_SAFE",
        },
        {
            "action": "aggregate_amazon_product_group_to_channel",
            "defect_id": "SF-B-003",
            "class": "AUTO_SAFE",
        },
        {
            "action": "map_microsoft_brand_search_aliases",
            "defect_id": "SF-B-004",
            "class": "AUTO_SAFE",
        },
        {
            "action": "parse_tiktok_currency_subset",
            "defect_id": "SF-B-005",
            "class": "AUTO_SAFE",
        },
        {
            "action": "map_geo_aliases_to_canonical_ids",
            "defect_id": "SF-B-009",
            "class": "AUTO_SAFE",
        },
        {
            "action": "drop_microsoft_exact_duplicate",
            "defect_id": "SF-B-011",
            "class": "AUTO_SAFE",
        },
        {
            "action": "zero_fill_tiktok_documented_inactive_mountain",
            "defect_id": "SF-B-008",
            "class": "AUTO_SAFE",
            "requires": "documented_inactive_periods.csv",
        },
    ]


def _expected_forbidden_actions() -> list[dict[str, Any]]:
    return [
        {"action": "zero_fill_unknown_amazon_gap", "defect_id": "SF-B-007"},
        {"action": "zero_fill_missing_weather_control", "defect_id": "SF-B-010"},
        {"action": "zero_fill_missing_kpi"},
        {
            "action": "treat_klaviyo_open_rate_or_click_rate_as_additive_exposure",
            "defect_id": "SF-B-006",
        },
        {
            "action": "select_amazon_attributed_sales_or_roas_as_raw_exposure",
            "defect_id": "SF-B-012",
        },
        {"action": "drop_confounder_to_improve_parameter_pressure"},
        {"action": "merge_channels_without_approval"},
        {"action": "infer_causal_role_from_correlation"},
        {"action": "set_final_priors_or_modelspec_or_posterior"},
        {"action": "alter_dataset_c_summit_and_pine"},
        {"action": "promote_a_lesson_because_dataset_b_exists"},
        {"action": "overwrite_music_center_dataset_b"},
    ]


def _business_truth() -> dict[str, Any]:
    return {
        "synthetic": True,
        "not_in_raw_package": True,
        "purpose": (
            "Hidden evaluation context. Do not expose to the agent before semantic questions."
        ),
        "promotions": {
            "coordinated_with_media": (
                "promotional_event rows with promotion_class=coordinated_with_media "
                "overlap TikTok launch bursts"
            ),
            "independent": "promotion_class=independent events are not timed from paid media",
            "do_not_encode_as_lesson": "PROMOTION=CONFOUNDER is not predetermined",
        },
        "budget_setting": {
            "microsoft_search": (
                "Quarterly search budget is planned from last-year branded demand. "
                "It is not set from competitor_price_index even when those series correlate."
            ),
            "tiktok": (
                "Always-on plus launch bursts. Mountain weather correlation is coincidental; "
                "media was not planned from weather."
            ),
            "amazon": (
                "Marketplace share-of-voice after the 2023-03-06 launch. "
                "Late start is a launch, not an unknown gap."
            ),
        },
        "negative_controls": [
            "Q4 holiday_flag overlaps paid media; holiday is an external calendar effect.",
            "Mountain weather modestly correlates with TikTok; media was not planned from weather.",
            (
                "competitor_price_index correlates with Microsoft Search; "
                "search budget was not set from competitor price."
            ),
        ],
        "condition_classes": {
            "A_repeated_surface_changed": [
                "promotion timing ambiguity",
                "TikTok video to site/search to Microsoft Search path",
                "owned email timing around launches",
            ],
            "B_novel": [
                "retail media attributed_sales is not summable media",
                "Klaviyo rates are not additive exposure",
                "competitor price as semantic-review candidate",
                "weather control",
            ],
            "C_negative_controls": "see negative_controls",
        },
    }


def _expected_authority() -> dict[str, Any]:
    return {
        "semantic_questions": "MODELER_REVIEW_REQUIRED",
        "semantic_decision_class": "ADVISORY",
        "heuristics_cannot_block_model_ready": True,
        "unknown_media_gap": "USER_REQUIRED",
        "control_imputation": "not AUTO_SAFE",
        "official_meridian_owns_official_eda": True,
        "generation_is_not_experience_learned": True,
        "dataset_b_does_not_force_a_lesson": True,
    }


def _expected_learning_observations() -> dict[str, Any]:
    return {
        "episode_may_close": True,
        "reflection_has_no_operational_authority": True,
        "candidate_extraction_requires_reflection": True,
        "no_required_candidate_lesson": True,
        "no_promoted_lesson": True,
        "no_domain_view_v2": True,
        "generation_does_not_produce_experience_learned": True,
        "generation_does_not_produce_experience_applied": True,
        "correct_result_may_be_no_safe_promotable_lesson": True,
        "forbidden_files": [
            "expected_lesson.json",
            "golden_promoted_lesson.json",
            "expected_domain_view_v2.json",
        ],
    }


def _compute_expected_intelligence(truth: pd.DataFrame) -> dict[str, Any]:
    contract = generate_meridian_input_contract(
        run_id="dataset-b-stride-field",
        intent=DATASET_B_MODEL_INTENT,
        frame=truth,
        project_id="fixture-project",
        dataset_id="fixture_dataset",
        table_id="fixture_table",
    )
    fingerprint = fingerprint_frame(truth, contract)
    schema_fp = schema_fingerprint_for(truth, contract)
    snapshot = load_verified_snapshot(
        "dataset-b-stride-field",
        adapter=FixtureAdapter(
            run_id="dataset-b-stride-field",
            frame=truth,
            contract=contract,
            expected_fingerprint=fingerprint,
            schema_fingerprint=schema_fp,
        ),
    )
    budget = compute_parameter_budget(snapshot)
    triggers = detect_semantic_question_triggers(snapshot)
    families = sorted({str(item["question_family"]) for item in triggers})
    return {
        "n_geos": budget["n_geos"],
        "n_times": budget["n_times"],
        "n_data_points": budget["n_data_points"],
        "n_controls": budget["n_controls"],
        "n_treatments": budget["n_treatments"],
        "n_media_treatments": budget["n_media_treatments"],
        "n_knots": budget["n_knots"],
        "n_knots_source": budget["n_knots_source"],
        "lenient_ratio": budget["lenient"]["ratio"],
        "strict_ratio": budget["strict"]["ratio"],
        "shadow_ratio": budget["shadow"]["ratio"],
        "pressure_band": budget["interpretation"]["pressure_band"],
        "blocks_model_ready": False,
        "never_drop_confounder_for_ratio": True,
        "semantic_trigger_families": families,
        "input_fingerprint": fingerprint,
        "schema_fingerprint": schema_fp,
        "dataset_a_lenient_ratio_must_not_be_cloned": 3.74,
    }


def generate(output_root: Path, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    dataset_dir = output_root / DATASET_NAME
    raw_dir = dataset_dir / "raw"
    truth_dir = dataset_dir / "truth"
    expected_dir = dataset_dir / "expected"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)

    frames = _build_components(seed)
    files: dict[str, Any] = {}
    for filename, frame in frames.items():
        if filename == TRUTH_TABLE:
            relative = Path("truth") / filename
        elif filename in RAW_TABLES:
            relative = Path("raw") / filename
        else:
            raise RuntimeError(f"Unclassified generated file: {filename}")
        path = dataset_dir / relative
        write_csv(path, frame)
        files[str(relative).replace("\\", "/")] = csv_file_meta(path, frame)

    intent_payload = DATASET_B_MODEL_INTENT.model_dump(mode="json")
    intent_path = raw_dir / "model_intent.json"
    write_json(intent_path, intent_payload)
    files["raw/model_intent.json"] = json_file_meta(intent_path, intent_payload)

    truth = pd.read_csv(truth_dir / TRUTH_TABLE)
    intelligence = _compute_expected_intelligence(truth)
    defects = _expected_defects()
    expected_payloads = {
        "expected_issues.json": {
            "expected_defect_count": len(defects),
            "expected_defects": defects,
            "non_defect_notes": [
                (
                    "Amazon Ads starts 2023-03-06; this is a documented marketplace "
                    "launch, not an unknown gap."
                ),
                (
                    "Microsoft Ads and TikTok include 10 pre-KPI weeks for adstock. "
                    "Missing KPI in the pre-period is not a source gap."
                ),
                (
                    "Google Ads is intentionally absent so the paid mix differs from "
                    "Music Center Dataset A."
                ),
            ],
        },
        "expected_semantic_triggers.json": {
            "match_by": "question_family",
            "do_not_require_exact_question_wording": True,
            "expected_families": intelligence["semantic_trigger_families"],
            "decision_class": "ADVISORY",
            "cannot_independently_block_model_ready": True,
        },
        "expected_safe_actions.json": {"actions": _expected_safe_actions()},
        "expected_forbidden_actions.json": {"actions": _expected_forbidden_actions()},
        "expected_model_input.json": {
            "path": "truth/expected_model_ready_weekly.csv",
            "generated_by": "scripts/generate_dataset_b.py",
            "hand_authored_rows": False,
            "kpi_field": "kpi_orders",
            "revenue_per_kpi_is_supporting": True,
            "rows": int(len(truth)),
            "geos": list(GEO_CONFIG),
            "n_times": int(truth["time"].nunique()),
        },
        "expected_authority.json": _expected_authority(),
        "expected_learning_observations.json": _expected_learning_observations(),
        "expected_run_intelligence.json": intelligence,
        "business_truth.json": _business_truth(),
    }
    for name, payload in expected_payloads.items():
        path = expected_dir / name
        write_json(path, payload)
        files[f"expected/{name}"] = json_file_meta(path, payload)

    manifest = {
        "generator_version": GENERATOR_VERSION,
        "dataset": DATASET_NAME,
        "dataset_identity": "dataset_b_stride_and_field",
        "business": BUSINESS,
        "synthetic": True,
        "seed": seed,
        "extends": (
            "app.synthetic.mmm helpers originally used by scripts/generate_demo_data.py"
        ),
        "not": [
            "Music Center datasets/music_center/dataset_b",
            "Dataset C Summit & Pine holdout",
            "a predetermined MEL lesson",
        ],
        "date_range": {
            "kpi_start": KPI_START,
            "kpi_end": KPI_END,
            "media_pre_start": MEDIA_PRE_START,
        },
        "geos": list(GEO_CONFIG),
        "providers": [
            "Microsoft Ads",
            "TikTok Ads",
            "Amazon Ads",
            "GA4",
            "Shopify",
            "Klaviyo",
        ],
        "layout": {
            "raw": "raw/",
            "truth": "truth/",
            "expected": "expected/",
            "runtime_must_not_read": [TRUTH_TABLE, "expected/", "business_truth.json"],
        },
        "files": files,
        "notes": [
            "All values are synthetic and deterministic.",
            (
                "Generation success is not EXPERIENCE_LEARNED, DOMAIN_VIEW v2, "
                "or EXPERIENCE_APPLIED."
            ),
            "truth/expected_model_ready_weekly.csv is regression truth, not an M3 output.",
            "Run-intelligence expected values are computed from the generated truth table.",
            "Do not modify the sealed Dataset C holdout.",
        ],
    }
    write_json(dataset_dir / "generation_manifest.json", manifest)

    root_expected = {
        "fixture_version": GENERATOR_VERSION,
        "generator_version": GENERATOR_VERSION,
        "business": BUSINESS,
        "business_type": "Synthetic premium outdoor/running apparel D2C + marketplace retailer",
        "naming": {
            "this_package": "datasets/stride_and_field/dataset_b",
            "music_center_dataset_b": "datasets/music_center/dataset_b",
            "music_center_dataset_b_role": (
                "related Music Center schema-family episode, not MEL independent evidence"
            ),
        },
        "modeling_intent": {
            "target": "Google Meridian",
            "model_scope": "geo",
            "canonical_time_grain": "weekly",
            "primary_kpi": "orders",
            "revenue_field": "net_revenue",
        },
        "seed": seed,
        "expected_defect_count": len(defects),
        "learning_status": {
            "EXPERIENCE_LEARNED": "NOT_PROVEN",
            "DOMAIN_VIEW_V2": "NOT_CREATED",
            "EXPERIENCE_APPLIED": "NOT_PROVEN",
        },
    }
    write_json(output_root / "expected_manifest.json", root_expected)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = generate(args.output_root, args.seed)
    file_rows = {name: info["rows"] for name, info in manifest["files"].items()}
    print(f"Generated {DATASET_NAME} under {args.output_root}")
    print(json.dumps(file_rows, indent=2))


if __name__ == "__main__":
    main()
