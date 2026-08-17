# Backend Contract Requests

**Owner:** shared frontend/backend Mission 2 contract registry
**Canonical architecture:** `docs/context/14_MULTITENANCY_AND_IDENTITY_BOUNDARY.md`,
`docs/context/15_FRONTEND_INTEGRATION_AND_SERVICE_SURFACE.md`,
`docs/context/16_AUTH_BILLING_AND_ENTITLEMENTS.md`
**Purpose:** a living registry of backend capabilities the frontend depends on but does not
implement. Rule: **never invent missing backend behavior in frontend code — file or update a
request here instead.** Do not create a second overlapping request file.

Status values: `NOT STARTED` · `IN PROGRESS` · `AVAILABLE` · `SUPERSEDED` · `BLOCKED`.

REQ-001 through REQ-010 originated in the Mission 2 frontend prompt pack. REQ-011 through
REQ-015 are specified here as first-class Mission 2 commercial/resource contracts.

---

## SUPERSEDED — anonymous Planner backend session / claim handshake

**Status:** SUPERSEDED (2026-08-17)

Any earlier requirement that public `/planner`:

- create an anonymous backend PlanningRun or session;
- receive `TenantContext` (including a fictional `ANONYMOUS` tenant);
- write GCS/Firestore/BigQuery state;
- later "claim" that anonymous state after Clerk sign-up;

is **SUPERSEDED**. Public `/planner` is deterministic/local-static. It makes no `prem3-api`
call at anonymous runtime. Conversion creates or selects an authenticated MMM Project only
after verified identity **and** a passing `max_active_projects` check. Imported Planner
fields are candidate/unconfirmed until backend provenance confirms them.

If a request below still mentions sessions/auth, that language applies to **authenticated**
`prem3-api` context only — never to anonymous `/planner`.

---

## P0 — before live auth/planning integration

### REQ-001 — Contract schema export

**Status:** IMPLEMENTED — CURRENT CONTRACT FAMILIES (2026-08-17)
**Exporter:** `scripts/export_contracts.py` (`app/tools/schema_export.py`)
**Check:** `python scripts/export_contracts.py --check` or `python scripts/check_contracts.py`
**Artifacts:** `contracts/schema/`

Generated from live Pydantic models. Do not hand-edit the JSON Schema files.

| Artifact | Public roots | Python source |
|---|---|---|
| `response.schema.json` | `StructuredResponse` | `app.response.contracts` |
| `state.schema.json` | `DurableRunState`, `RunStatusEvent`, `Issue`, `Transformation`, `ReadinessReceipt`, `BigQueryPublishReceipt`, `LearningReceipt` | `app.core.contracts` (`RunStage` via `DurableRunState.stage`) |
| `intelligence.schema.json` | `Prem3PreEdaFinding`, `SemanticQuestion`, `GuidedRemediationItem`, `DimensionalStatus`, `DomainView`, `DomainViewDiff` | `app.intelligence.contracts` + `app.domain.intelligence.models` |
| `mel.schema.json` | `ExperienceEpisode`, `ExperienceReflection`, `PromotionReceipt`, `ExperienceApplication`, `HoldoutManifest` | `app.mel.models` |

Mission 2 Project / Dataset / Entitlement / Planning / OpenAPI families join this pipeline only when their authoritative backend models exist.

Not claimed: REQ-002 OpenAPI freeze.

### TenantContext / WorkspaceContext / canonical path foundation

**Status:** IMPLEMENTED — INTERNAL PRIMITIVE (2026-08-17)
**Modules:** `app/core/tenancy.py`, `app/core/resource_paths.py`, `app/core/identifiers.py`,
`app/core/developer_bootstrap.py`

Request-scoped `TenantContext` and `WorkspaceContext` plus fail-closed identifier/path
builders exist. They are **not** public REQ-001 schema roots and are **not** `/v1/me`
payloads. The public Planner still receives no TenantContext.

This is a prerequisite for REQ-003, REQ-011, signed uploads, and repository/tool authority
refactor. It does **not** implement Clerk, Firestore persistence, FastAPI, entitlements, or
OpenAPI.

