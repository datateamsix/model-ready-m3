# 17 — Import and Publish Governance

**Status:** Canonical for Mission 2 Google connections and import/publish contracts (M2-11).  
**Does not implement:** Drive/BigQuery materialization into `DatasetUpload`, or MODEL_READY artifact publishing (M2-12).

Clerk authentication is not Google authorization. Tenant identity is never derived from a Google email, subject, Cloud project, Drive owner, or BigQuery principal.

## Canonical states

These three states must never collapse into a single `READY` enum.

| State | Owner | Means | Does not mean |
|---|---|---|---|
| **IMPORT_READY** | Deterministic evaluator `evaluate_import_readiness` | Selected source is authorized, bound, role-mapped, version-identified, and safe to materialize into an immutable DatasetUpload | Meridian-ready, repaired, statistically suitable, `MODEL_READY` |
| **MODEL_READY** | Existing deterministic execution pipeline (validators + official Meridian EDA gate) | Unchanged Mission 1/2 terminal pre-modeling state | Import eligibility or publish destination proof |
| **PUBLISH_READY** | Deterministic evaluator `evaluate_publish_readiness` | A MODEL_READY run plus a bound destination satisfy the Publish Contract | “User asked to publish” or “a publish was attempted” |

Gemini may explain receipts. Gemini may not declare any of these states.

`IMPORT_READY != MODEL_READY`. A source can be IMPORT_READY and later fail pre-modeling.

## Principles

1. Authority before access.
2. Explicit source binding.
3. Explicit destination binding.
4. Least privilege.
5. Deterministic manifests.
6. Immutable or version-verified source identity.
7. No silent source discovery.
8. No ambiguous role mapping.
9. Provenance survives materialization.
10. Customer data is never re-parented across tenants/projects.
11. PreM3 writes only to explicitly bound destinations.
12. The model cannot select storage authority.
13. Import and publish readiness require receipts.
14. User-visible names are not resource authority.
15. Source changes invalidate stale readiness rather than being silently accepted.

## Source types

| Type | Evidence | Materialization (M2-12) |
|---|---|---|
| `GCS_UPLOAD` | Verified Mission 10 `DatasetUpload` + `prem3_upload_manifest.v1.json` | Existing DatasetUpload (already materialized) |
| `GOOGLE_DRIVE` | Active `GoogleConnection` + `DriveWorkspaceBinding` + explicit file IDs | Must become DatasetUpload; never bypass |
| `BIGQUERY` | Active connection + bound source tables/views + inspectable schema/version | Must become DatasetUpload; never bypass |

Customer source tables may live outside the PreM3 depot (`analytics.google_ads`, `marketing.meta_ads`, …). The governed warehouse destination is always `<customer_project>.prem3_modeling`.

## Canonical Drive depot

- Visible folder name (convention only): **`prem3-modeling`** (lowercase).
- Authority: **Google Drive folder ID**, never a name query.
- OAuth capability: `GOOGLE_DRIVE` → scope `https://www.googleapis.com/auth/drive.file`.
- Do not auto-bind a same-named folder if the stored ID disappears; mark the binding degraded and require deliberate repair.

Layout under the bound root:

```text
prem3-modeling/
  imports/<workspace_id>/<dataset_id>/
  exports/<workspace_id>/<dataset_id>/<run_id>/
  reports/<workspace_id>/<dataset_id>/<run_id>/
```

PreM3 IDs are path authority. Display names are not.

Google Sheets are **not** IMPORT_READY in M2-11. Only CSV, Parquet, and JSON have a proven DatasetUpload materialization path.

## Canonical BigQuery depot

- Dataset ID: **`prem3_modeling`** (underscore; BigQuery cannot use the hyphenated Drive name).
- Friendly/display name: **`prem3-modeling`**.
- Pattern: `<customer_project>.prem3_modeling`.
- OAuth `BIGQUERY_WRITE` scope does **not** imply `write_verified=true`. Cloud IAM remains authoritative; write verification is an explicit mutation/setup result.

### Customer publish table naming (frozen for M2-12)

PreM3-owned model-consumption tables remain `model_input_{sanitized_run_id}` inside the PreM3 ops project.

Customer depot outputs (future M2-12, not executed here):

| Asset | Name |
|---|---|
| Versioned MODEL_READY table | `model_ready_{dataset_id}_{run_id}` (sanitized, `[a-zA-Z0-9_]`) |
| Active pointer view | `model_ready_{dataset_id}_current` |
| Location | Bound destination location; mismatch is `DESTINATION_LOCATION_MISMATCH` |

