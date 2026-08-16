# Stride & Field Dataset B

**Stride & Field** is a fully synthetic premium outdoor/running apparel retailer (D2C + marketplace). It is the independent MEL **learning-evidence** Dataset B.

This package is **not**:

- Music Center `datasets/music_center/dataset_b/` (a related Music Center schema-family episode)
- Dataset C Summit & Pine (the sealed holdout)
- a fixture designed around a predetermined lesson
- proof of `EXPERIENCE_LEARNED`, DOMAIN_VIEW v2, or `EXPERIENCE_APPLIED`

## Generate

From the repository root, using the same synthetic stack as Music Center Dataset A:

```bash
python scripts/generate_dataset_b.py
```

Shared primitives (stable RNG, weekly split, SHA-256, CSV write) live in `app/synthetic/mmm.py`. They were extracted from `scripts/generate_demo_data.py` so Dataset B extends the Music Center generator instead of forking a second stack.

The generator is deterministic. Seed `20260817`. Every generated file is fingerprinted in `dataset_b/generation_manifest.json`.

## Shape

- modeling target: Google Meridian
- geo model, weekly grain
- 6 geos: NE, MA, SE, MW, MT, WE
- KPI window: 2023-01-02 through 2025-12-22 (156 Monday weeks)
- paid media pre-period: Microsoft Ads and TikTok from 2022-10-24
- Amazon Ads launch: 2023-03-06 (documented launch, not an unknown gap)
- KPI: Shopify orders (`revenue_per_kpi` is supporting)
- paid: Microsoft Ads (search), TikTok Ads (video/social), Amazon Ads (retail media)
- owned: GA4 organic sessions, Klaviyo `send_count`
- controls: weather, competitor price, promotional event, holiday flag

Google Ads is intentionally absent so the provider mix differs from Music Center Dataset A.

## Layout

```text
raw/                 runtime package
truth/               regression truth only; not an M3 output
expected/            evaluation manifests, including hidden business_truth.json
generation_manifest.json
```

Runtime tools must receive only `raw/`. Do not load `expected/business_truth.json` before the normal semantic-question path.

## Guardrails

- Unknown Amazon SE gap must not be zero-filled.
- Missing weather observations are not AUTO_SAFE to impute.
- Klaviyo open/click rates and Amazon attributed sales/ROAS are not additive media exposure.
- Dataset generation does not promote a lesson.
- Do not modify Dataset C.
- Do not overwrite Music Center Dataset B.
