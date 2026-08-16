# Meridian Readiness Spec

## Goal

Convert Meridian documentation into executable readiness checks.

This document is a starting specification; every rule should eventually carry:
- rule ID;
- severity;
- deterministic implementation;
- source/evidence URL;
- applicability conditions;
- remediation options;
- auto-remediation safety class.

## Core variable families

Meridian DataFrame loading supports concepts including:
- geo;
- time;
- kpi;
- revenue_per_kpi;
- population;
- controls;
- media;
- media_spend;
- reach;
- frequency;
- rf_spend;
- non_media_treatments;
- organic_media;
- organic_reach;
- organic_frequency.

## Rule families

### MR-001 — Time format
**Check:** time values can be normalized to `yyyy-mm-dd`.
**Severity:** ERROR
**Auto:** safe if parsing is unambiguous.

### MR-002 — Missing values
**Check:** no unsupported missing values remain in model input.
**Severity:** ERROR
**Auto:** depends on semantic role.

Media missing because channel was inactive may be safely zero-filled when evidence supports inactivity.

KPI/control missing values must not be zero-filled automatically merely to satisfy completeness.

### MR-003 — Consistent temporal grain
**Check:** all required variables align to a common temporal grain.
**Recommendation:** weekly is preferred for typical use.
**Severity:** ERROR/WARN depending on mismatch.

### MR-004 — Historical sufficiency
Check model context against directional history guidance.

Examples from current Meridian documentation:
- geo model: generally at least two years of weekly history;
- national model: generally three years;
- monthly: generally at least three years.

Treat as guidance rather than an absolute guarantee of model quality.

### MR-005 — Geo granularity
Prefer geo-level data where available.

Check:
- consistent geo identifiers;
- population availability when required;
- low-volume geos;
- national vs geo model intent.

### MR-006 — Summability
KPI and non-R&F media exposure metrics should be summable across geography/time.

Reject direct use of:
- CTR;
- CPC;
- ROAS;
- averages/rates;
as summable execution inputs.

When raw components exist, derive valid volumes deterministically.

### MR-007 — Media/spend alignment
Media and media spend must align by:
- channel;
- geo;
- time.

### MR-008 — Reach/frequency mapping completeness
If R&F is used:
- reach mapping required;
- frequency mapping required;
- RF spend mapping required.

### MR-009 — Channel aggregation
Campaign/ad-group/creative data may need aggregation to modeled media channels.

Aggregation must preserve summable measures.

### MR-010 — Duplicate observation grain
No duplicate observation at canonical model grain unless aggregation is intentional.

### MR-011 — KPI semantics
KPI must represent the modeled response.

If KPI is non-revenue and revenue translation is desired, validate `revenue_per_kpi`.

### MR-012 — Population
For geo models, validate population coverage and alignment.

### MR-013 — Controls
Controls should be defensible confounders/predictors, not arbitrary correlated metrics.

This is partly semantic and may produce warnings rather than deterministic failure.

### MR-014 — Media variation
Flag channels with insufficient variation / effectively constant execution.

### MR-015 — Data-to-parameter sufficiency
Calculate directional data-to-effect / parameter diagnostics where configuration is known.

The numeric ratio is a deterministic diagnostic. Interpreting a ratio around or below 10 as high/severe parameter pressure is an `MMM_EVIDENCE_HEURISTIC` with `review_recommended=true`. It cannot independently block `MODEL_READY`. Never drop a confirmed confounder merely to improve the ratio. See `docs/context/intelligence/MODELING_FEASIBILITY_SPEC.md`.

### MR-016 — Complete calendar
Detect missing periods at expected cadence.

Classify missing periods as:
- inactive media;
- missing KPI/control;
- unknown.

### MR-017 — Units/currency
Ensure media spend units/currency are internally consistent before aggregation.

### MR-018 — Provenance
Every generated model field must map back to source fields and transformations.

### MR-019 — BigQuery publish parity
**Check:** the BigQuery model table/view matches the artifact that passed deterministic readiness validation.
**Severity:** ERROR
**Auto:** deterministic.

