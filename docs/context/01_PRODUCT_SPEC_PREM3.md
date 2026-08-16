# Product Spec — PreM3

## Product

**PreM3**
*A self-learning, autonomous pre-modeling agent for Google Meridian.*

**Operating method:** **Map. Mend. Model.**
**Secondary line:** Before you model, PreM3.
**Domain meaning of M3:** Media Mix Modeling

First modeling target: **Google Meridian**

Canonical product intelligence: `PREM3_PRODUCT_CONTEXT.md`.
MMM constitution: `PREM3_MMM_BOOT_CONTEXT.md`.

Four user-value behaviors: **Assess. Advise. Insight. Guide.**

PreM3 is simultaneously the product and the autonomous agent. Do not present a separate M3 Agent personality.

In **Map. Mend. Model.**, **Model** refers to completing and validating the model-consumption package and pre-modeling diagnostics—not fitting the Meridian MMM.

PreM3 was originally developed under the working name ModelReady. Some internal cloud identifiers retain that namespace for compatibility.

## Problem

MMM fails long before modeling begins.

Teams face:
- fragmented provider exports;
- incompatible grains;
- inconsistent naming;
- missing dates;
- duplicate observations;
- non-summable metrics;
- mixed currencies;
- unclear field semantics;
- incomplete geographic coverage;
- insufficient historical depth;
- missing controls;
- channel taxonomies that do not align;
- platform-specific schema quirks.

Existing workflows require analysts to manually inspect, transform and reconcile these datasets before they can even discover whether a model is feasible.

## User outcome

Provide raw marketing data.

Receive:
1. source/readiness assessment;
2. issue inventory;
3. automatic repair summary;
4. remaining human decisions;
5. model-ready artifact;
6. provenance and audit trail;
7. BigQuery model input;
8. physical verification;
9. stable Meridian endpoint;
10. Meridian input contract;
11. official Meridian EDA;
12. EDA findings;
13. PreM3 analysis;
14. PreM3 User Resolution Pack when blocked;
15. PreM3 Pre-Modeling Handoff;
16. future PreM3 Learning Receipt when a reusable lesson is actually promoted.

Completed episodes are evaluated by MEL. A PreM3 Learning Receipt is generated only when a scoped lesson is actually promoted.

## Product boundary

PreM3 owns source intake, mapping, semantic resolution, profiling, remediation, validation, provenance, model-input construction, BigQuery publication, BigQuery verification, the Meridian input contract, official Meridian pre-modeling EDA, EDA interpretation, user resolution guidance, modeler handoff, and experiential learning from completed episodes.

PreM3 does **not** autonomously own posterior sampling, production model fitting, final prior selection, ROI estimation, incrementality claims, response curves, budget optimization, or model-driven budget allocation.

PreM3 identifies both data problems and unresolved decisions that require human context.

## Primary workflow

### Trigger
New files land in upload storage.

### MAP
Understand the data before changing it:
- inventory files;
- inspect headers/sample rows;
- infer provider/report;
- identify temporal/geographic grain;
- identify KPI/media/control/treatment candidates;
- resolve semantics;
- establish provenance;
- determine what PreM3 knows and does not know.

### Registry resolution
Match provider metadata against known registry entries.

### Profiling
Calculate:
- row/column counts;
- data types;
- missingness;
- uniqueness;
- duplicate patterns;
- date range;
- cadence;
- continuity;
- variance;
- min/max/outliers;
- geo coverage;
- metric additivity candidates;
- currency/unit patterns.

### Semantic mapping
Map fields into normalized concepts:
- time;
- geo;
- KPI;
- revenue_per_kpi;
- population;
- controls;
- media;
- media_spend;
- reach;
- frequency;
- rf_spend;
- non_media_treatments;
- organic media.

### Readiness evaluation
Run deterministic Meridian-oriented rules.

### MEND
Safely resolve what can be resolved.

Classify each issue:

**AUTO_SAFE**
- date parsing;
- obvious column alias normalization;
- deterministic channel aggregation;
- zero fill for explicitly inactive media periods where evidence supports inactivity;
- type coercion when lossless;
- removal of exact duplicates;
- weekly alignment when aggregation semantics are valid.

**APPROVAL_REQUIRED**
- KPI imputation;
- control imputation;
- changing geographic grain;
- combining media channels;
- inferred currency conversion;
- ambiguous semantic mappings;
- dropping low-volume geos;
- selecting between clicks vs impressions as media execution.

**BLOCKED**
- irrecoverable missing KPI;
- contradictory semantic definitions;
- insufficient data with no valid alternative;
- unresolved unsupported grain.