`MODELREADY_ORGANIZATION_ID` / `MODELREADY_WORKSPACE_ID` remain developer/CLI bootstrap
inputs only (`bind_developer_bootstrap()`). They do not bind `require_tenant()` /
`require_workspace()`.

### Dataset execution authority (server-owned ExecutionContext)

**Status:** IMPLEMENTED — INTERNAL PRIMITIVE (2026-08-17)
**Modules:** `app/core/execution_context.py`, `app/core/legacy_execution.py`,
`app/core/run_repository.py`

Registered `root_agent` tools no longer accept tenant, workspace, Dataset,
package URI, GCS/filesystem path, BigQuery destination, plan, or entitlement
arguments. Evaluation identity comes from bound `ExecutionContext`.
`RunRepository` derives Mission 2 and legacy artifact prefixes from that context
via `app/core/resource_paths.py`. `Settings` no longer carries organization or
workspace authority fields.

Trusted CLI/cloud-proof scripts may still pass a package URI through
`prepare_legacy_dataset_execution`, which is not registered on `root_agent`.
The already-deployed Cloud Run ADK API cannot bind process `ContextVar`s from
an HTTP prompt; historical cloud proof scripts remain a legacy harness until
`prem3-api` binds execution before agent invocation.

Not claimed: REQ-002, REQ-003, REQ-011, REQ-014.

### REQ-002 — OpenAPI freeze

**Status:** NOT STARTED
**One-line description:** OpenAPI freeze.
**Needs specification:** `contracts/openapi.yaml` as the integration contract; which
endpoints are in the initial freeze; process for amending after freeze. Required resource
families are listed in `15_*` §4.

### REQ-003 — Identity `/v1/me` and authenticated context

**Status:** NOT STARTED
**One-line description:** identity `/v1/me` and authenticated context.
**Scope:** authenticated `prem3-api` only. **Does not** apply to public `/planner`.
**Needs specification:** response shape — current subscription/plan, entitlement projection
(`max_active_projects`, active project count), organization/`tenant_id` mapping (internal),
authorized MMM Project list. Tenant is resolved from the verified Clerk credential, never
from the request body, query, or URL.
**SUPERSEDED portion:** any reading that `/v1/me` or a sibling session endpoint should mint
anonymous Planner backend state or a claim handshake.

### REQ-004 — Question schema

**Status:** NOT STARTED
**One-line description:** question schema.
**Needs specification:** `answer_type` enumeration and generated-question-renderer shape for
authenticated acquisition-planning intake. Must support tri-state YES/NO/UNKNOWN.

### REQ-005 — Field provenance

**Status:** NOT STARTED
**One-line description:** field provenance.
**Needs specification:** per-field provenance shape (user-confirmed vs. extracted/registry/
assumed/candidate-from-planner-import).

### REQ-006 — Workflow change

**Status:** NOT STARTED
**One-line description:** workflow change.
**Needs specification:** endpoint(s) for changing an in-progress authenticated planning
workflow path (`POST /v1/planning/runs/{planning_run_id}/change-path`).

## P0 — new commercial model

### REQ-011 — Project/Dataset resource model and endpoints

**Status:** NOT STARTED
**Needs:**

- First-class MMM Project (`workspace_id`) and Dataset (`dataset_id`) resources persisted in
  Firestore. Project creation is **explicit** and capacity-gated; Clerk user/org provisioning
  must not auto-create a paid MMM Project.
- CRUD endpoints per `15_*` §4 (`/v1/workspaces`, `/v1/workspaces/{workspace_id}/datasets`).
- Each Evaluation Run (`run_id`) carries an explicit `dataset_id` foreign key.
- List/detail fields remain contract-backed (name, intended KPI/grain, source count, latest
  evaluation state, latest evaluated timestamp, evaluation count, next action).
- Isolation: tenant from verified credential; `workspace_id` in the URL is a selector that
  must be authorized; unauthorized lookup returns not-found.

### REQ-012 — Public Plan Catalog + entitlement fields

**Status:** NOT STARTED
**Needs:**

- `GET /v1/catalog/plans` (public, no auth required, no secrets) returning per plan:
  `plan_id`, `display_name`, `monthly_price_display`, `billing_interval`,
  `max_active_projects`, `cta_kind`, `stripe_checkout_available`, and feature-copy fields.
