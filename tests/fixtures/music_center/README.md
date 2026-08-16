# Music Center golden demo fixtures

**Music Center** is a fully synthetic ecommerce retailer for musical instruments used as the reproducible PreM3 hackathon scenario.

The fixture is designed to behave like a small but realistic MMM data package rather than a toy single-table CSV. It includes provider-shaped exports for Google Ads, Meta Ads, GA4, Shopify/commerce, controls, and geo population reference data.

## Generate the fixtures

From the repository root:

```bash
python scripts/generate_demo_data.py
```

Generate only Dataset A:

```bash
python scripts/generate_demo_data.py --dataset dataset_a
```

The generator is deterministic. The default seed is `20260815`, and every generated file receives a SHA-256 fingerprint in its `generation_manifest.json`.

## Business / modeling shape

- modeling target: Google Meridian
- intended model scope: geo
- canonical grain: weekly × geo
- geos: CA, TX, FL, NY
- Dataset A history: 2024-01-01 through 2026-06-29 (131 weekly periods)
- Dataset B history: 2024-02-05 through 2026-07-27 (130 weekly periods)
- KPI: Shopify orders
- revenue translation: Shopify net revenue / orders
- modeled paid channels: paid search, Shopping, paid social
- organic signal: GA4 organic sessions
- controls: synthetic consumer sentiment, competitor discount index, Music Center promotion indicator
- population: synthetic geo reference values

All business values are synthetic. No real customer or platform account data is included.

## Generated files

Each dataset directory receives:

```text
raw/google_ads_daily.csv
raw/meta_ads_weekly.csv
raw/ga4_weekly.csv
raw/shopify_weekly.csv
raw/controls_weekly.csv
raw/geo_population.csv
raw/model_intent.json
truth/expected_model_ready_weekly.csv
generation_manifest.json
```

Runtime tools must receive only `raw/`. `truth/expected_model_ready_weekly.csv` is **regression truth**, not an M3-produced artifact and not a runtime input. Tests may load it only after M3 independently produces the final model frame.

`raw/model_intent.json` is legitimate user/workflow input. It names the KPI, revenue field, grain, and selected controls. It does not contain the numerical answer.

On the default seed, Dataset A produces approximately:

- Google Ads: 11,005 rows, including exactly one injected duplicate
- Meta Ads: 1,572 campaign-week-geo rows
- GA4: 524 week-geo rows
- Shopify: 524 week-geo rows
- controls: 524 week-geo rows
- clean regression truth: 524 week-geo rows

Dataset B changes campaigns/context while preserving the related schema family for the later learning demonstration.

## Dataset A — Phase 1 golden path

Dataset A deliberately contains **exactly five Phase 1 seeded defects**:

1. one exact duplicated Google Ads campaign row;
2. Google Ads ISO dates vs Meta `MM/DD/YYYY` dates;
3. daily Google Ads data vs weekly KPI/other sources;
4. Meta `amount_spent` encoded as currency strings such as `$1,234.56`;
5. inconsistent Meta channel labels: `Meta`, `Paid Social`, and `paid_social`.

The exact ground truth, expected evidence, remediation class, and Meridian rule family are declared in `expected_manifest.json`.

Campaign-level source data and derived CTR/CPC fields are intentionally realistic. Campaign-to-modeled-channel aggregation is a required transformation, while CTR/CPC must not be treated as summable media execution metrics.

## Dataset B — MEL / Experience Applied setup

Dataset B is a related future episode, not a duplicate of Dataset A. It changes Meta campaign names and introduces the channel variant `FB / IG` while retaining the Meta `amount_spent` field.

That field is intentionally aligned to the learning example in the PreM3 Experience Loop:

```text
meta_ads.amount_spent → media_spend
```

The fixture does **not** claim that M3 learned this mapping. Dataset A/B only provide the controlled conditions required to measure whether a validated lesson later changes M3's resolver behavior. Any improvement in tool calls, approvals, confidence, latency, or trajectory must come from actual runs.

## Guardrails

- Seeded defects are allowed in ground-truth metadata because they are synthetic test facts.
- Never hard-code M3 readiness scores, tool-call counts, learning improvements, or receipt metrics into the fixture.
- Never treat `truth/expected_model_ready_weekly.csv` as agent output or tool input.
- Do not fabricate missing KPI/control observations merely to get a passing result.
- Raw fixture data is synthetic and safe to commit; real customer/raw data must never be committed.