Reruns create a new versioned table and may retarget the current view. Overwrite of a versioned table for the same `run_id` is explicit (`OVERWRITE_POLICY_EXPLICIT`).

## Source roles

Reuse `CanonicalRole` from `app/core/source_inventory.py`. Do not invent a second taxonomy.

`paid_media` · `kpi` · `revenue` · `organic_media` · `controls` · `population` · `inactivity_evidence` · `model_intent`

`unknown` is never IMPORT_READY.

## Source identity and change

| Source | Identity | Version |
|---|---|---|
| GCS_UPLOAD | `upload_file_id` | Frozen GCS `generation` + checksum |
| GOOGLE_DRIVE | Drive file ID | `headRevisionId` / `md5Checksum` / `version` (provider-supported) |
| BIGQUERY | `project.dataset.table` | `etag` + `lastModifiedTime` (and bytes when present) |

If the provider cannot supply a stable change identity: **NOT IMPORT_READY** (`SOURCE_VERSION_UNVERIFIABLE`).

M2-12 must revalidate version identity immediately before materialization. On mismatch: `SOURCE_CHANGED_SINCE_IMPORT_READY`, supersede the current receipt, require revalidation. Do not silently import different bytes under an old receipt.

## Import Contract

`prem3.import.v1` — typed `PreM3ImportContractV1`.

Fingerprint is SHA-256 over canonical JSON of semantic fields (object selection, roles, provider identity, source/version identity, binding). Timestamps, status, and check results are excluded. Equivalent manifests fingerprint identically.

Only `evaluate_import_readiness(...)` may emit `IMPORT_READY`.

## Publish Contract

`prem3.publish.v1` — typed `PreM3PublishContractV1`.

PUBLISH_READY requires MODEL_READY evidence, a bound destination, write eligibility, deterministic naming, and identified artifacts. It does not publish data.

Drive targets: `exports/.../<run_id>/` and `reports/.../<run_id>/` under the bound `prem3-modeling` folder.

BigQuery target: bound `<project>.prem3_modeling` only. The model cannot select a destination.

## Future flows (frozen)

```text
GCS_UPLOAD | GOOGLE_DRIVE | BIGQUERY
        → PreM3ImportContractV1 → IMPORT_READY
        → materializer → DatasetUpload → VERIFIED manifest
        → DatasetEvaluationRef → ExecutionContext → ADK
        → MODEL_READY
        → PreM3PublishContractV1 → PUBLISH_READY
        → Drive prem3-modeling and/or BQ prem3_modeling
```

## Issue taxonomy (stable codes)

`CONNECTION_INACTIVE` · `BINDING_MISSING` · `RESOURCE_NOT_FOUND` · `PERMISSION_DENIED` · `FORMAT_UNSUPPORTED` · `OBJECT_EMPTY` · `SCHEMA_UNREADABLE` · `SOURCE_ROLE_MISSING` · `SOURCE_ROLE_AMBIGUOUS` · `PROVIDER_UNRESOLVED` · `SOURCE_VERSION_UNVERIFIABLE` · `SOURCE_CHANGED_SINCE_IMPORT_READY` · `DESTINATION_NOT_WRITABLE` · `DESTINATION_LOCATION_MISMATCH` · `MODEL_READY_REQUIRED` · `PUBLISH_ARTIFACT_MISSING` · `CONNECTION_ACTIVE` · `SOURCE_AUTHORIZED` · `SOURCE_BOUND` · `RESOURCE_EXISTS` · `FORMAT_SUPPORTED` · `OBJECT_NONEMPTY` · `SCHEMA_INSPECTABLE` · `VERSION_IDENTITY_AVAILABLE` · `PROVIDER_RESOLVED` · `ROLE_ASSIGNED` · `ROLE_MAPPING_UNAMBIGUOUS` · `DUPLICATE_SELECTION_ABSENT` · `MANIFEST_COMPLETE` · `MODEL_READY_VERIFIED` · `DESTINATION_BOUND` · `DESTINATION_AUTHORIZED` · `DESTINATION_EXISTS_OR_CREATABLE` · `DESTINATION_WRITABLE` · `LOCATION_COMPATIBLE` · `NAMING_DETERMINISTIC` · `REQUIRED_ARTIFACTS_PRESENT` · `OVERWRITE_POLICY_EXPLICIT` · `LINEAGE_COMPLETE`

## Disconnect

Revoke provider access where supported, delete encrypted credentials, mark the connection `REVOKED`, mark bindings unavailable, and invalidate *current* IMPORT_READY. Do **not** delete Drive/BQ customer resources or historical receipts.