- Plans: Planner / Project / Portfolio / Enterprise = 0 / 1 / 10 / 50 active MMM Projects.
- Paid plans include unlimited re-evaluations. Do **not** expose `dataset_runs_per_month`,
  run credits, or a commercial run-balance field.
- `/v1/me` (REQ-003) returns the current entitlement projection from Firestore.
- No dollar amounts or Stripe Price IDs are hardcoded frontend-side.

### REQ-013 — Stripe Checkout/Portal endpoints and subscription projection

**Status:** NOT STARTED
**Needs:**

```text
POST /v1/billing/checkout-session
  body: { plan_id }
  -> { redirect_url }

POST /v1/billing/portal-session
  -> { redirect_url }

POST /v1/webhooks/billing
```

- Checkout Session creation keyed by `plan_id`, not a client-owned Stripe Price ID.
- Stripe is subscription source of truth; PreM3 stores the entitlement/subscription
  projection and webhook idempotency records in Firestore.
- Stripe Customer/Price IDs are mapped attributes, never Firestore document IDs, GCS path
  segments, or BigQuery dataset names.
- A Checkout success redirect is not entitlement proof. `/v1/me` is the source the frontend
  refreshes after Checkout.
- Downgrade policy is server-decided and non-destructive; frontend only presents server
  guidance.

If older notes used `/v1/billing/checkout` or `/v1/billing/portal`, those names alias the
canonical `checkout-session` / `portal-session` paths in `15_*` §4.

### REQ-014 — Dataset lifecycle, evaluation-run history, and dataset-to-run linkage

**Status:** NOT STARTED
**Needs:**

- Evaluation-run history scoped to a `dataset_id` (unlimited commercially; operational
  pagination is not a quota).
- Signed upload URL / upload contract; frontend never constructs `gs://` or holds cloud
  credentials.
- Run creation returns a run ID / long-operation state consumable by Mission 1 run-workspace
  components.
- Comparable-fields contract for run-to-run comparison; frontend must not infer readiness
  deltas.

### REQ-015 — Deterministic Planner manifest / registry snapshot export

**Status:** NOT STARTED
**Needs:**

- A generated, versioned artifact (proposed:
  `contracts/planner-manifest.schema.json` and
  `frontend/src/generated/planner-manifest.v1.json`) containing approved BUNDLED/PROMOTED
  provider metadata and deterministic planning rules.
- Regenerable from canonical source with CI drift verification.
- **Not** a runtime API. Ships with the frontend so anonymous `/planner` makes zero backend
  calls and never includes tenant overlay data.
- Tenant OVERLAY registry metadata lives in Firestore and is available only inside
  authenticated project workflows.

## P1 — execution workspace

### REQ-007 — Taskmaster read model

**Status:** NOT STARTED
**One-line description:** Taskmaster read model.
**Needs specification:** per-stage `status`, `objective`, `known`, `missing`, `owner`,
`evidence`, `artifacts`, `current_task`. Frontend reconstructs Taskmaster state from this
read model only.

### REQ-009 — Registry search/gaps

**Status:** NOT STARTED
**One-line description:** registry search/gaps.
**Needs specification:** authenticated provider search API and candidate-disambiguation
shape. Public Planner must not call this.

### REQ-010 — Planning response types

**Status:** NOT STARTED
**One-line description:** planning response types.
**Needs specification:** authenticated `PlanningReportV1` family (`MMM_PROJECT_BLUEPRINT`,
`MMM_ACQUISITION_PLAN`, `MMM_DATA_GAP_PLAN`). Distinct from the free Planner's local brief.
Exact schema belongs in future `17_PLANNING_ENGINE_AND_REPORT_CONTRACT.md`.
**Readiness:** Planner brief ≠ `COLLECTION_READY` ≠ `MODEL_READY`. Frontend computes none
of them.

## P1 — collaboration

### REQ-008 — Revocable plan share token

**Status:** NOT STARTED
**One-line description:** revocable plan share token.
**Needs specification:** backend-issued, revocable read-only share token for authenticated
plan detail pages. Optional until specified.
