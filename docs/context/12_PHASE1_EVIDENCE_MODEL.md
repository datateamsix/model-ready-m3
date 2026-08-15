# Phase 1 evidence model

Judges should be able to follow one Dataset A run without trusting agent prose.

```text
raw package fingerprint
  → detected issues
  → authorized deterministic transforms
  → transformed artifacts (URI + SHA-256)
  → readiness receipt (MR-001 … MR-018)
  → BigQuery publication receipt + parity
  → Meridian input contract
  → MODEL_READY gate
```

## Input evidence

`dataset_fingerprint` hashes the immutable raw package. Each transform records `SourceArtifactEvidence` (`role`, `uri`, `sha256`). Single-input tools also expose `source_uri` / `source_sha256`. `build_model_ready_frame` records all seven source roles: Google media, Meta media, Shopify KPI, GA4 organic, controls, population, and model intent.

## Issue evidence

Issues start `OPEN`, move to `REMEDIATING` while AUTO_SAFE tools run, and become `RESOLVED` only after a matching `APPLIED` transform with an output fingerprint. Resolution stores `resolution_action_ids` and transform metrics. Failed remediation leaves the issue unresolved and fails the run.

## Transformation evidence

Provenance stores identifiers, hashes, parameters, and row counts — never raw rows. MR-018 requires the dataset fingerprint, required tools, input and output fingerprints, full-frame source roles, and the final model-artifact fingerprint.

## Gate

`evaluate_model_ready_gate` derives `readiness_pass`, `publish_pass`, `parity_pass`, `contract_pass`, and `provenance_pass` from receipts. Caller-supplied `"PASS"` strings cannot set `MODEL_READY`. `provenance_pass` reuses MR-018 plus the same completeness check.

## State

`MODEL_READY` is a success milestone. True terminal stages are `FAILED` and `COMPLETE`. `MODEL_READY → LEARNING` and `MODEL_READY → WAITING_FOR_MODEL_APPROVAL` are legal. Phase 1 scripts still stop displaying at `MODEL_READY`.
