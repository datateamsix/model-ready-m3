# Cloud first PreM3 learning cycle

**Date:** 2026-08-17  
**Status:** EXPERIENCE_APPLIED on frozen Cloud Run revision `modelready-m3-00013-c4s`  
**Does not claim:** bootstrap `current/domain_view.json` replacement; Dataset C Map/Mend `MODEL_READY`; posterior fit

This is the cloud-controlled A+B → DOMAIN_VIEW v2 → same Dataset C application. It is stacked on the provider-agnostic coordinator qualification. It does not rebuild the application image.

Reproduction: `python scripts/run_cloud_learning_experiment.py`

## Freeze

| Control | Value |
|---|---|
| Service | `modelready-m3` / `us-central1` |
| Revision | `modelready-m3-00013-c4s` |
| Image digest | `sha256:7dffe4904c1a3ce9e2bb7426793954608bb3d3b5c274b2dc592fcefb0246f6d6` |
| Image code SHA | `1222eb6fcdabec5ea6132347c8b6df2bc907f705` |
| Registry | `gs://modelready-m3-912257136465-artifacts/experiments/cloud_first_learning_cycle_001/domain_view_registry/` |
| C-v1 and C-v2 revision | identical |

Pointer updates on that GCS prefix are data. A code change would require a new revision and a restart of C-v1/C-v2.

## Order of operations

1. Probe Cloud Run: DOMAIN_VIEW `1.0.0`, promoted lessons `0`
2. Capture Dataset C v1 **before** any promotion
3. Reflect cloud Dataset A (`m3cloud653724094004`, `MODEL_READY`)
4. Reflect Dataset B from intelligence evaluation of the same B package (cloud Map/Mend run `m3cloud856c4fdede10` is non-terminal `REMEDIATING`)
5. Extract A+B candidates. Dataset C excluded.
6. Promote one `ROUTING_HINT` → DOMAIN_VIEW `1.0.1` as GCS data
7. Probe Cloud Run on the **same** revision: DOMAIN_VIEW `1.0.1`, promoted lessons `1`
8. Rerun the same Dataset C
9. Measure only the predeclared effect

## C-v1 control

Assignment mode: `INTELLIGENCE_EVALUATION` against the sealed Summit & Pine model-ready table. Cloud Run cannot run `run_pre_eda_diagnostics` without a published table, and Dataset C correctly remains unpublished because USER_REQUIRED evidence remains. The holdout comparison uses the same GCS-loaded DOMAIN_VIEW the frozen revision loads.

| Field | C-v1 |
|---|---|
| Run | `dataset-c-v1-cloud-00013` |
| DOMAIN_VIEW | `1.0.0` / `b3ad518e…8e46cf` |
| Retrieved claims | `[]` |
| `modeler-questions` rank | **2** |
| Sealed package fingerprint | `f1bfaa5ba98b8f6d94cccb6b7a19c1e50ab8e315567e82fa3cf22129193bf18f` |
| Model-input fingerprint | `0a79f1c411a5268f15822d9d1d8afced8ac0171d0b6549479571640f134a4cee` |

## Learning evidence

| | |
|---|---|
| A episode | `ep-m3cloud653724094004-8839ba8855077a04` from cloud run `m3cloud653724094004` |
| B episode | `ep-dataset-b-cloud-learning-00013-2f2de878cf841b6d` |
| Selected candidate | `cand-semantic_question_routing-9e0ebb37bed1` |
| Authority | `ROUTING_HINT` |
| Independent contexts | 2 |
| EXPERIENCE_LEARNED | `experience/cloud_learning/experience_learned_receipt.json` |

Per-episode-only candidates were rejected for missing independent support or missing regression. Dataset C did not enter candidate generation.

## DOMAIN_VIEW as data

| | v1 | v2 |
|---|---|---|
| version | `1.0.0` | `1.0.1` |
| fingerprint | `b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf` | `5847aaf4c1740cc25b52c664114ba5d2c97ec587bb44f2a22e18c0f5154e42f1` |
| promoted experiential claims | 0 | 1 |
| Cloud Run revision | `00013-c4s` | `00013-c4s` |

Bootstrap `app/domain/intelligence/data/current/domain_view.json` remains `1.0.0`.

This v2 fingerprint is **not** the local-cycle fingerprint `3a05706d…`. The cloud candidate has different source episode IDs.

## Declared application (no inference)

Predeclared before C-v2:

- type `HANDOFF_PRIORITY_UP`
- target `modeler-questions`
- success `rank <= 1`
- direction `LOWER_IS_BETTER`
- allowed fields: `handoff_action_order`, `recommended_presentation_order`, `retrieved_claim_ids`

| Metric | C-v1 | C-v2 |
|---|---|---|
| `modeler-questions` rank | 2 | 1 |
| SEMANTIC_INTERVIEW presentation rank | 4 | 2 |
| retrieved claim | none | `DV-EXP-cand-semantic_question_routing-9e0ebb37bed1` |
| undeclared field changes | 0 | 0 |
| package fingerprint | unchanged | unchanged |
| model-input fingerprint | unchanged | unchanged |

Receipt: `app-2bf74f1f98e5c6d7`.

## What this does not prove

- Dataset C Map/Mend `MODEL_READY`
- Official Meridian EDA on Dataset C
- Bootstrap DOMAIN_VIEW file replacement
- Frontend integration
- Eventarc / ambient Taskmaster
