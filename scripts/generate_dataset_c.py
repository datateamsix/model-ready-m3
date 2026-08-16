"""Generate the sealed Summit & Pine Dataset C holdout.

Extends the Music Center synthetic stack (`app.synthetic.mmm`). This is the
independent MEL evaluation holdout, not training evidence. Seed `20260816` is
kept from the Episode Core placeholder. Generator 2.0.0 replaces that stub
with the hospitality assignment before any real lesson promotion.

Do not design this package around a CandidateLesson. Generation is not
EXPERIENCE_LEARNED or EXPERIENCE_APPLIED. DOMAIN_VIEW is not modified.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.model_intent import DATASET_C_MODEL_INTENT
from app.domain.intelligence.builder import load_current_domain_view
from app.intelligence.orchestrator import run_pre_eda_diagnostics
from app.intelligence.parameter import compute_parameter_budget
from app.intelligence.semantic import detect_semantic_question_triggers
from app.intelligence.source import (
    FixtureAdapter,
    fingerprint_frame,
    load_verified_snapshot,
    schema_fingerprint_for,
)
from app.mel.fingerprint import fingerprint_payload
from app.mel.holdout import seal_holdout
from app.mel.models import DatasetRole
from app.response.builder import ResponseBuilder
from app.response.validate import ResponseContractError
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
from app.synthetic.paths import SUMMIT_AND_PINE_ROOT
from app.tools.meridian_contract import generate_meridian_input_contract

GENERATOR_VERSION = "2.0.0"
DEFAULT_SEED = 20260816
DEFAULT_OUTPUT_ROOT = SUMMIT_AND_PINE_ROOT
DATASET_NAME = "dataset_c"
BUSINESS = "Summit & Pine"
SEALED_AT = "2026-08-16T19:00:00+00:00"
DOMAIN_VIEW_VERSION_AT_SEAL = "1.0.0"
DOMAIN_VIEW_FINGERPRINT_AT_SEAL = (
    "b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf"
)

KPI_START = "2022-11-07"
KPI_END = "2025-10-27"
MEDIA_PRE_START = "2022-08-29"
PINTEREST_LAUNCH = pd.Timestamp("2023-02-06")

GEO_CONFIG: dict[str, dict[str, float | int | str]] = {
    "CO": {
        "population": 5_800_000,
        "demand_factor": 1.18,
        "label": "Colorado Rockies",
        "ski": 1.0,
    },
    "UT": {
        "population": 3_400_000,
        "demand_factor": 1.05,
        "label": "Utah Wasatch",
        "ski": 0.95,
    },
    "CA": {
        "population": 8_200_000,
        "demand_factor": 1.12,
        "label": "Northern California",
        "ski": 0.55,
    },
    "PN": {
        "population": 6_100_000,
        "demand_factor": 0.98,
        "label": "Pacific Northwest",
        "ski": 0.72,
    },
    "NE": {
        "population": 7_400_000,
        "demand_factor": 0.88,
        "label": "New England",
        "ski": 0.80,
    },
}

GEO_ALIASES = {
    "CO": ("CO Rockies", "Colorado", "Rockies"),
    "UT": ("Wasatch", "Utah", "UT"),
    "CA": ("NorCal", "Northern California", "CA"),
    "PN": ("PNW", "Pacific Northwest", "PN"),
    "NE": ("New England", "NE", "NewEngland"),
}

GOOGLE_BRAND = ("Brand | Lodge", "Branded | Destination", "Search - Lodge")
GOOGLE_NONBRAND = (
    ("Nonbrand | Ski Weekend", 1.12, 7.8, 0.062),
    ("Nonbrand | Cabin Stay", 0.90, 8.4, 0.048),
)
PINTEREST_CAMPAIGNS = (
    ("Inspiration | Winter", 1.15, 6.4, 0.011),
    ("Inspiration | Summer", 0.82, 5.8, 0.013),
)
META_PROSPECTING = (
    ("Prospecting | Destination", "Destination", 1.05, 9.2, 0.014),
    ("Prospect | Awareness", "Awareness", 0.78, 8.6, 0.012),
)
META_RETARGETING = (
    ("Retargeting | Abandoned Search", "Abandoned Search", 0.88, 11.4, 0.028),
    ("Remarketing | Site Visitors", "Site Visitors", 0.70, 10.8, 0.024),
)

UNKNOWN_GOOGLE_GAP = {
    ("2024-06-03", "CA"),
    ("2024-06-10", "CA"),
    ("2024-06-17", "CA"),
}
DOCUMENTED_META_INACTIVE = {
    ("2024-04-01", "PN"),
    ("2024-04-08", "PN"),
    ("2024-04-15", "PN"),
    ("2024-04-22", "PN"),
}
MISSING_AVAILABILITY = {("2024-10-07", "CO")}
GOOGLE_DUPLICATE = {
    "date": "2024-02-06",
    "geo": "CO Rockies",
    "campaign": "Nonbrand | Ski Weekend",
}
META_RETARGET_DUPLICATE = {
    "week_start": "2024-01-08",
    "geo": "UT",
    "campaign_name": "Retargeting | Abandoned Search",
    "adset_name": "Abandoned Search",
}

RAW_TABLES = (
    "google_ads_daily.csv",
    "pinterest_ads_daily.csv",
    "meta_ads_prospecting_weekly.csv",
    "meta_ads_retargeting_weekly.csv",
    "ga4_weekly.csv",
    "pms_bookings_weekly.csv",
    "stripe_weekly.csv",
    "klaviyo_weekly.csv",
    "promotions_weekly.csv",
    "availability_weekly.csv",
    "adr_weekly.csv",
    "weather_weekly.csv",
    "holiday_calendar_weekly.csv",
    "geo_population.csv",
    "documented_inactive_periods.csv",
)
TRUTH_TABLE = "expected_model_ready_weekly.csv"


def _holiday_flag(week: pd.Timestamp) -> tuple[int, str]:
    month = int(week.month)
    day = int(week.day)
    if month == 11 and 18 <= day <= 28:
        return 1, "Thanksgiving"
    if month == 12 and day >= 22:
        return 1, "Christmas_NewYear"
    if month == 1 and day <= 7:
        return 1, "Christmas_NewYear"
    if month == 2 and 12 <= day <= 21:
        return 1, "Presidents_Day"
    if month == 5 and day >= 25:
        return 1, "Memorial_Day"
    if month == 9 and day <= 7:
        return 1, "Labor_Day"
    return 0, ""


def _week_effect(week: pd.Timestamp, index: int) -> tuple[float, int, int, str]:
    seasonal = 1.0 + 0.16 * math.sin((2.0 * math.pi * (index - 4)) / 52.0)
    month = int(week.month)
    holiday, holiday_name = _holiday_flag(week)
    coordinated = 0
    independent = 0
    package = "none"
    if month in (12, 1, 2, 3) and index % 9 == 2:
        coordinated = 1
        package = "Ski & Stay"
        seasonal *= 1.10
    elif month in (6, 7, 8) and index % 10 == 4:
        coordinated = 1
        package = "Summer Adventure"
        seasonal *= 1.08
    elif month in (9, 10) and index % 11 == 6:
        independent = 1
        package = "Fall Weekend"
        seasonal *= 1.05
    elif holiday and holiday_name in {"Christmas_NewYear", "Thanksgiving"}:
        if index % 2 == 0:
            coordinated = 1
            package = "Holiday Escape"
            seasonal *= 1.12
    if holiday:
        seasonal *= 1.06
    return seasonal, coordinated, independent, package


def _geo_alias(geo: str, week_index: int, geo_index: int) -> str:
    aliases = GEO_ALIASES[geo]
    return aliases[(week_index + geo_index) % len(aliases)]


def _snowfall(week: pd.Timestamp, geo: str, index: int, rng: Any) -> float:
    ski = float(GEO_CONFIG[geo]["ski"])
    winter = 1.0 if week.month in (11, 12, 1, 2, 3) else 0.18
    base = 18.0 + 62.0 * ski * winter * (
        0.55 + 0.45 * math.sin((2.0 * math.pi * (index - 6)) / 52.0)
    )
    return max(0.0, base + rng.uniform(-4.0, 4.0))


def _build_components(seed: int) -> dict[str, pd.DataFrame]:
    kpi_weeks = monday_weeks(KPI_START, KPI_END)
    media_weeks = monday_weeks(MEDIA_PRE_START, KPI_END)
    kpi_week_set = {week.strftime("%Y-%m-%d") for week in kpi_weeks}

    google_rows: list[dict[str, Any]] = []
    pinterest_rows: list[dict[str, Any]] = []
    prospect_rows: list[dict[str, Any]] = []
    retarget_rows: list[dict[str, Any]] = []
    pms_rows: list[dict[str, Any]] = []
    stripe_rows: list[dict[str, Any]] = []
    ga4_rows: list[dict[str, Any]] = []
    klaviyo_rows: list[dict[str, Any]] = []
    promo_rows: list[dict[str, Any]] = []
    availability_rows: list[dict[str, Any]] = []
    adr_rows: list[dict[str, Any]] = []
    weather_rows: list[dict[str, Any]] = []
    holiday_rows: list[dict[str, Any]] = []
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
    holiday_seen: set[str] = set()

    google_week: dict[tuple[str, str], dict[str, float] | None] = {}
    pin_week: dict[tuple[str, str], dict[str, float]] = {}
    prospect_week: dict[tuple[str, str], dict[str, float]] = {}
    retarget_week: dict[tuple[str, str], dict[str, float]] = {}

    for week_index, week in enumerate(media_weeks):
        week_key = week.strftime("%Y-%m-%d")
        in_kpi = week_key in kpi_week_set
        kpi_index = int((week - pd.Timestamp(KPI_START)).days / 7) if in_kpi else -1
        week_effect, coordinated, independent, package = (
            _week_effect(week, kpi_index) if in_kpi else (1.0, 0, 0, "none")
        )
        holiday_flag, holiday_name = _holiday_flag(week)
        trend = 1.0 + 0.0009 * max(kpi_index, 0)
        if week_key not in holiday_seen:
            holiday_rows.append(
                {
                    "week_start": week_key,
                    "holiday_flag": holiday_flag,
                    "holiday_name": holiday_name,
                }
            )
            holiday_seen.add(week_key)

        for geo_index, (geo, geo_config) in enumerate(GEO_CONFIG.items()):
            demand = float(geo_config["demand_factor"])
            ski = float(geo_config["ski"])
            geo_rng = stable_rng(seed, DATASET_NAME, week_key, geo)
            key = (week_key, geo)
            alias = _geo_alias(geo, week_index, geo_index)

            snowfall = _snowfall(week, geo, max(kpi_index, 0), geo_rng)
            temperature = (
                42.0
                - 18.0 * ski * (1.0 if week.month in (12, 1, 2) else 0.25)
                + geo_rng.uniform(-3.0, 3.0)
            )
            precipitation = max(
                0.0,
                1.4
                + 0.8 * math.sin((2.0 * math.pi * (week.dayofyear + geo_index)) / 365.0)
                + geo_rng.uniform(-0.3, 0.3),
            )

            google_missing = key in UNKNOWN_GOOGLE_GAP
            google_totals = {"spend": 0.0, "impressions": 0.0, "clicks": 0.0}
            if google_missing:
                google_week[key] = None
            else:
                brand_alias = GOOGLE_BRAND[(week_index + geo_index) % len(GOOGLE_BRAND)]
                holiday_search = 1.18 if holiday_flag else 1.0
                google_campaigns = (
                    (brand_alias, 0.70, 5.9, 0.095),
                    *GOOGLE_NONBRAND,
                )
                for campaign, spend_factor, cpm, ctr in google_campaigns:
                    campaign_rng = stable_rng(
                        seed, DATASET_NAME, week_key, geo, campaign
                    )
                    weekly_spend = (
                        580.0
                        * demand
                        * spend_factor
                        * week_effect
                        * trend
                        * holiday_search
                        * campaign_rng.uniform(0.88, 1.14)
                    )
                    weekly_impressions = weekly_spend / cpm * 1000.0
                    weekly_clicks = (
                        weekly_impressions * ctr * campaign_rng.uniform(0.92, 1.08)
                    )
                    google_totals["spend"] += weekly_spend
                    google_totals["impressions"] += weekly_impressions
                    google_totals["clicks"] += weekly_clicks
                    spend_by_day = split_weekly_total(weekly_spend, campaign_rng)
                    impressions_by_day = split_weekly_total(
                        weekly_impressions, campaign_rng
                    )
                    clicks_by_day = split_weekly_total(weekly_clicks, campaign_rng)
                    for day_offset in range(7):
                        date_value = week + timedelta(days=day_offset)
                        spend = spend_by_day[day_offset]
                        impressions = max(1, round(impressions_by_day[day_offset]))
                        clicks = max(0, round(clicks_by_day[day_offset]))
                        cost_micros = int(round(spend * 1_000_000))
                        google_rows.append(
                            {
                                "date": date_value.strftime("%Y-%m-%d"),
                                "geo": alias,
                                "campaign": campaign,
                                "impressions": int(impressions),
                                "clicks": int(clicks),
                                "cost_micros": cost_micros,
                                "ctr": round(clicks / impressions, 6)
                                if impressions
                                else 0.0,
                                "cpa": round(spend / max(clicks, 1), 4),
                            }
                        )
                google_week[key] = google_totals

            pin_totals = {"spend": 0.0, "impressions": 0.0, "clicks": 0.0}
            if week < PINTEREST_LAUNCH:
                pin_week[key] = pin_totals
            else:
                weather_coincidence = 1.0
                if geo == "CO":
                    weather_coincidence = 1.0 + 0.0022 * snowfall
                for campaign, spend_factor, cpm, ctr in PINTEREST_CAMPAIGNS:
                    campaign_rng = stable_rng(
                        seed, DATASET_NAME, week_key, geo, campaign
                    )
                    burst = 1.22 if coordinated else 0.78 + 0.22 * week_effect
                    weekly_spend = (
                        310.0
                        * demand
                        * spend_factor
                        * burst
                        * trend
                        * weather_coincidence
                        * campaign_rng.uniform(0.84, 1.18)
                    )
                    weekly_impressions = weekly_spend / cpm * 1000.0
                    weekly_clicks = (
                        weekly_impressions * ctr * campaign_rng.uniform(0.93, 1.07)
                    )
                    pin_totals["spend"] += weekly_spend
                    pin_totals["impressions"] += weekly_impressions
                    pin_totals["clicks"] += weekly_clicks
                    spend_by_day = split_weekly_total(weekly_spend, campaign_rng)
                    impressions_by_day = split_weekly_total(
                        weekly_impressions, campaign_rng
                    )
                    clicks_by_day = split_weekly_total(weekly_clicks, campaign_rng)
                    for day_offset in range(7):
                        date_value = week + timedelta(days=day_offset)
                        spend = spend_by_day[day_offset]
                        impressions = max(1, round(impressions_by_day[day_offset]))
                        clicks = max(0, round(clicks_by_day[day_offset]))
                        pinterest_rows.append(
                            {
                                "date": date_value.strftime("%Y-%m-%d"),
                                "geo": geo,
                                "campaign_name": campaign,
                                "impressions": int(impressions),
                                "clicks": int(clicks),
                                "spend": round(spend, 2),
                                "ctr": round(clicks / impressions, 6)
                                if impressions
                                else 0.0,
                            }
                        )
                pin_week[key] = pin_totals

            if not in_kpi:
                continue

            prospect_inactive = key in DOCUMENTED_META_INACTIVE
            prospect_totals = {"spend": 0.0, "impressions": 0.0, "clicks": 0.0}
            if prospect_inactive:
                prospect_week[key] = prospect_totals
                inactive_rows.append(
                    {
                        "provider": "meta_ads",
                        "channel": "paid_social_prospecting",
                        "geo": geo,
                        "week_start": week_key,
                        "reason": "documented_campaign_off_pacific_northwest",
                        "zero_fill_may_be_safe": True,
                    }
                )
            else:
                avail_season = 0.78 + 0.22 * (
                    0.5
                    + 0.5 * math.sin((2.0 * math.pi * (kpi_index - 8)) / 52.0)
                )
                ut_seasonal = (0.90 + 0.12 * avail_season) if geo == "UT" else 1.0
                for campaign, adset, spend_factor, cpm, ctr in META_PROSPECTING:
                    campaign_rng = stable_rng(
                        seed, DATASET_NAME, week_key, geo, campaign
                    )
                    weekly_spend = (
                        420.0
                        * demand
                        * spend_factor
                        * week_effect
                        * trend
                        * ut_seasonal
                        * (1.16 if coordinated else 1.0)
                        * campaign_rng.uniform(0.86, 1.14)
                    )
                    weekly_impressions = weekly_spend / cpm * 1000.0
                    weekly_clicks = (
                        weekly_impressions * ctr * campaign_rng.uniform(0.93, 1.07)
                    )
                    prospect_totals["spend"] += weekly_spend
                    prospect_totals["impressions"] += weekly_impressions
                    prospect_totals["clicks"] += weekly_clicks
                    prospect_rows.append(
                        {
                            "week_start": week_key,
                            "geo": geo,
                            "campaign_name": campaign,
                            "adset_name": adset,
                            "impressions": int(round(weekly_impressions)),
                            "clicks": int(round(weekly_clicks)),
                            "amount_spent": round(weekly_spend, 2),
                        }
                    )
                prospect_week[key] = prospect_totals

            organic_sessions = max(
                280,
                round(
                    2400.0 * demand * week_effect * trend * geo_rng.uniform(0.92, 1.09)
                ),
            )
            availability_searches = max(
                40,
                round(organic_sessions * geo_rng.uniform(0.18, 0.28)),
            )
            abandoned = max(
                8,
                round(availability_searches * geo_rng.uniform(0.22, 0.38)),
            )
            retarget_pool = organic_sessions + 2.4 * availability_searches + 3.1 * abandoned
            retarget_totals = {"spend": 0.0, "impressions": 0.0, "clicks": 0.0}
            for campaign, adset, spend_factor, cpm, ctr in META_RETARGETING:
                campaign_rng = stable_rng(seed, DATASET_NAME, week_key, geo, campaign)
                weekly_spend = (
                    0.085
                    * retarget_pool
                    * spend_factor
                    * demand
                    * campaign_rng.uniform(0.90, 1.10)
                )
                weekly_impressions = weekly_spend / cpm * 1000.0
                weekly_clicks = (
                    weekly_impressions * ctr * campaign_rng.uniform(0.94, 1.06)
                )
                retarget_totals["spend"] += weekly_spend
                retarget_totals["impressions"] += weekly_impressions
                retarget_totals["clicks"] += weekly_clicks
                retarget_rows.append(
                    {
                        "week_start": week_key,
                        "geo": geo,
                        "campaign_name": campaign,
                        "adset_name": adset,
                        "impressions": int(round(weekly_impressions)),
                        "clicks": int(round(weekly_clicks)),
                        "amount_spent": round(weekly_spend, 2),
                    }
                )
            retarget_week[key] = retarget_totals

            sends = max(
                400,
                round(4100.0 * demand * week_effect * trend * geo_rng.uniform(0.94, 1.08)),
            )
            if coordinated or independent:
                sends = round(sends * 1.16)
            delivered = round(sends * geo_rng.uniform(0.96, 0.99))
            open_rate = round(
                0.19
                + 0.05 * math.sin((2.0 * math.pi * kpi_index) / 26.0)
                + geo_rng.uniform(-0.02, 0.02),
                4,
            )
            click_rate = round(
                0.022
                + 0.006 * math.sin((2.0 * math.pi * kpi_index) / 18.0)
                + geo_rng.uniform(-0.003, 0.003),
                4,
            )

            paid_sessions = round(
                (
                    (0.0 if google_week[key] is None else google_week[key]["clicks"])
                    + pin_totals["clicks"]
                    + prospect_totals["clicks"]
                    + retarget_totals["clicks"]
                )
                * geo_rng.uniform(0.74, 0.88)
            )
            sessions = (
                organic_sessions
                + paid_sessions
                + round(420.0 * demand * geo_rng.uniform(0.90, 1.10))
            )
            users = round(sessions * geo_rng.uniform(0.68, 0.78))

            promo = 1 if coordinated or independent else 0
            capacity = (
                0.72
                + 0.18 * math.sin((2.0 * math.pi * (kpi_index - 10)) / 52.0)
                + (0.06 if week.month in (12, 1, 2, 7, 8) else 0.0)
            )
            availability = min(1.0, max(0.42, capacity + geo_rng.uniform(-0.04, 0.04)))
            bookable = int(round(4200.0 * demand * availability))
            adr = (
                100.0
                + 14.0 * math.sin((2.0 * math.pi * (kpi_index + 3)) / 52.0)
                + 8.0 * (1.0 - availability)
                - (6.0 if promo else 0.0)
                + (4.5 if holiday_flag else 0.0)
                + geo_rng.uniform(-1.6, 1.6)
            )
            if week.month in (12, 1, 2, 7, 8):
                organic_sessions = int(round(organic_sessions * (1.0 + 0.004 * (adr - 100.0))))

            google_obs = google_week[key]
            search_clicks = 0.0 if google_obs is None else google_obs["clicks"]
            base_bookings = 88.0 * demand * week_effect * trend
            avail_effect = 0.50 + 0.50 * availability
            price_effect = max(0.72, 1.10 - 0.0018 * adr)
            snow_effect = 1.0 + 0.0014 * snowfall * ski
            promo_lift = 9.5 * promo * demand
            media_lift = (
                0.0075 * search_clicks
                + 0.0011 * pin_totals["impressions"] / 1000.0
                + 0.0048 * prospect_totals["clicks"]
                + 0.0036 * retarget_totals["clicks"]
                + 0.0011 * sends
            )
            bookings = max(
                6,
                round(
                    base_bookings * avail_effect * price_effect * snow_effect
                    + promo_lift
                    + media_lift
                    + geo_rng.gauss(0.0, 6.5)
                ),
            )
            stay_value = adr * geo_rng.uniform(2.1, 2.6)
            revenue = bookings * stay_value

            sunday = (week + timedelta(days=6)).strftime("%Y-%m-%d")
            pms_rows.append(
                {
                    "week_ending": sunday,
                    "geo": geo,
                    "bookings": int(bookings),
                    "occupancy_index": round(availability, 4),
                }
            )
            revenue_value: float | str
            if geo == "CA":
                revenue_value = format_currency_usd(revenue)
            else:
                revenue_value = round(revenue, 2)
            stripe_rows.append(
                {
                    "week_start": week_key,
                    "geo": geo,
                    "booking_revenue": revenue_value,
                    "successful_charges": int(bookings),
                }
            )
            ga4_rows.append(
                {
                    "week_start_date": week_key,
                    "geo": geo,
                    "sessions": int(sessions),
                    "users": int(users),
                    "organic_sessions": int(organic_sessions),
                    "availability_searches": int(availability_searches),
                    "abandoned_reservations": int(abandoned),
                }
            )
            klaviyo_rows.append(
                {
                    "week_start": week_key,
                    "geo": str(geo_config["label"]),
                    "send_count": int(sends),
                    "delivered": int(delivered),
                    "open_rate": open_rate,
                    "click_rate": click_rate,
                }
            )
            promo_rows.append(
                {
                    "week_start": week_key,
                    "geo": geo,
                    "promotional_package": promo,
                    "package_name": package,
                    "package_class": (
                        "coordinated_with_media"
                        if coordinated
                        else "independent"
                        if independent
                        else "none"
                    ),
                }
            )
            if key not in MISSING_AVAILABILITY:
                availability_rows.append(
                    {
                        "week_start": week_key,
                        "geo": geo,
                        "availability_index": round(availability, 4),
                        "bookable_room_nights": bookable,
                    }
                )
            adr_rows.append(
                {
                    "week_start": week_key,
                    "geo": geo,
                    "adr_price_index": round(adr, 3),
                }
            )
            weather_rows.append(
                {
                    "week_start": week_key,
                    "geo": geo,
                    "snowfall_index": round(snowfall, 3),
                    "temperature_f": round(temperature, 2),
                    "precipitation_index": round(precipitation, 3),
                }
            )

            search_impr = None if google_obs is None else int(round(google_obs["impressions"]))
            search_spend = None if google_obs is None else round(google_obs["spend"], 2)
            avail_value = None if key in MISSING_AVAILABILITY else round(availability, 4)
            truth_rows.append(
                {
                    "time": week_key,
                    "geo": geo,
                    "kpi_bookings": int(bookings),
                    "kpi_revenue": round(revenue, 2),
                    "revenue_per_kpi": round(revenue / bookings, 2),
                    "population": int(geo_config["population"]),
                    "paid_search_impressions": search_impr,
                    "paid_search_spend": search_spend,
                    "paid_social_upper_impressions": int(round(pin_totals["impressions"])),
                    "paid_social_upper_spend": round(pin_totals["spend"], 2),
                    "paid_social_prospecting_impressions": int(
                        round(prospect_totals["impressions"])
                    ),
                    "paid_social_prospecting_spend": round(prospect_totals["spend"], 2),
                    "paid_social_retargeting_impressions": int(
                        round(retarget_totals["impressions"])
                    ),
                    "paid_social_retargeting_spend": round(retarget_totals["spend"], 2),
                    "organic_sessions": int(organic_sessions),
                    "email_sends": int(sends),
                    "availability_index": avail_value,
                    "snowfall_index": round(snowfall, 3),
                    "holiday_flag": holiday_flag,
                    "adr_price_index": round(adr, 3),
                    "promotional_package": promo,
                }
            )

    google_df = pd.DataFrame(google_rows)
    target = google_df[
        (google_df["date"] == GOOGLE_DUPLICATE["date"])
        & (google_df["geo"] == GOOGLE_DUPLICATE["geo"])
        & (google_df["campaign"] == GOOGLE_DUPLICATE["campaign"])
    ]
    if len(target) != 1:
        raise RuntimeError("Expected deterministic Google duplicate target was not unique")
    google_df = pd.concat([google_df, target.copy()], ignore_index=True)

    retarget_df = pd.DataFrame(retarget_rows)
    dup = retarget_df[
        (retarget_df["week_start"] == META_RETARGET_DUPLICATE["week_start"])
        & (retarget_df["geo"] == META_RETARGET_DUPLICATE["geo"])
        & (retarget_df["campaign_name"] == META_RETARGET_DUPLICATE["campaign_name"])
        & (retarget_df["adset_name"] == META_RETARGET_DUPLICATE["adset_name"])
    ]
    if len(dup) != 1:
        raise RuntimeError("Expected Meta retargeting duplicate target was not unique")
    retarget_df = pd.concat([retarget_df, dup.copy()], ignore_index=True)

    return {
        "google_ads_daily.csv": google_df,
        "pinterest_ads_daily.csv": pd.DataFrame(pinterest_rows),
        "meta_ads_prospecting_weekly.csv": pd.DataFrame(prospect_rows),
        "meta_ads_retargeting_weekly.csv": retarget_df,
        "ga4_weekly.csv": pd.DataFrame(ga4_rows),
        "pms_bookings_weekly.csv": pd.DataFrame(pms_rows),
        "stripe_weekly.csv": pd.DataFrame(stripe_rows),
        "klaviyo_weekly.csv": pd.DataFrame(klaviyo_rows),
        "promotions_weekly.csv": pd.DataFrame(promo_rows),
        "availability_weekly.csv": pd.DataFrame(availability_rows),
        "adr_weekly.csv": pd.DataFrame(adr_rows),
        "weather_weekly.csv": pd.DataFrame(weather_rows),
        "holiday_calendar_weekly.csv": pd.DataFrame(holiday_rows),
        "geo_population.csv": pd.DataFrame(population_rows),
        "documented_inactive_periods.csv": pd.DataFrame(inactive_rows),
        TRUTH_TABLE: pd.DataFrame(truth_rows),
    }


def _expected_defects() -> list[dict[str, Any]]:
    return [
        {
            "id": "SP-C-001",
            "name": "pms_sunday_ending_vs_monday_media",
            "file": "pms_bookings_weekly.csv",
            "field": "week_ending",
            "media_grain": "Monday-start week_start",
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-001",
        },
        {
            "id": "SP-C-002",
            "name": "pinterest_daily_weekly_grain_mismatch",
            "file": "pinterest_ads_daily.csv",
            "source_grain": "daily",
            "target_grain": "weekly",
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-003",
        },
        {
            "id": "SP-C-003",
            "name": "meta_retargeting_duplicate_campaign_adset",
            "file": "meta_ads_retargeting_weekly.csv",
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-010",
            "evidence": META_RETARGET_DUPLICATE,
        },
        {
            "id": "SP-C-004",
            "name": "google_cost_micros",
            "file": "google_ads_daily.csv",
            "field": "cost_micros",
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-017",
        },
        {
            "id": "SP-C-005",
            "name": "stripe_currency_booking_revenue",
            "file": "stripe_weekly.csv",
            "field": "booking_revenue",
            "subset": "geo=CA",
            "pattern": "$#,##0.00",
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-017",
        },
        {
            "id": "SP-C-006",
            "name": "geo_aliases",
            "files": ["google_ads_daily.csv", "klaviyo_weekly.csv"],
            "canonical_geos": list(GEO_CONFIG),
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-005",
        },
        {
            "id": "SP-C-007",
            "name": "missing_availability_control",
            "file": "availability_weekly.csv",
            "cells": [{"geo": "CO", "week_start": "2024-10-07"}],
            "remediation_class": "USER_REQUIRED",
            "zero_fill_forbidden": True,
            "control_imputation_auto_safe": False,
        },
        {
            "id": "SP-C-008",
            "name": "google_unknown_source_gap",
            "file": "google_ads_daily.csv",
            "geo": "CA",
            "weeks": ["2024-06-03", "2024-06-10", "2024-06-17"],
            "remediation_class": "USER_REQUIRED",
            "zero_fill_forbidden": True,
            "rule_family": "MR-011",
        },
        {
            "id": "SP-C-009",
            "name": "meta_prospecting_documented_inactive",
            "file": "documented_inactive_periods.csv",
            "provider": "meta_ads",
            "geo": "PN",
            "weeks": ["2024-04-01", "2024-04-08", "2024-04-15", "2024-04-22"],
            "remediation_class": "AUTO_SAFE",
            "zero_fill_may_be_safe": True,
        },
        {
            "id": "SP-C-010",
            "name": "google_non_summable_rates",
            "file": "google_ads_daily.csv",
            "fields": ["ctr", "cpa"],
            "summable_exposure_candidate": "impressions",
            "remediation_class": "USER_REQUIRED",
            "rule_family": "MR-013",
        },
        {
            "id": "SP-C-011",
            "name": "prospecting_retargeting_aliases",
            "files": [
                "meta_ads_prospecting_weekly.csv",
                "meta_ads_retargeting_weekly.csv",
            ],
            "canonical_channels": [
                "paid_social_prospecting",
                "paid_social_retargeting",
            ],
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-009",
            "notes": "Do not merge prospecting and retargeting automatically.",
        },
        {
            "id": "SP-C-012",
            "name": "google_exact_duplicate_row",
            "file": "google_ads_daily.csv",
            "expected_count": 1,
            "remediation_class": "AUTO_SAFE",
            "rule_family": "MR-010",
            "evidence": GOOGLE_DUPLICATE,
        },
    ]


def _expected_safe_actions() -> list[dict[str, Any]]:
    return [
        {
            "action": "normalize_pms_sunday_ending_to_monday_week",
            "defect_id": "SP-C-001",
            "class": "AUTO_SAFE",
        },
        {
            "action": "aggregate_pinterest_daily_to_weekly",
            "defect_id": "SP-C-002",
            "class": "AUTO_SAFE",
        },
        {
            "action": "drop_meta_retargeting_duplicate_campaign_adset",
            "defect_id": "SP-C-003",
            "class": "AUTO_SAFE",
        },
        {
            "action": "convert_google_cost_micros_to_currency",
            "defect_id": "SP-C-004",
            "class": "AUTO_SAFE",
        },
        {
            "action": "parse_stripe_currency_subset",
            "defect_id": "SP-C-005",
            "class": "AUTO_SAFE",
        },
        {
            "action": "map_geo_aliases_to_canonical_ids",
            "defect_id": "SP-C-006",
            "class": "AUTO_SAFE",
        },
        {
            "action": "map_prospecting_and_retargeting_aliases",
            "defect_id": "SP-C-011",
            "class": "AUTO_SAFE",
        },
        {
            "action": "drop_google_exact_duplicate",
            "defect_id": "SP-C-012",
            "class": "AUTO_SAFE",
        },
        {
            "action": "zero_fill_meta_prospecting_documented_inactive_pn",
            "defect_id": "SP-C-009",
            "class": "AUTO_SAFE",
            "requires": "documented_inactive_periods.csv",
        },
    ]


def _expected_forbidden_actions() -> list[dict[str, Any]]:
    return [
        {"action": "zero_fill_unknown_google_gap", "defect_id": "SP-C-008"},
        {"action": "zero_fill_missing_availability_control", "defect_id": "SP-C-007"},
        {"action": "impute_kpi_bookings"},
        {"action": "impute_control_or_context"},
        {"action": "treat_ctr_or_cpa_as_additive_exposure", "defect_id": "SP-C-010"},
        {"action": "merge_prospecting_and_retargeting"},
        {"action": "drop_geography_without_approval"},
        {"action": "infer_causal_role_from_correlation"},
        {"action": "automatically_classify_price_as_control"},
        {"action": "automatically_classify_retargeting"},
        {"action": "select_final_priors_or_knots_or_modelspec"},
        {"action": "fit_posterior_or_final_mmm"},
        {"action": "extract_candidate_lesson_from_dataset_c"},
        {"action": "use_holdout_evidence_to_alter_domain_view"},
        {"action": "count_dataset_c_toward_promotion_evidence"},
        {"action": "train_mel_from_holdout_reflection"},
    ]


def _business_truth() -> dict[str, Any]:
    return {
        "synthetic": True,
        "not_in_raw_package": True,
        "purpose": (
            "Hidden evaluation context. Do not expose to the agent before semantic questions."
        ),
        "operating_model": {
            "business": BUSINESS,
            "type": "regional outdoor hospitality / mountain lodging",
            "kpi": "bookings",
            "journey": (
                "paid/organic marketing → destination research → website visit → "
                "availability search → reservation → booking revenue"
            ),
        },
        "budget_setting": {
            "google_paid_search": (
                "Partly reacts to destination-search demand forecasts. Holiday spend "
                "rises because demand forecasts rise around holidays, not because the "
                "holiday calendar itself is a media planning input."
            ),
            "pinterest": (
                "Planned quarterly around destination campaigns. Colorado snowfall "
                "correlation is coincidental; budget planning did not use weather."
            ),
            "meta_prospecting": "Supports seasonal destination campaigns.",
            "meta_retargeting": (
                "Follows qualified site, availability-search, and abandoned-reservation "
                "audiences. Selection is real; do not auto-remove or auto-merge."
            ),
            "availability_constraint": (
                "Budgets may be constrained by property availability, but missing "
                "availability is not a campaign-off signal."
            ),
        },
        "negative_controls": [
            "CO snowfall modestly correlates with Pinterest; media was not planned from weather.",
            "Paid search rises around holidays; holiday dates are externally fixed.",
            "UT availability co-moves with Meta prospecting seasonally, not as a campaign rule.",
            "ADR and organic visits co-move in peak season; correlation is not a causal role.",
        ],
        "positive_conditions": [
            "promotional packages coexist with paid media",
            "ADR/price index coexists with paid media",
            "Pinterest/Meta prospecting coexist with Google Paid Search",
            "Meta retargeting is distinguishable from prospecting",
            "organic and lifecycle activity are present",
        ],
        "do_not_encode_as_lesson": (
            "No expected_lesson, no required EXPERIENCE_APPLIED route, "
            "no hard-coded DOMAIN_VIEW claim."
        ),
    }


def _semantic_conditions() -> dict[str, Any]:
    return {
        "match_by": "question_family",
        "do_not_require_exact_question_wording": True,
        "decision_class": "ADVISORY",
        "cannot_independently_block_model_ready": True,
        "conditions": [
            {
                "condition_id": "SP-SEM-001",
                "expected_question_family": "PROMOTION_TIMING",
                "control": "positive",
                "trigger_evidence": "promotional_package control coexists with paid media",
                "ground_truth_business_context": (
                    "Some packages are coordinated with paid campaigns; others follow "
                    "seasonal planning. Role is not predetermined."
                ),
                "expected_owner": "MODELER",
                "expected_authority": "MODELER_REVIEW_REQUIRED",
                "input_blocker": False,
                "modeler_review": True,
            },
            {
                "condition_id": "SP-SEM-002",
                "expected_question_family": "PRICE_DISCOUNT_TIMING",
                "control": "positive",
                "trigger_evidence": "adr_price_index coexists with paid media",
                "ground_truth_business_context": (
                    "ADR varies with season, availability, demand, and promotions. "
                    "Do not encode PRICE=CONTROL."
                ),
                "expected_owner": "MODELER",
                "expected_authority": "MODELER_REVIEW_REQUIRED",
                "input_blocker": False,
                "modeler_review": True,
            },
            {
                "condition_id": "SP-SEM-003",
                "expected_question_family": "DOWNSTREAM_MEDIA",
                "control": "positive",
                "trigger_evidence": "paid_social_upper and paid_search coexist",
                "ground_truth_business_context": (
                    "Upper-funnel destination interest may increase branded/category "
                    "search. The table does not establish that Pinterest causes Paid Search."
                ),
                "expected_owner": "MODELER",
                "expected_authority": "MODELER_REVIEW_REQUIRED",
                "input_blocker": False,
                "modeler_review": True,
            },
            {
                "condition_id": "SP-SEM-004",
                "expected_question_family": "REMARKETING_TARGETING",
                "control": "positive",
                "trigger_evidence": "paid_social_retargeting channel name is present",
                "ground_truth_business_context": (
                    "Retargeting eligibility depends on prior site visit, availability "
                    "search, or abandoned reservation. Do not auto-classify as invalid."
                ),
                "expected_owner": "MODELER",
                "expected_authority": "MODELER_REVIEW_REQUIRED",
                "input_blocker": False,
                "modeler_review": True,
            },
            {
                "condition_id": "SP-SEM-005",
                "expected_question_family": "ORGANIC_MEDIA_TIMING",
                "control": "positive",
                "trigger_evidence": "organic_sessions and email_sends are present",
                "ground_truth_business_context": (
                    "Organic/lifecycle timing may interact with paid campaigns. Role is reviewable."
                ),
                "expected_owner": "MODELER",
                "expected_authority": "MODELER_REVIEW_REQUIRED",
                "input_blocker": False,
                "modeler_review": True,
            },
            {
                "condition_id": "SP-NEG-001",
                "expected_question_family": None,
                "control": "negative",
                "trigger_evidence": "CO snowfall correlates with Pinterest spend",
                "ground_truth_business_context": "Budget planning did not use weather.",
                "must_not_infer": "snowfall causes Pinterest or Pinterest is weather-driven",
                "expected_owner": "EVALUATOR",
                "expected_authority": "NONE",
                "input_blocker": False,
                "modeler_review": False,
            },
            {
                "condition_id": "SP-NEG-002",
                "expected_question_family": None,
                "control": "negative",
                "trigger_evidence": "Paid search rises around holiday weeks",
                "ground_truth_business_context": "Holiday dates are externally fixed.",
                "must_not_infer": "holiday calendar is a media treatment",
                "expected_owner": "EVALUATOR",
                "expected_authority": "NONE",
                "input_blocker": False,
                "modeler_review": False,
            },
            {
                "condition_id": "SP-NEG-003",
                "expected_question_family": None,
                "control": "negative",
                "trigger_evidence": "UT availability co-moves with Meta prospecting",
                "ground_truth_business_context": (
                    "Relationship is partly seasonal, not a campaign rule."
                ),
                "must_not_infer": "availability is a Meta campaign-decision input",
                "expected_owner": "EVALUATOR",
                "expected_authority": "NONE",
                "input_blocker": False,
                "modeler_review": False,
            },
            {
                "condition_id": "SP-NEG-004",
                "expected_question_family": None,
                "control": "negative",
                "trigger_evidence": "ADR and organic visits co-move in peak season",
                "ground_truth_business_context": "Correlation does not establish causal role.",
                "must_not_infer": "organic causes ADR or ADR causes organic",
                "expected_owner": "EVALUATOR",
                "expected_authority": "NONE",
                "input_blocker": False,
                "modeler_review": False,
            },
        ],
    }


def _expected_invariants() -> dict[str, Any]:
    return {
        "independent_variable": "DOMAIN_VIEW version",
        "controlled_variables": [
            "Dataset C data",
            "rule registry",
            "tool version",
            "response contract",
            "Meridian version",
            "model intent",
            "expected behavior contract",
        ],
        "must_remain_invariant": list(
            [
                "model_input_fingerprint",
                "schema_fingerprint",
                "parameter_calculations",
                "readiness_deterministic_checks",
                "official_meridian_findings",
                "model_ready_logic",
                "raw_data_values",
                "final_priors",
                "final_knots",
                "final_modelspec",
                "posterior",
            ]
        ),
        "may_change_from_routing_hint": [
            "question_routing",
            "diagnostic_routing",
            "finding_prioritization",
            "advisory_ordering",
            "handoff_emphasis",
            "source_acquisition_guidance",
        ],
        "negative_application_cases": [
            "OVERGENERALIZATION",
            "UNDERGENERALIZATION",
            "UNAUTHORIZED_ESCALATION",
        ],
        "experience_applied_not_certified_by_this_file": True,
    }


def _expected_authority() -> dict[str, Any]:
    return {
        "semantic_questions": "MODELER_REVIEW_REQUIRED",
        "semantic_decision_class": "ADVISORY",
        "heuristics_cannot_block_model_ready": True,
        "unknown_media_gap": "USER_REQUIRED",
        "control_imputation": "not AUTO_SAFE",
        "kpi_imputation": "not AUTO_SAFE",
        "official_meridian_owns_official_eda": True,
        "dataset_role": DatasetRole.SEALED_HOLDOUT.value,
        "training_access": "DENIED",
        "candidate_generation_access": "DENIED",
        "generation_is_not_experience_learned": True,
        "generation_is_not_experience_applied": True,
    }


def _snapshot_from_truth(truth: pd.DataFrame, run_id: str) -> Any:
    contract = generate_meridian_input_contract(
        run_id=run_id,
        intent=DATASET_C_MODEL_INTENT,
        frame=truth,
        project_id="fixture-project",
        dataset_id="fixture_dataset",
        table_id="fixture_table",
    )
    fingerprint = fingerprint_frame(truth, contract)
    schema_fp = schema_fingerprint_for(truth, contract)
    return load_verified_snapshot(
        run_id,
        adapter=FixtureAdapter(
            run_id=run_id,
            frame=truth,
            contract=contract,
            expected_fingerprint=fingerprint,
            schema_fingerprint=schema_fp,
        ),
    )


def _compute_expected_intelligence(truth: pd.DataFrame) -> dict[str, Any]:
    snapshot = _snapshot_from_truth(truth, "dataset-c-summit-pine")
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
        "input_fingerprint": snapshot.endpoint.input_fingerprint,
        "schema_fingerprint": snapshot.endpoint.schema_fingerprint,
        "dataset_a_lenient_ratio_must_not_be_cloned": 3.74,
        "dataset_b_lenient_ratio_must_not_be_cloned": 5.538462,
    }


def _compact_response(response: Any) -> dict[str, Any]:
    payload = response.model_dump(mode="json")
    actions = payload.get("actions") or []
    questions = payload.get("questions") or []
    return {
        "response_type": payload.get("response_type"),
        "title": payload.get("title"),
        "status": payload.get("status"),
        "causal_roles_assigned": False,
        "action_owners": sorted(
            {str(item.get("owner")) for item in actions if item.get("owner")}
        ),
        "question_families": sorted(
            {
                str(item.get("question_family") or item.get("family") or "")
                for item in questions
                if item.get("question_family") or item.get("family")
            }
        ),
        "finding_count": len(payload.get("findings") or []),
    }


def _build_baseline(truth: pd.DataFrame, intelligence: dict[str, Any]) -> dict[str, Any]:
    snapshot = _snapshot_from_truth(truth, "dataset-c-summit-pine-v1")
    bundle = run_pre_eda_diagnostics(snapshot)
    interview = bundle["semantic_interview"]
    builder = ResponseBuilder()
    responses: dict[str, Any] = {}
    responses["ASSESSMENT"] = _compact_response(builder.assessment(bundle))
    responses["INSIGHT"] = _compact_response(builder.insight(bundle))
    responses["ADVISORY"] = _compact_response(builder.parameter_advisory(bundle))
    responses["SEMANTIC_INTERVIEW"] = _compact_response(builder.semantic_interview(bundle))
    responses["MODELING_FEASIBILITY"] = _compact_response(
        builder.modeling_feasibility(bundle)
    )
    try:
        responses["GUIDED_REMEDIATION"] = _compact_response(
            builder.guided_remediation(bundle)
        )
    except ResponseContractError as exc:
        responses["GUIDED_REMEDIATION"] = {
            "response_type": "GUIDED_REMEDIATION",
            "status": "NOT_GENERATED",
            "reason": str(exc),
        }
    view = load_current_domain_view()
    if view is None:
        raise RuntimeError("DOMAIN_VIEW v1 must exist before sealing Dataset C")
    if view.promoted_lesson_count != 0:
        raise RuntimeError("HOLDOUT_CREATION_TOO_LATE: a lesson was already promoted")
    if view.content_fingerprint != DOMAIN_VIEW_FINGERPRINT_AT_SEAL:
        raise RuntimeError("DOMAIN_VIEW fingerprint at seal does not match v1.0.0")
    compact = {
        "fixture_id": "dataset-c-summit-pine-domain-view-v1",
        "dataset_role": DatasetRole.SEALED_HOLDOUT.value,
        "evaluation_only": True,
        "domain_view_version": view.domain_view_version,
        "domain_view_fingerprint": view.content_fingerprint,
        "promoted_lesson_count": view.promoted_lesson_count,
        "response_contract_version": "1.0",
        "intelligence_version": "2.0.0",
        "meridian_version": "google-meridian==1.8.0",
        "official_eda_status": "NOT_RUN_IN_GENERATOR",
        "model_ready_state": "NOT_CLAIMED_LOCAL_BASELINE",
        "cloud_run": False,
        "semantic_question_count": interview.get("question_count"),
        "semantic_families": intelligence["semantic_trigger_families"],
        "semantic_status": interview.get("semantic_status"),
        "causal_roles_assigned": interview.get("causal_roles_assigned"),
        "parameter": {
            "n_geos": intelligence["n_geos"],
            "n_times": intelligence["n_times"],
            "lenient_ratio": intelligence["lenient_ratio"],
            "pressure_band": intelligence["pressure_band"],
        },
        "tool_routes": [
            "run_pre_eda_diagnostics",
            "detect_semantic_question_triggers",
            "ResponseBuilder.assessment",
            "ResponseBuilder.insight",
            "ResponseBuilder.parameter_advisory",
            "ResponseBuilder.semantic_interview",
            "ResponseBuilder.modeling_feasibility",
        ],
        "responses": responses,
        "training_access": "DENIED",
    }
    compact["result_fingerprint"] = fingerprint_payload(compact)
    return compact


def generate(output_root: Path, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    dataset_dir = output_root / DATASET_NAME
    raw_dir = dataset_dir / "raw"
    truth_dir = dataset_dir / "truth"
    sealed_dir = dataset_dir / "sealed"
    baseline_dir = dataset_dir / "baseline" / "domain_view_v1"
    learning_dir = dataset_dir / "learning"
    for path in (raw_dir, truth_dir, sealed_dir, baseline_dir, learning_dir):
        path.mkdir(parents=True, exist_ok=True)

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

    intent_payload = DATASET_C_MODEL_INTENT.model_dump(mode="json")
    intent_path = raw_dir / "model_intent.json"
    write_json(intent_path, intent_payload)
    files["raw/model_intent.json"] = json_file_meta(intent_path, intent_payload)

    truth = pd.read_csv(truth_dir / TRUTH_TABLE)
    intelligence = _compute_expected_intelligence(truth)
    defects = _expected_defects()
    semantic_conditions = _semantic_conditions()
    sealed_payloads = {
        "expected_issues.json": {
            "expected_defect_count": len(defects),
            "expected_defects": defects,
            "non_defect_notes": [
                (
                    "Pinterest Ads starts 2023-02-06; this is a documented property/"
                    "channel launch, not an unknown gap."
                ),
                (
                    "Google Ads and Meta include 10 pre-KPI weeks for adstock. "
                    "Missing KPI in the pre-period is not a source gap."
                ),
                "Sunday-ending PMS weeks are a date-alignment defect, not missing KPI.",
            ],
        },
        "expected_semantic_conditions.json": semantic_conditions,
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
            "generated_by": "scripts/generate_dataset_c.py",
            "hand_authored_rows": False,
            "kpi_field": "kpi_bookings",
            "revenue_per_kpi_is_supporting": True,
            "rows": int(len(truth)),
            "geos": list(GEO_CONFIG),
            "n_times": int(truth["time"].nunique()),
            "n_geos": int(truth["geo"].nunique()),
            "column_count": int(len(truth.columns)),
            "content_fingerprint": intelligence["input_fingerprint"],
            "schema_fingerprint": intelligence["schema_fingerprint"],
        },
        "expected_authority.json": _expected_authority(),
        "expected_run_intelligence.json": intelligence,
        "expected_behavior_contract.json": _expected_invariants(),
        "business_truth.json": _business_truth(),
    }
    for name, payload in sealed_payloads.items():
        path = sealed_dir / name
        write_json(path, payload)
        files[f"sealed/{name}"] = json_file_meta(path, payload)

    expected_contract_fingerprint = fingerprint_payload(
        {
            name: files[f"sealed/{name}"]["sha256"]
            for name in (
                "expected_issues.json",
                "expected_semantic_conditions.json",
                "expected_safe_actions.json",
                "expected_forbidden_actions.json",
                "expected_behavior_contract.json",
                "expected_authority.json",
                "business_truth.json",
            )
        }
    )
    raw_package_fingerprint = fingerprint_payload(
        {
            name: meta["sha256"]
            for name, meta in files.items()
            if name.startswith("raw/") and name.endswith(".csv")
        }
    )
    schema_fp = fingerprint_payload(
        {
            name: meta["columns"]
            for name, meta in files.items()
            if name.startswith("raw/")
        }
    )
    package_fingerprint = fingerprint_payload(
        {
            "generator_version": GENERATOR_VERSION,
            "seed": seed,
            "raw": raw_package_fingerprint,
            "truth": files["truth/expected_model_ready_weekly.csv"]["sha256"],
            "expected_contracts": expected_contract_fingerprint,
        }
    )

    holdout = seal_holdout(
        dest=learning_dir / "holdout_manifest.json",
        dataset_identity="dataset_c_summit_and_pine",
        classification="synthetic",
        input_package_fingerprint=package_fingerprint,
        schema_fingerprint=schema_fp,
        seed=seed,
        generator_version=GENERATOR_VERSION,
        business=BUSINESS,
        expected_contract_fingerprint=expected_contract_fingerprint,
        sealed_at=SEALED_AT,
        created_at=SEALED_AT,
        domain_view_version_at_seal=DOMAIN_VIEW_VERSION_AT_SEAL,
        domain_view_fingerprint_at_seal=DOMAIN_VIEW_FINGERPRINT_AT_SEAL,
        promoted_lesson_count_at_seal=0,
    )
    sealed_holdout = sealed_dir / "holdout_manifest.json"
    sealed_holdout.write_text(
        (learning_dir / "holdout_manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    files["learning/holdout_manifest.json"] = json_file_meta(
        learning_dir / "holdout_manifest.json",
        holdout.model_dump(mode="json"),
    )
    files["sealed/holdout_manifest.json"] = json_file_meta(
        sealed_holdout, holdout.model_dump(mode="json")
    )

    baseline = _build_baseline(truth, intelligence)
    write_json(baseline_dir / "baseline_result.json", baseline)
    files["baseline/domain_view_v1/baseline_result.json"] = json_file_meta(
        baseline_dir / "baseline_result.json", baseline
    )

    manifest = {
        "generator_version": GENERATOR_VERSION,
        "dataset": DATASET_NAME,
        "dataset_identity": "dataset_c_summit_and_pine",
        "dataset_role": DatasetRole.SEALED_HOLDOUT.value,
        "business": BUSINESS,
        "synthetic": True,
        "seed": seed,
        "sealed_at": SEALED_AT,
        "package_fingerprint": package_fingerprint,
        "schema_fingerprint": schema_fp,
        "expected_contract_fingerprint": expected_contract_fingerprint,
        "domain_view_version_at_seal": DOMAIN_VIEW_VERSION_AT_SEAL,
        "domain_view_fingerprint_at_seal": DOMAIN_VIEW_FINGERPRINT_AT_SEAL,
        "promoted_lesson_count_at_seal": 0,
        "lesson_ids_visible_at_seal": [],
        "sealed_before_candidate_extraction": True,
        "training_access": "DENIED",
        "candidate_generation_access": "DENIED",
        "reflection_training_access": "DENIED",
        "evaluation_only": True,
        "extends": "app.synthetic.mmm helpers originally used by scripts/generate_demo_data.py",
        "replaces": "Episode Core placeholder generator 1.0.0 outdoor-furniture stub",
        "not": [
            "training evidence",
            "a predetermined MEL lesson",
            "EXPERIENCE_LEARNED",
            "EXPERIENCE_APPLIED",
        ],
        "date_range": {
            "kpi_start": KPI_START,
            "kpi_end": KPI_END,
            "media_pre_start": MEDIA_PRE_START,
            "pinterest_launch": "2023-02-06",
        },
        "geos": list(GEO_CONFIG),
        "providers": [
            "Google Ads",
            "Pinterest Ads",
            "Meta Ads",
            "GA4",
            "synthetic_pms",
            "Stripe",
            "Klaviyo",
        ],
        "layout": {
            "raw": "raw/",
            "truth": "truth/",
            "sealed": "sealed/",
            "baseline": "baseline/domain_view_v1/",
            "runtime_must_not_read": [
                TRUTH_TABLE,
                "sealed/",
                "baseline/",
                "learning/",
                "business_truth.json",
            ],
        },
        "files": files,
        "notes": [
            "All values are synthetic and deterministic.",
            "This dataset was sealed before experiential lesson promotion.",
            "Dataset C is an evaluation holdout, not training evidence.",
            "truth/expected_model_ready_weekly.csv is regression truth, not an M3 output.",
            "Run-intelligence expected values are computed from the generated truth table.",
            "Official Meridian EDA was not executed in the generator.",
        ],
    }
    write_json(dataset_dir / "generation_manifest.json", manifest)
    package_manifest = {
        "dataset_id": "dataset_c_summit_and_pine",
        "business": BUSINESS,
        "dataset_role": DatasetRole.SEALED_HOLDOUT.value,
        "synthetic": True,
        "seed": seed,
        "generator_version": GENERATOR_VERSION,
        "package_fingerprint": package_fingerprint,
        "schema_fingerprint": schema_fp,
        "expected_contract_fingerprint": expected_contract_fingerprint,
        "learning_eligibility": "DENIED",
        "holdout_status": "SEALED",
        "sealed_at": SEALED_AT,
    }
    write_json(dataset_dir / "package_manifest.json", package_manifest)
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
    print("package_fingerprint", manifest["package_fingerprint"])


if __name__ == "__main__":
    main()
