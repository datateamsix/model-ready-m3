# PreM3 rebrand migration

Factual record of the 2026-08-15 product rename.

## Old hierarchy

- ModelReady = product
- M3 Agent = autonomous worker
- M3 = Map. Mend. Model-Ready.
- MEL = ModelReady Experience Loop
- M3 Learning Receipt = user-facing learning proof

## New hierarchy

- PreM3 = product and autonomous pre-modeling agent
- M3 = Map. Mend. Model. operating method / Media Mix Modeling reference
- MEL = PreM3 Experience Loop
- PreM3 Learning Receipt = user-facing proof of promoted experience
- MODEL_READY = verified pre-modeling terminal state

## Why

The system now owns the complete pre-modeling assignment, not only readiness checking. The new name describes the work that happens before the MMM is fit.

## Machine identifiers intentionally preserved

- Python distribution name `model-ready-m3`
- ADK agent name `modelready_m3`
- environment namespaces `M3_*` and `MODELREADY_*`
- class names `ModelReadyManifest`, `ModelReadyError`
- machine files `model_ready_manifest.json`, `m3_eda_analysis.json`, `pre_modeling_handoff.md`
- machine state `MODEL_READY`
- serialized receipt types `EXPERIENCE_LEARNED` / `EXPERIENCE_APPLIED`

## Files renamed

- `docs/context/01_PRODUCT_SPEC_MODELREADY.md` → `docs/context/01_PRODUCT_SPEC_PREM3.md`

`10_MODELREADY_AGENTIC_LEARNING_SYSTEM.md` did not exist.

## Contracts preserved

No serialized field keys or readiness enums were renamed for branding. Historical artifacts remain readable.

## Cloud resources unchanged

- GCP project `modelready-m3` / `912257136465`
- Cloud Run service `modelready-m3`
- Cloud Run Job `meridian-eda-worker`
- runtime SA `m3-runtime@modelready-m3.iam.gserviceaccount.com`
- GCS buckets `modelready-m3-912257136465-raw` and `-artifacts`
- BigQuery datasets `modelready_ops`, `modelready_experience`, `modelready_models`

No duplicate PreM3 cloud project, buckets, datasets, or services were created.

## Remaining legacy terms

Expected retained occurrences:

- historical Decision Log entries from 2026-08-13
- Source Update Manifest v1 record
- deprecated-term list in `docs/PREM3_BRAND_AND_NAMING.md`
- machine identifiers listed above
- diagram filename `modelready_m3_adk_identity_runtime.svg`
- historical proof artifacts and tags (`phase1-precloud-golden`, `cloud-alive`, `cloud-taskmaster`, `pre-modeling-golden`)

## Repository rename

- previous remote: `datateamsix/model-ready-m3`
- current remote: `datateamsix/prem3`
- GitHub redirect from the old name is active
- local origin updated to `https://github.com/datateamsix/prem3.git`

## Python package decision

Keep `name = "model-ready-m3"` in `pyproject.toml`. Changing the distribution name would risk ADK discovery, Docker/build imports, and local editable installs. Only the public description metadata was updated.
