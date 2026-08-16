"""Deterministic Summit & Pine Dataset C holdout generator.

Synthetic, independent of Music Center Dataset A. Seal this holdout before
MEL candidate extraction. Do not inspect learned candidates and then reshape
this dataset to match them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.mel.fingerprint import fingerprint_payload
from app.mel.holdout import seal_holdout
from app.tools.artifacts import sha256_file

GENERATOR_VERSION = "1.0.0"
DEFAULT_SEED = 20260816
DEFAULT_OUTPUT = Path("tests/fixtures/summit_and_pine/dataset_c")


def _rng_value(seed: int, *parts: object) -> float:
    raw = "|".join(str(part) for part in (seed, *parts))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def generate_dataset_c(output_root: Path, *, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    raw = output_root / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    start = date(2024, 7, 1)
    weeks = [start + timedelta(days=7 * index) for index in range(78)]
    tiktok_rows: list[dict[str, Any]] = []
    amazon_rows: list[dict[str, Any]] = []
    stripe_rows: list[dict[str, Any]] = []
    email_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    for index, week in enumerate(weeks):
        seasonal = 1.0 + 0.12 * math.sin((2.0 * math.pi * index) / 52.0)
        holiday = 1.25 if week.month in {11, 12} else 1.0
        demand = 800 + 40 * index
        tiktok_spend_cents = int(
            (4200 + 900 * seasonal * holiday) * (0.85 + _rng_value(seed, "tt", index))
        )
        amazon_spend = round(
            (3100 + 700 * seasonal) * (0.9 + _rng_value(seed, "amz", index)), 2
        )
        charges = int(demand * seasonal * holiday * (0.92 + _rng_value(seed, "kpi", index)))
        tiktok_rows.append(
            {
                "week_start": week.isoformat(),
                "geo": "US",
                "campaign": "Prospecting | Outdoor",
                "impressions": tiktok_spend_cents * 18,
                "spend_cents": tiktok_spend_cents,
            }
        )
        amazon_rows.append(
            {
                "date": week.strftime("%m-%d-%Y"),
                "marketplace": "US",
                "campaign_name": "SP | Patio Furniture",
                "impressions": int(amazon_spend * 22),
                "cost": amazon_spend,
            }
        )
        if index != 17:
            stripe_rows.append(
                {
                    "week_start": week.isoformat(),
                    "region": "US",
                    "successful_charges": charges,
                    "net_revenue": round(charges * 84.5, 2),
                }
            )
        email_rows.append(
            {
                "week_start": week.isoformat(),
                "geo": "US",
                "sends": int(12000 * seasonal),
                "attributed_orders": int(40 * seasonal),
            }
        )
        control_rows.append(
            {
                "week_start": week.isoformat(),
                "geo": "US",
                "weather_index": round(50 + 20 * math.sin(index / 8.0), 2),
                "holiday_flag": 1 if week.month in {11, 12} else 0,
            }
        )
    stripe_rows.append(stripe_rows[3])
    files = {
        "tiktok_ads_weekly.csv": pd.DataFrame(tiktok_rows),
        "amazon_ads_weekly.csv": pd.DataFrame(amazon_rows),
        "stripe_weekly.csv": pd.DataFrame(stripe_rows),
        "email_weekly.csv": pd.DataFrame(email_rows),
        "weather_controls_weekly.csv": pd.DataFrame(control_rows),
    }
    file_meta: dict[str, Any] = {}
    for name, frame in files.items():
        path = raw / name
        frame.to_csv(path, index=False)
        file_meta[f"raw/{name}"] = {
            "rows": int(len(frame)),
            "columns": list(frame.columns),
            "sha256": sha256_file(path),
        }
    intent = {
        "canonical_time_grain": "week",
        "model_scope": "national",
        "kpi": {"field": "successful_charges", "source": "stripe_weekly.csv"},
        "revenue": {"field": "net_revenue", "source": "stripe_weekly.csv"},
        "paid_media": [
            {"name": "tiktok", "impressions": "impressions", "spend": "spend_cents"},
            {"name": "amazon_sponsored", "impressions": "impressions", "spend": "cost"},
        ],
        "organic_media": [{"name": "email", "metric": "sends"}],
        "controls": ["weather_index", "holiday_flag"],
        "population": None,
        "synthetic_label": "Summit & Pine is a fully synthetic outdoor-furniture retailer.",
    }
    intent_path = raw / "model_intent.json"
    intent_path.write_text(json.dumps(intent, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    file_meta["raw/model_intent.json"] = {
        "rows": None,
        "columns": sorted(intent),
        "sha256": sha256_file(intent_path),
    }
    package_fp = fingerprint_payload(file_meta)
    schema_fp = fingerprint_payload(
        {name: meta["columns"] for name, meta in file_meta.items()}
    )
    generation = {
        "generator_version": GENERATOR_VERSION,
        "dataset": "dataset_c",
        "business": "Summit & Pine",
        "synthetic": True,
        "seed": seed,
        "geo": ["US"],
        "weeks": 78,
        "providers": ["TikTok Ads", "Amazon Ads", "Stripe", "email"],
        "seeded_defects": [
            "TikTok spend stored as integer cents",
            "Amazon dates as MM-DD-YYYY",
            "one duplicated Stripe week row",
            "one missing Stripe week (index 17)",
        ],
        "files": file_meta,
        "package_fingerprint": package_fp,
        "schema_fingerprint": schema_fp,
        "notes": [
            "Fully synthetic holdout. Not a Music Center clone.",
            "Sealed for MEL before candidate extraction.",
        ],
    }
    (output_root / "generation_manifest.json").write_text(
        json.dumps(generation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    seal_holdout(
        dest=output_root / "learning" / "holdout_manifest.json",
        dataset_identity="dataset_c_summit_and_pine",
        classification="synthetic",
        input_package_fingerprint=package_fp,
        schema_fingerprint=schema_fp,
        seed=seed,
        generator_version=GENERATOR_VERSION,
    )
    return generation


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Summit & Pine Dataset C holdout")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    generate_dataset_c(args.output_root, seed=args.seed)


if __name__ == "__main__":
    main()