MEND never means fabricate data, silently impute KPI, silently change causal semantics, silently merge channels, or silently change model configuration.

### Validate
Re-run all checks and compare before/after.

### MODEL — construct and prove the model-consumption input

After deterministic readiness validation passes, PreM3 may autonomously publish the model-ready artifact to BigQuery.

Minimum BigQuery contract:
- validated model-input table;
- stable Meridian-facing view;
- channel mapping;
- validation results;
- transformation manifest;
- provenance;
- run metadata.

PreM3 must independently verify that the published BigQuery artifact matches the validated artifact, then run official Meridian pre-modeling EDA, interpret structured findings, and produce the modeler handoff before setting the run to `MODEL_READY`.

### Deliver

Artifacts:
- `model_ready.csv` or parquet;
- BigQuery model-input table/view;
- `model_ready_manifest.json` (human title: PreM3 Model-Ready Manifest);
- `meridian_mapping.json`;
- generated Meridian input/config contract;
- official Meridian EDA HTML and structured receipt;
- `m3_eda_analysis.json` (human title: PreM3 EDA Analysis);
- PreM3 User Resolution Pack when blocked;
- PreM3 Pre-Modeling Handoff;
- `readiness_report.json`;
- `transformation_manifest.json`;
- `provenance.json`;
- `publish_receipt.json`;
- `run_summary.json`.

### Modeler handoff

Actual Meridian posterior / model fitting is **modeler-governed**.

PreM3 may prepare and recommend:
- BigQuery source/view;
- field mappings;
- channel names;
- model-input configuration;
- official EDA findings;
- review recommendations.

The user may then approve a Meridian run. A stretch implementation may use Cloud Workflows and Colab Enterprise, consistent with Google's Cortex for Meridian execution pattern.

### Learn

Record episode, outcomes and candidate lessons. Generate a **PreM3 Learning Receipt** only when a scoped lesson is actually promoted, and an **Experience Applied** receipt when validated knowledge materially changes a later run.

## UX

The experience should feel like an operations console rather than a chatbot.

Suggested stages:

`RECEIVED`
→ `DISCOVERING`
→ `PROFILING`
→ `MAPPING`
→ `ASSESSING`
→ `REMEDIATING`
→ `VALIDATING`
→ `PUBLISHING`
→ `EXPLORING`
→ `MODEL_READY`
→ `LEARNING`
→ `COMPLETE`

Optional: `WAITING_FOR_MODEL_APPROVAL` → `MODELING`

`MODEL_READY` is the operational pre-modeling outcome. `LEARNING` is post-task episode evaluation. Learning success is not required to validate the model artifact.

When PreM3 cannot safely continue, it concludes `USER_REQUIRED` and answers:

- what is wrong;
- why it matters;
- what PreM3 can fix;
- what PreM3 cannot safely decide;
- who needs to act;
- what they should do;
- what evidence is needed;
- when to rerun PreM3.

Primary summary should not let a 0–100 readiness score obscure blockers, official EDA findings, or review recommendations.

## Required demo defects

Seed known defects so we can prove accuracy:
- duplicated campaign rows;
- Google/Meta date format differences;
- missing inactive-media week;
- currency symbol/string spend field;
- daily Google Ads vs weekly KPI data;
- campaign-level data needing channel aggregation;
- CTR/CPC present but raw summable metric needed;
- inconsistent channel taxonomy;
- a KPI missing period requiring approval;
- insufficient history warning;
- ambiguous control variable;
- geo name mismatch.

## Success metrics

Per run:
- provider identification accuracy;
- field mapping accuracy;
- defect precision/recall;
- safe remediation success;
- false safe-remediation rate;
- final deterministic readiness;
- number of human decisions;
- runtime;
- tool trajectory score;
- artifact completeness.

Publishing metrics:
- BigQuery publish success;
- row-count parity;
- schema parity;
- checksum/fingerprint parity where applicable;
- generated Meridian contract completeness;
- provenance completeness.

Learning metrics:
- repeated-case tool calls reduced;
- mapping accuracy improved;
- approval requests reduced without increased errors;
- run time reduced;
- trajectory quality improved;
- regression suite unchanged/improved.

### BigQuery publication authority

**AUTO_SAFE after validation**
- create/write versioned model-input tables;
- create/update a run-scoped or versioned Meridian-facing view;
- write manifests and provenance;
- generate Meridian mappings/config;
- verify published output;
- run official Meridian pre-modeling EDA.

**APPROVAL_REQUIRED / modeler-governed**
- selecting/changing final modeling priors;
- materially changing business semantics;
- launching a Meridian posterior / model fit;
- overwriting a production model contract not owned by the current run.