Validate:
- row count;
- required columns;
- data types;
- canonical grain;
- null behavior;
- field/channel mapping;
- version/run identity;
- checksum/fingerprint where practical.

A run cannot enter `MODEL_READY` if publish parity fails.

### MR-020 — Meridian handoff contract
**Check:** the published artifact has a complete model-input contract for the chosen Meridian loading path.
**Severity:** ERROR/WARN depending on execution intent.

Include:
- BigQuery project/dataset/view identity;
- time field;
- geo field where applicable;
- KPI;
- population where applicable;
- media columns;
- spend columns;
- R&F columns when applicable;
- controls/treatments/organic mappings when used;
- channel names.

This rule validates handoff completeness; it does not choose modeling priors.

## Readiness score

The readiness score is a product UX layer, not a Meridian-defined official score.

Therefore:
- never imply Google endorses the score;
- expose component checks;
- show blockers separately;
- a high score cannot override a blocker.

Suggested status:
- `BLOCKED`
- `NEEDS_DECISIONS`
- `READY_WITH_WARNINGS`
- `READY`

## Output adapter

Primary MVP targets:
- Pandas DataFrame / CSV compatible with Meridian loading;
- validated BigQuery model-input table;
- stable/versioned Meridian-facing BigQuery view;
- field/channel mapping JSON;
- generated Meridian input contract/config;
- optional MMM Unified Schema representation if feasible.

### Model-ready state

`MODEL_READY` means:
1. deterministic source/readiness checks pass;
2. required authorized remediation completes;
3. unresolved blockers = 0;
4. provenance complete;
5. PreM3 Model-Ready Manifest complete;
6. explicit model-consumption schema compiled;
7. versioned BigQuery model table written;
8. physical schema independently verified;
9. partition verified where applicable;
10. clustering verified where applicable;
11. column descriptions verified where required;
12. content fingerprint verified;
13. stable Meridian-facing endpoint verified;
14. Meridian input contract complete;
15. official Meridian EDA executed;
16. official HTML persisted;
17. structured EDA receipt persisted;
18. official Meridian ERROR count = 0;
19. PreM3 interpretation persisted;
20. modeler handoff persisted.

ATTENTION may still permit `MODEL_READY` with `review_recommended=true`. Official input rejection or ERROR produces `USER_REQUIRED` and a PreM3 User Resolution Pack.

`MODEL_READY` means the pre-modeling contract and official EDA gate pass. It does not guarantee posterior convergence, identifiability, stable ROI, business usefulness, or a particular modeler's final specification.

It does **not** mean a Meridian model has already been fit. EDA-only `sample_prior` is disclosed as `EDA_PRIOR_DIAGNOSTICS_ONLY` and is not approved for final modeling. EDA-only `knots < n_time` for geo-invariant time-only controls is disclosed and is not approved for final modeling.

### Meridian execution boundary

Three distinct Meridian surfaces:

1. **Autonomous pre-modeling EDA** — official `MeridianEDA` / `EDASpec()` against the confirmed BigQuery model input. Required for `MODEL_READY`. May call `sample_prior`. Must not call `sample_posterior` or fit the model.
2. **EDA-only `sample_prior`** — prior-probability diagnostics inside EDA. Recorded as `MERIDIAN_DEFAULT` / `EDA_PRIOR_DIAGNOSTICS_ONLY` / `approved_for_final_modeling=false`.
3. **Approval-gated posterior / model execution** — `WAITING_FOR_MODEL_APPROVAL` then `MODELING`. Out of scope until a human approves.

A stretch path may use Cloud Workflows and Colab Enterprise, following the official Cortex for Meridian pattern.

## Tests

Create fixtures for:
- national without R&F;
- geo without R&F;
- geo with R&F;
- organic media + treatments;
- malformed date;
- missing media;
- missing KPI;
- non-summable rate;
- inconsistent grain;
- bad channel mapping;
- duplicate grain;
- BigQuery schema mismatch;
- BigQuery row-count mismatch;
- incomplete Meridian handoff contract.
