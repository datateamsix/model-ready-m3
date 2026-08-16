# Dataset B — Stride & Field learning evidence

Status: **PREM3_DATASET_B_LEARNING_EVIDENCE_READY**

This is inspectable proof that an independent synthetic pre-modeling assignment exists so MEL can evaluate whether a reusable low-risk lesson appears across Dataset A and Dataset B. It is **not** a claim that PreM3 learned from Dataset B.

## Identity

| | |
|---|---|
| Business | Stride & Field (synthetic outdoor/running apparel D2C + marketplace) |
| Path | `datasets/stride_and_field/dataset_b/` |
| Generator | `scripts/generate_dataset_b.py` |
| Shared stack | `app/synthetic/mmm.py` (extracted from Music Center `scripts/generate_demo_data.py`) |
| Seed | `20260817` |
| Generator version | `1.0.0` |
| KPI | Shopify orders |
| Geos | NE, MA, SE, MW, MT, WE (156 Monday weeks, 2023-01-02–2025-12-22) |

**Not** Music Center `datasets/music_center/dataset_b/`. That remaining fixture is a related Music Center schema-family episode.

**Not** Dataset C. Summit & Pine stay sealed.

## Synthetic tooling

Dataset B extends the Music Center generator primitives rather than inventing a second RNG/hash/CSV stack:

- `stable_rng` / `split_weekly_total` / `write_csv` / `sha256_file`
- Music Center Dataset A regeneration still uses those helpers
- Dataset C keeps its own sealed generator and was not modified

## Providers

Directory-trust providers already present: Microsoft Ads, TikTok Ads, Amazon Ads. A **minimal** Klaviyo directory stub was added (`trust=directory`, rates marked non-summable). It is not executable field mapping.

## Seeded defects

Twelve defects (`SF-B-001`…`SF-B-012`) are declared in `expected/expected_issues.json`. Surfaces differ from Music Center Dataset A’s five defects (Meta `amount_spent` / Google daily grain / CA-TX-FL-NY).

## Intelligence

`expected/expected_run_intelligence.json` is **computed** from the generated truth table after write. Tests recompute parameter budget and semantic trigger **families** (not question wording) and compare.

Computed lenient observations-per-parameter ratio is **5.538462**, pressure band `SEVERE`. That is not a clone of Dataset A’s 3.74 ratio. The heuristic cannot block `MODEL_READY`.

Semantic families present: `PROMOTION_TIMING`, `PRICE_DISCOUNT_TIMING`, `DOWNSTREAM_MEDIA`, `ORGANIC_MEDIA_TIMING`. Decision class remains advisory.

## MEL

- Dataset-B-like episode close + `ExperienceReflection` is tested.
- Reflection has no operational authority.
- Cross-episode candidates from A+B can be **reported** (`independent_context_count`, `common_pattern`, `cross_episode_differences`, `generalization_basis`).
- Tests assert `PROMOTE` is not forced.
- Holdout episodes are rejected by `propose_cross_episode_candidates`.
- DOMAIN_VIEW remains `1.0.0` / `b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf` with **0** promoted lessons.

## Dataset C integrity

Summit & Pine lives at `datasets/summit_and_pine/dataset_c/`. `scripts/generate_dataset_b.py` does not import or write Dataset C paths. The Episode Core furniture-stub fingerprints are obsolete; see `docs/proof/DATASET_C_SUMMIT_AND_PINE_HOLDOUT.md`.

## What this does not prove

- `EXPERIENCE_LEARNED`
- DOMAIN_VIEW v2
- `EXPERIENCE_APPLIED`
- a required reusable lesson (correct result may still be `NO_SAFE_PROMOTABLE_LESSON`)
- a cloud Dataset B `MODEL_READY` run (deferred)

Cloud Dataset B execution is **not** claimed here. Local generator, defect, semantic, episode/reflection, A+B candidate, and Dataset C integrity tests are the proof surface.
