# Dataset C — Summit & Pine sealed holdout

Status: **PREM3_DATASET_C_HOLDOUT_READY** (local seal and firewall). Cloud
Dataset C execution and official Meridian EDA are **not** claimed here.

This is inspectable proof that the independent holdout assignment exists and was
sealed **before** the first real multi-episode lesson promotion attempt. It is
**not** a claim that PreM3 learned, and it is **not** `EXPERIENCE_APPLIED`.

## Identity

| | |
|---|---|
| Business | Summit & Pine (synthetic mountain lodging / outdoor hospitality) |
| Canonical path | `datasets/summit_and_pine/dataset_c/` |
| Dataset ID | `dataset_c_summit_and_pine` |
| Typed role | `SEALED_HOLDOUT` |
| Generator | `scripts/generate_dataset_c.py` `2.0.0` |
| Shared stack | `app/synthetic/mmm.py` |
| Seed | `20260816` (kept from Episode Core placeholder) |
| Sealed at | `2026-08-16T19:00:00+00:00` |
| KPI | bookings |
| Geos | CO, UT, CA, PN, NE (156 Monday weeks, 2022-11-07–2025-10-27) |

The Episode Core placeholder at `tests/fixtures/summit_and_pine/` was a protocol
stub (national outdoor-furniture mix). Generator 2.0.0 replaced it with this
hospitality holdout **while promoted experiential lessons were still 0**.

## Pre-learning seal

| | |
|---|---|
| DOMAIN_VIEW | `1.0.0` |
| DOMAIN_VIEW fingerprint | `b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf` |
| Promoted lessons at seal | **0** |
| `lesson_ids_visible_at_seal` | `[]` |
| `EXPERIENCE_LEARNED` | NO |
| `EXPERIENCE_APPLIED` | NO |
| Package fingerprint | `f1bfaa5ba98b8f6d94cccb6b7a19c1e50ab8e315567e82fa3cf22129193bf18f` |
| Schema fingerprint | `1da7e7a724fdf6b9522bf3816fefe14db9dca15c6e43b663ba7de04bc298003e` |
| Expected-contract fingerprint | `d09c95deed895576765b4923f90c8a831c923687ab9016221d8e3c576a7dd522` |
| Model-input fingerprint | `0a79f1c411a5268f15822d9d1d8afced8ac0171d0b6549479571640f134a4cee` |
| v1 baseline fingerprint | `7d3c94eb30b6d5a39d03cc2c35488faea669c61cab46aad9e2af70448abb4ffe` |

## Shape

5 geos × 156 weeks = 780 rows. 4 paid treatments + 2 organic + 5 controls.
Computed lenient observations-per-parameter ratio **4.588235**, pressure band
`SEVERE`. Distinct from Dataset A (3.74) and Dataset B (5.538462). Heuristics
cannot block `MODEL_READY`.

## Providers

Google Ads (daily, `cost_micros`), Pinterest Ads (daily), Meta Ads prospecting
and retargeting (weekly), GA4, synthetic PMS bookings (Sunday-ending weeks),
Stripe booking revenue, Klaviyo, promotion calendar, availability, ADR, weather,
holiday calendar.

Pinterest launch 2023-02-06 is a documented launch, not an unknown gap.

## Defects

Twelve defects `SP-C-001`…`SP-C-012` in `sealed/expected_issues.json`, including
unknown Google CA gap (not zero-fill), missing CO availability (not imputed),
documented Meta prospecting off (zero-fill may be AUTO_SAFE), rates not additive,
and no automatic prospecting/retargeting merge.

## Semantic coverage

Positive families present on v1 baseline: `PROMOTION_TIMING`,
`PRICE_DISCOUNT_TIMING`, `DOWNSTREAM_MEDIA`, `REMARKETING_TARGETING`,
`ORGANIC_MEDIA_TIMING`. Decision class remains advisory. Causal roles are not
assigned.

Negative controls (must not become causal claims): snowfall×Pinterest,
holiday×paid search, availability×Meta in UT, ADR×organic in peak season.

## DOMAIN_VIEW v1 baseline

Local synchronous path: `run_pre_eda_diagnostics` + structured responses
(ASSESSMENT, INSIGHT, ADVISORY, SEMANTIC_INTERVIEW, MODELING_FEASIBILITY,
GUIDED_REMEDIATION). Official Meridian EDA: `NOT_RUN_IN_GENERATOR`. Terminal
state: `NOT_CLAIMED_LOCAL_BASELINE`. Cloud run: no.

Semantic status: `MODELER_REVIEW_REQUIRED`. Causal roles assigned: false.

## Training firewall

Typed `DatasetRole.SEALED_HOLDOUT` rejects:

- CandidateLesson extraction (`REJECTED_HOLDOUT_INPUT`)
- inclusion in A+B promotion evidence
- `evaluate_experience_episode` candidate generation
- evaluation-only reflections as training input

Filename heuristics are not the security boundary.

## Future EXPERIENCE_APPLIED protocol

Same Dataset C, same fingerprints, same rules/tools/Meridian configuration,
different DOMAIN_VIEW. Compare with `app/mel/holdout_compare.py`. Advisory
routing may change. Deterministic calculations, official Meridian severity, and
`MODEL_READY` logic must not. This file records **no** v2 result.

## What this does not prove

- `EXPERIENCE_LEARNED`
- DOMAIN_VIEW v2
- `EXPERIENCE_APPLIED`
- a cloud Dataset C `MODEL_READY` run
- official Meridian EDA on Summit & Pine
