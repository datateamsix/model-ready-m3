# Product Spec — ModelReady

## Product

**ModelReady**  
*Autonomous Data Preparation for Marketing Measurement*

**Autonomous worker:** **M3 Agent**  
**M3 meaning:** **Map. Mend. Model-Ready.**  
**Domain meaning:** Media Mix Modeling

First modeling target: **Google Meridian**

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
1. readiness assessment;
2. issue inventory;
3. auto-remediation summary;
4. remaining human decisions;
5. normalized dataset;
6. Meridian adapter/mapping;
7. transformation manifest;
8. provenance and audit trail;
9. machine-readable validation results;
10. validated BigQuery model table/view;
11. generated Meridian input contract/config;
12. publish-verification receipt;
13. M3 Learning Receipt when new reusable experience is created.

## Primary workflow

### Trigger
New files land in upload storage.

### Intake
- inventory files;
- inspect headers/sample rows;
- infer provider/report;
- identify temporal/geographic grain;
- identify metrics/dimensions.

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

### Remediation planning
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

### Transform
Apply approved/safe transformations.

### Validate
Re-run all checks and compare before/after.

### Publish

After deterministic readiness validation passes, M3 may autonomously publish the model-ready artifact to BigQuery.

Minimum BigQuery contract:
- validated model-input table;
- stable Meridian-facing view;
- channel mapping;
- validation results;
- transformation manifest;
- provenance;
- run metadata.

M3 must verify that the published BigQuery artifact matches the validated artifact before setting the run to `MODEL_READY`.

### Deliver

Artifacts:
- `model_ready.csv` or parquet;
- BigQuery model-input table/view;
- `meridian_mapping.json`;
- generated Meridian input/config contract;
- `mmm_unified_schema.pb/json` where feasible;
- `readiness_report.json`;
- `readiness_report.md`;
- `transformation_manifest.json`;
- `provenance.json`;
- `publish_receipt.json`;
- `run_summary.json`.

### Model handoff

Actual Meridian execution is **approval required** for the hackathon architecture.

M3 may prepare and recommend:
- BigQuery source/view;
- field mappings;
- channel names;
- model-input configuration;
- execution package.

The user may then approve a Meridian run. A stretch implementation may use Cloud Workflows and Colab Enterprise, consistent with Google's Cortex for Meridian execution pattern.

### Learn

Record episode, outcomes and candidate lessons. Generate an **M3 Learning Receipt** for newly promoted experience and an **Experience Applied** receipt when validated knowledge materially changes a later run.

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
→ optional `WAITING_FOR_MODEL_APPROVAL`
→ optional `MODELING`

Primary summary:

**Meridian Readiness: 94/100**

- 12 issues detected
- 8 automatically resolved
- 3 warnings
- 1 approval required

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
- verify published output.

**APPROVAL_REQUIRED**
- selecting/changing modeling priors;
- materially changing business semantics;
- launching a Meridian model run;
- overwriting a production model contract not owned by the current run.
