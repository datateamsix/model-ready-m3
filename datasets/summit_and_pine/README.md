# Summit & Pine Dataset C — sealed holdout

**Summit & Pine** is a fully synthetic regional outdoor hospitality / mountain
lodging company (lodges, cabins, guided outdoor experiences, seasonal packages).
It is PreM3's independent MEL **evaluation holdout**.

This dataset was sealed before experiential lesson promotion.

Dataset C is an evaluation holdout, not training evidence.

It was not designed around a CandidateLesson discovered from Dataset A or
Dataset B.

## Role

Typed role: `SEALED_HOLDOUT`.

Training access, candidate-generation access, and reflection-training access are
`DENIED`. A holdout episode may exist operationally; its reflection role is
`EVALUATION_ONLY`.

Do not use Dataset C for:

- CandidateLesson generation
- cross-episode training evidence
- lesson promotion
- DOMAIN_VIEW construction
- MEL evidence sufficiency

until after a real lesson has been promoted from training episodes, and then
only as the **same sealed assignment** for DOMAIN_VIEW v2 application testing.

## Generate

```bash
python scripts/generate_dataset_c.py
```

Shared primitives live in `app/synthetic/mmm.py`. Seed **`20260816`** is kept
from the Episode Core placeholder. Generator **2.0.0** replaced that
outdoor-furniture stub with this hospitality assignment. Do not change the seed
casually.

## Shape

- modeling target: Google Meridian
- geo model, weekly grain
- 5 destination geos: CO, UT, CA, PN, NE
- KPI window: 2022-11-07 through 2025-10-27 (156 Monday weeks)
- media pre-period from 2022-08-29
- Pinterest launch: 2023-02-06 (documented launch, not an unknown gap)
- KPI: bookings (`revenue_per_kpi` is supporting)
- paid: Google Paid Search, Pinterest (upper funnel), Meta Prospecting, Meta Retargeting
- owned: GA4 organic sessions, Klaviyo sends
- controls: availability, snowfall, holiday calendar, ADR/price index, promotional packages

## Layout

```text
raw/                         runtime package only
truth/                       regression truth; not an M3 output
sealed/                      expected evaluation contracts + holdout copy
learning/holdout_manifest.json
baseline/domain_view_v1/     pre-learning DOMAIN_VIEW v1 baseline
generation_manifest.json
package_manifest.json
```

Runtime tools must receive only `raw/`. Tests and evaluators may read `sealed/`
and `baseline/`. Candidate extraction must not.

## Defects and semantics

Twelve seeded defects (`SP-C-001`…`SP-C-012`) are declared in
`sealed/expected_issues.json`. Positive semantic families and negative controls
are in `sealed/expected_semantic_conditions.json`.

Unknown Google Search absence is not zero. Missing availability is not
`AUTO_SAFE` to impute. Prospecting and retargeting must not be merged
automatically. Causal roles are not encoded from correlation.

## Future DOMAIN_VIEW v2

The same sealed package will be reused later with DOMAIN_VIEW v2. Only
DOMAIN_VIEW should be the independent variable. See
`sealed/expected_behavior_contract.json` and `app/mel/holdout_compare.py`.

This package emits no `EXPERIENCE_LEARNED` or `EXPERIENCE_APPLIED` receipt.
