# Cloud pre-modeling golden run — Dataset A (Music Center)

Status: **PREM3_CLOUD_PREMODELING_GOLDEN_READY**

This is the core product proof. Raw Music Center files arrived in GCS. PreM3 mapped them, repaired only AUTO_SAFE defects, published a versioned BigQuery model-consumption table, independently read that table back, ran official Meridian EDA, and reached `MODEL_READY` only after the deterministic gate passed.

Machine companions:

- `evaluation/dataset_a_cloud_premodel_scorecard.json`
- `evaluation/cloud_premodeling_scorecard.json`
- `evaluation/demo/dataset_a_golden_run.json`
- `evaluation/cloud_revision_freeze.json`

Do not treat this document as the gate. The confirmation receipt is the gate.

## Runtime

| Field | Value |
|---|---|
| Branch | `feature/prem3-first-real-learning-cycle` |
| Code SHA | `f734ccce81e814498e3a8829173b8a95291f1aca` |
| Service | `modelready-m3` / `us-central1` |
| Revision | `modelready-m3-00012-8xq` |
| Image digest | `sha256:8a099d90e0a5bd99ee5ee663e906dde4190b82650a95a267ef3c206d843e5f69` |
| Runtime SA | `m3-runtime@modelready-m3.iam.gserviceaccount.com` |
| Invoker | `user:zrodaymusic@gmail.com` only (`allUsers` absent) |
| DOMAIN_VIEW loaded | `1.0.0` / `b3ad518e…` / 0 promoted lessons / `gcs_registry` |

## Input

| Field | Value |
|---|---|
| Run ID | `m3cloudc5b11fe79553` |
| Package | `gs://modelready-m3-912257136465-raw/music-center/mmm-demo/dataset-a/packages/dataset-a-cloud-golden-20260817/` |
| Dataset fingerprint | `43a1a4c2d3aecf270724ac78e1e01ae169db5be076e17dbfd314b17f868cdda5` |
| Providers | Google Ads, Meta Ads, GA4, Shopify, controls, geo population |
| Raw rows | Google 11005, Meta 1572, GA4 524, Shopify 524, controls 524, geos 4 |

Truth files were not staged.

## Map → Mend → Validate

Gemini chose run-level tools. Deterministic code executed them.

Trajectory: `initialize_dataset_run` → `apply_safe_remediations` → `validate_and_publish_run` → `run_pre_eda_diagnostics` → `inspect_modeling_feasibility` → `generate_semantic_readiness_interview` → `run_meridian_eda` → `complete_dataset_run`. All SUCCESS.

| Issue | Repair class | Result |
|---|---|---|
| MC-A-001 duplicate Google campaign rows | AUTO_SAFE | RESOLVED |
| MC-A-002 Google/Meta date-format mismatch | AUTO_SAFE | RESOLVED |
| MC-A-003 daily Google vs weekly grain | AUTO_SAFE | RESOLVED |
| MC-A-004 currency-formatted Meta spend | AUTO_SAFE | RESOLVED |
| MC-A-005 inconsistent Meta channel labels | AUTO_SAFE | RESOLVED |

USER_REQUIRED = 0. MODELER_REVIEW_REQUIRED = 0. Forbidden transforms attempted = 0. Open issues = 0.

Deterministic readiness: **PASS**. Model frame: 524 × 16. Fingerprint `7cfc15152067923b6ec6d2b77d6b4e4fae16b748eae24deb250939e7458fe18f`. Provenance: 9 transform records.

## Publish → Verify

Versioned table: `modelready-m3.modelready_models.model_input_m3cloudc5b11fe79553`

Stable view: `modelready-m3.modelready_models.meridian_input_music_center_mmm_demo`

Independent post-run query: 524 rows. Partition field `time`. Clustering `geo`. 16/16 columns described. Table description present. Publish parity **PASS**. Artifact fingerprint equals published fingerprint.

Pre-EDA diagnostics fingerprint the BigQuery table with the same `coerce_model_frame_types` + `MODEL_READY_COLUMNS` path used by publish parity. That alignment is what allowed Explore to start.

## Explore → Interpret → Handoff

PreM3 pre-EDA ran against the verified table. Official Meridian EDA ran on `meridian-eda-worker` with `google-meridian==1.8.0`. Posterior sampling and model fitting were both false.

| Official severity | Count |
|---|---|
| ERROR | 0 |
| ATTENTION | 12 |
| INFO | 10 |

ATTENTION does not block `MODEL_READY`. Review is recommended. Official findings remain in `eda/meridian_eda_receipt.json` and the HTML report. Pre-EDA set `official_meridian_findings_included = false`.

Four semantic questions were generated (promotion timing, price/discount timing, downstream media, organic timing). Handoff: `eda/pre_modeling_handoff.md`. Meridian input contract: COMPLETE. Consumption promotion: PROMOTION_VERIFIED.

## Terminal

`model_ready_confirmation_receipt.json` status = `MODEL_READY`.

Run state stage = `MODEL_READY`.

Gate evidence includes readiness, publish parity, physical schema, stable view, official EDA with zero ERROR, provenance, and handoff. Agent prose did not set the terminal state.

Episode closed as `ep-m3cloudc5b11fe79553-81ff06ae999bf918` with `terminal_outcome = MODEL_READY` and `learning_eligible = true`.

## What this does not prove

Dataset B and Dataset C did not complete this Cloud Run Map/Mend path. `RunCoordinator` still expects Dataset A runtime files and Dataset A issue IDs. That limitation is recorded in `evaluation/cloud_premodeling_scorecard.json` and does not weaken Dataset A.

Experiential learning on this revision is a separate milestone.
