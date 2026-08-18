# Backend Contract Requests

**Owner:** frontend track (Claude Code)
**Consumers:** backend/service-owner agents (Cursor / ChatGPT), per
`PREM3_MISSION_2_FRONTEND_EXECUTION_PROMPT_PACK.md`'s header.
**Purpose:** a living registry of backend capabilities the frontend depends on but does not
implement. Rule: **never invent missing backend behavior in frontend code — file or update a
request here instead.**

Status values: `NOT STARTED` · `IN PROGRESS` · `AVAILABLE` · `BLOCKED`.

This file did not exist before Mission 2's `M2-00` prompt. REQ-001 through REQ-010 below are
carried over verbatim from the Mission 2 prompt pack's own "Parallel backend dependency
checklist" — that section is the only place in this repository that named them prior to this
file's creation. Their one-line descriptions are transcribed, not expanded or invented; anyone
picking one up should treat the one-liner as a starting point requiring real specification, not
a finished contract. REQ-011 through REQ-015 are specified in full here per `M2-00`'s explicit
scope.

---

## P0 — before live auth/planning integration

### REQ-001 — Contract schema export

**Status:** AVAILABLE (backend Mission 06, 2026-08-17)
**One-line description (from the prompt pack):** contract schema export.
`contracts/schema/api.schema.json` exists on the backend's frozen contract commit
(`e045b4294e2bba36efa74b132e976e0959e2644b`, branch referenced as `feature/prem3-api-contract`
in the backend's own handoff note — not visible via `git ls-remote --heads`, but the commit
fetches fine by exact SHA). Not yet pulled into this frontend branch as a tracked dependency;
frontend types in `src/lib/adapters/*` currently hand-mirror the schema rather than importing it
directly (see REQ-002 note on why).

### REQ-002 — OpenAPI freeze

**Status:** AVAILABLE (backend Mission 06, 2026-08-17)
**One-line description (from the prompt pack):** OpenAPI freeze.
`contracts/openapi.yaml` exists on the same frozen commit as REQ-001, 791 lines, real paths for
health/ready/catalog/me/workspaces/datasets/billing. **Frontend integration status (2026-08-17
evening):** read directly and hand-mirrored into TypeScript interfaces inside each adapter
(`api-project-source.ts`, `api-dataset-source.ts`, `api-billing-source.ts`,
`api-plan-catalog-source.ts`) rather than run through a codegen tool — a deliberate time-boxed
choice this session, not a refusal of the backend's "generate a TypeScript client" instruction.
Revisit with `openapi-typescript contracts/openapi.yaml` (or equivalent) once there's time for a
proper generated-client pipeline with CI drift checking, matching `M2-02`'s original intent.
Endpoint paths corrected from earlier guesses: workspaces are `/v1/workspaces` (not
`/v1/projects`), billing is `/v1/billing/checkout-session` / `/v1/billing/portal-session` (not
`/v1/billing/checkout` / `/v1/billing/portal`). Errors are real RFC7807 ProblemDetail
(`application/problem+json`), parsed in `prem3-api-client.ts`.

### REQ-003 — Identity `/v1/me` and authenticated context

**Status:** CONTRACT AVAILABLE, PROVIDER NOT CONFIGURED (backend Mission 06 froze the shape;
Clerk verification against FastAPI is backend Mission 07, explicitly not started)
**One-line description (from the prompt pack):** identity `/v1/me` and authenticated context.
**Real shape (frozen contract):** `MeResponse{user{user_id}, organization{tenant_id,
display_name}, plan{plan_id,status,feature_summary}, project_capacity{active_projects,
max_active_projects,remaining_projects}}` — nested, not the flat shape this frontend's
`BillingSummary` type assumed. No field yet for renewal/cancellation date, billing guidance
copy, or portal availability; `api-billing-source.ts`'s mapping defaults those to `null`/`false`
honestly rather than inventing them. Consumed by `M2-06` (Clerk/BFF), `M2-07` (Stripe billing
settings), `M2-11` (dashboard).
**M2-06 status (2026-08-17):** the frontend side of this boundary is built and waiting —
`src/app/api/prem3/[...path]/route.ts` resolves the caller's Clerk session server-side, forwards
a verified token, and propagates a request ID. Locally running the frozen backend today returns
`AUTH_PROVIDER_NOT_CONFIGURED` for this endpoint (per the backend's own handoff note) — Clerk
verification against FastAPI is backend Mission 07's job, not blocked on any frontend work.

### REQ-004 — Question schema

**Status:** NOT STARTED
**One-line description (from the prompt pack):** question schema.
**Needs specification:** `answer_type` enumeration and generated-question-renderer shape for the
authenticated acquisition-planning intake (`M2-10`). Must support tri-state YES/NO/UNKNOWN.

### REQ-005 — Field provenance

**Status:** NOT STARTED
**One-line description (from the prompt pack):** field provenance.
**Needs specification:** per-field provenance shape (user-confirmed vs. extracted/registry/
assumed) consumed by `M2-10`'s understanding panel.

### REQ-006 — Workflow change

**Status:** NOT STARTED
**One-line description (from the prompt pack):** workflow change.
**Needs specification:** endpoint(s) for changing an in-progress planning workflow path,
consumed by `M2-10`.

## P0 — new commercial model

### REQ-011 — Project/Dataset resource model and endpoints

**Status:** CONTRACT AVAILABLE (backend Mission 06, 2026-08-17), PROVIDER NOT CONFIGURED —
real `DatasetResponse{dataset_id,workspace_id,name,status,created_at,updated_at}` and
`GET/POST /v1/workspaces/{workspace_id}/datasets` now frozen. No KPI/grain/evaluation-count
fields on the wire yet (that detail is still genuinely open) — `api-dataset-source.ts`'s mapping
defaults those to `null`/`0` honestly. Auth provider (Clerk verification) not configured, so
every call returns `AUTH_PROVIDER_NOT_CONFIGURED` against a running backend today.
**Filed by:** `M2-00`
**Needs:**

- First-class `Dataset` resource nested under `workspace_id` (customer-facing MMM Project), with
  its own durable `dataset_id`.
- CRUD endpoints for Dataset (create, list under a project, get detail, archive/deactivate if
  supported).
- Each Evaluation Run (`run_id`) must carry an explicit `dataset_id` foreign key so run history
  can be queried per-Dataset.
- List/detail endpoints must return only contract-backed fields — see `M2-12`'s Dataset list/
  detail field requirements (name, intended KPI/grain, source count, latest evaluation state,
  latest evaluated timestamp, evaluation count, next action).
- **Gap found independently by both `M2-09` and `M2-11` (2026-08-17):** this request's original
  text specified Dataset CRUD in detail but left Project (`workspace_id`) list/create/detail
  endpoints implicit. Two parallel sessions each hit this and filed it — reconciled onto a single
  contract, **REQ-016**, rather than left as two overlapping specs. See REQ-016 below for the
  actual endpoint shape; both `/start` and `/app`'s dashboard are wired against it via the same
  adapter (`src/lib/adapters/project-source.ts` + `api-project-source.ts`).
**Consumed by:** `M2-09`, `M2-11`, `M2-12`, `M2-13`, `M2-14` for Dataset CRUD proper; see `REQ-016`
for Project CRUD.

### REQ-012 — Public Plan Catalog + entitlement fields

**Status:** AVAILABLE (backend Mission 06, 2026-08-17) — `GET /v1/catalog/plans` is real, public
(no auth), and runnable locally today per the backend's own handoff note. New
`ApiPlanCatalogSource` (`src/lib/adapters/api-plan-catalog-source.ts`) implements this, using the
new unauthenticated `callPublicPreM3Api` (added specifically because this endpoint must work
signed-out, unlike everything else this frontend calls). **Not yet wired into `/pricing`**: no
`PREM3_API_BASE_URL` is configured in any environment tonight, so swapping it in for the fixture
would replace a working, complete pricing page with a "not connected yet" empty state — a
deliberate deferral, not an oversight. `amount`/`currency`/`display_price` are all still `null`
on the real backend (no Stripe Price configured), matching the fixture's existing
`monthlyPriceDisplay: null` discipline.
**Filed by:** `M2-00`
**Needs:**

- A plan catalog endpoint (public, no auth required, for `/pricing`) returning per plan:
  `plan_id`, `display_name`, `monthly_price_display`, `billing_interval`, `max_active_projects`,
  `cta_kind`, `stripe_checkout_available`, and feature-copy/entitlement-summary fields.
- `/v1/me` (REQ-003) must return the current entitlement projection: plan, `max_active_projects`,
  active project count, subscription state.
- No dollar amounts or Stripe Price IDs are ever hardcoded frontend-side — this catalog is the
  only source.
**Consumed by:** `M2-05` (pricing page), `M2-03` (commercial presentation foundation), `M2-11`.

### REQ-013 — Stripe Checkout/Portal endpoints and subscription projection

**Status:** IMPLEMENTED (backend Mission 08, 2026-08-18, branch `feature/prem3-stripe-billing`
commit `d9461a7`) — **not yet deployed to Cloud Run** (backend's own words: "do not treat a
Checkout success page as a live paid path until Mission 09 deploys Clerk → tenant → entitlement
end-to-end"), but the contract itself is real and integrable against local/staging today. Real
paths: `POST /v1/billing/checkout-session` (Clerk session, body
`CheckoutSessionRequest{plan_id, return_path?}`, optional `Idempotency-Key` header) /
`POST /v1/billing/portal-session` (Clerk session, body `PortalSessionRequest{return_path?}`).
Both return `BillingSessionResponse{url, expires_at?}`. `return_path` must be a relative path
(e.g. `/app/settings/billing`); backend builds the full redirect from it. `GET /v1/catalog/plans`
(public) can now return real `display_price`/`amount`/`currency`/`checkout_eligible=true` for
Project/Portfolio/Enterprise once the backend has monthly prices configured (Planner stays
`max_active_projects=0`/`checkout_eligible=false` always). `GET /v1/me`'s `MePlan.status` and
`MeProjectCapacity` are the sole source of plan/entitlement truth post-webhook — capacities
remain the fixed 0/1/10/50 tiers, no run credits. Confirmed via `contracts/openapi.yaml` at
commit `d9461a7` directly (`MeResponse`/`PlanCatalogEntry`/`CheckoutSessionRequest`/
`PortalSessionRequest` schemas), not just the backend's recap prose.
**Hard UI rules from the backend's own handoff (2026-08-18), not to be violated:**
- A Checkout-success redirect is never itself proof of paid access — only a refreshed `/v1/me`
  showing the new plan is. If `/v1/me` still shows Planner/pending after return, show a waiting/
  retry state, not a silent revert to the old view.
- Never send `stripe_price_id`, a Stripe Customer ID, or a Stripe Price ID from the frontend.
- Never call Stripe's secret API from the browser (already statically guarded by
  `stripe-boundary.test.ts`).
- Never compute project capacity or entitlement client-side — render only what `/v1/me` and the
  catalog return.
- Portal is the billing *recovery* path — past-due/canceled users with an existing billing
  customer must be able to open it without an `ACTIVE` plan. `/v1/me` still has **no**
  `portalAvailable`-equivalent field (confirmed against the real `MePlan`/`MeOrganization`
  schemas), so the frontend must stop gating the Portal button on a fabricated flag and instead
  always offer it, surfacing the real `BILLING_CUSTOMER_UNAVAILABLE` error honestly if the
  backend rejects the attempt.
- New stable error codes to handle explicitly: `BILLING_PROVIDER_NOT_CONFIGURED`,
  `BILLING_PROVIDER_UNAVAILABLE`, `BILLING_CONFIGURATION_ERROR`, `BILLING_CUSTOMER_UNAVAILABLE`.
**Filed by:** `M2-00`
**Original (superseded) proposed shape, kept for history:**

```text
POST /v1/billing/checkout
  body: { plan_id }
  -> { redirect_url }

POST /v1/billing/portal
  -> { redirect_url }
```

- Checkout Session creation keyed by `plan_id`, not a client-owned Stripe Price ID.
- Stripe webhook processing and subscription-state projection live entirely in `prem3-api` —
  the frontend never handles Stripe secret keys or webhook payloads.
- `/v1/me` (REQ-003) is the single source the frontend polls/refreshes after Checkout to confirm
  the subscription projection updated — no client-side "success" state without a
  server-confirmed projection change.
- Downgrade policy (what happens if a plan change would put active project count above the new
  entitlement) is server-decided; the frontend only presents server guidance.
**Consumed by:** `M2-05`, `M2-07`.

### REQ-014 — Dataset lifecycle, evaluation-run history, and dataset-to-run linkage

**Status:** NOT STARTED
**Filed by:** `M2-00`
**Needs:**

- Evaluation-run history endpoint scoped to a `dataset_id`, returning all runs (unlimited —
  no commercial pagination-as-quota) linked to that Dataset.
- Signed upload URL / upload contract for Dataset source ingestion (frontend must never
  construct a `gs://` URI or hold a service-account credential — see `M2-12`).
- Run creation endpoint returns a run ID / long-operation state consumable by the existing
  Mission 1 run-workspace components.
- Comparable-fields contract for showing run-to-run comparisons (frontend must not infer
  readiness deltas client-side).
**Consumed by:** `M2-12`, `M2-13`.

### REQ-015 — Deterministic Planner manifest / registry snapshot export contract

**Status:** IMPLEMENTED (frontend-bundled artifact, 2026-08-17, `M2-08`)
**Filed by:** `M2-00`
**Needs:**

- A generated, versioned artifact (proposed path: `contracts/planner/planner_manifest.json`)
  containing: business/objective question definitions, channel categories, provider snapshot
  metadata from the curated registry, common field requirements, history/grain planning guidance
  (advisory only, not readiness authority), recommended collection tasks, manifest version and
  source timestamp.
- Must be regenerable from its canonical source with CI drift verification (the frontend must
  never hand-type provider capability data into React components).
- Explicitly **not** a runtime API — this ships as a static/versioned artifact bundled with the
  frontend build so the free Planner (`M2-08`) makes zero backend calls at anonymous runtime.
**Consumed by:** `M2-08`.
**Implementation note:** `frontend/scripts/generate-planner-manifest.mjs` generates
`frontend/src/lib/planner/provider-snapshot.generated.json` from
`app/registry/providers/marketing_advertising_providers.v1.json` (the "curated registry"), with
`npm run planner:manifest:check` as the CI drift guard. Only presentation-safe fields extracted
(`providerId`, `displayName`, `category`, `exportFormats`) — no field-mapping schema, Meridian gap
codes, or quirks notes. Question/channel-category/checklist content is hand-authored planning
logic in `frontend/src/lib/planner/manifest.ts`, layered on top of the generated provider data —
that part was never meant to be backend-generated (it's product copy, not a capability database).

### REQ-016 — MMM Project (workspace) resource model and endpoints

**Status:** CONTRACT AVAILABLE (backend Mission 06, 2026-08-17), PROVIDER NOT CONFIGURED — the
backend independently landed almost exactly this shape while this request was in flight:
`GET/POST /v1/workspaces`, `GET /v1/workspaces/{workspace_id}` (this request's proposed detail
endpoint matched exactly). Real `WorkspaceResponse{workspace_id,name,status,created_at,
updated_at}` has no `dataset_count`/activity/planning/Meridian fields yet — `api-project-source.ts`'s
mapping to `ProjectSummary`/`ProjectDetail` defaults those honestly rather than inventing them.
Archive/reactivate still not in the contract (unresolved, as noted below). Auth provider not
configured, so every call returns `AUTH_PROVIDER_NOT_CONFIGURED` against a running backend today.
**Filed by:** `M2-11`
**Needs:**

REQ-011 specifies Dataset CRUD nested under an assumed-existing `workspace_id`, but no contract
request anywhere covers creating or listing the MMM Project (workspace) itself — a real gap found
independently while building both `M2-09`'s `/start` funnel and `M2-11`'s customer dashboard
(two parallel sessions, same evening; reconciled onto this one contract rather than left as two
overlapping specs — see REQ-011's note above).

```text
GET /v1/projects
  -> { projects: [{ workspace_id, name, status, dataset_count, latest_activity_label }] }

POST /v1/projects
  body: { name }
  -> { workspace_id }
  errors: PROJECT_LIMIT_REACHED (maps to upgrade UI) when active project count is
    already at the plan's max_active_projects

GET /v1/projects/{workspace_id}
  -> { workspace_id, name, status, dataset_count, planning_artifact_count,
       latest_evaluation_state, meridian_integration_status }
```

- Entitlement check (`max_active_projects` vs. current active count) is server-side authority —
  the frontend never enforces the limit itself, only presents the typed `PROJECT_LIMIT_REACHED`
  error as an upgrade CTA.
- Archive/reactivate endpoints if that's the chosen slot-freeing policy (not yet decided anywhere
  — see `docs/context/16_AUTH_BILLING_AND_ENTITLEMENTS.md`'s "Downgrade below active-project
  count" failure mode, which explicitly defers this decision).
- List/detail responses return only presentation-safe fields — no `tenant_id`, no GCS/BigQuery
  identifiers.
**Consumed by:** `M2-09`, `M2-11`, `M2-12`, `M2-13`, `M2-14`.

### REQ-017 — Meridian Integration surface

**Status:** NOT STARTED
**Filed by:** `M2-14`
**Needs:**

The M2-14 prompt asks for a "project/dataset integration surface that communicates what PreM3
has prepared for Meridian" (user-facing term: **Meridian Integration**, never "Meridian model" —
PreM3 must not claim to have fit a Meridian model itself). No contract request anywhere covered
this before now — a real gap, same pattern as `REQ-016`. Recording the assumed contract
`/app/w/[workspaceId]/meridian` is built against, so nothing is invented silently:

```text
GET /v1/workspaces/{workspace_id}/meridian-integration
  -> {
    workspace_id,
    eda_report_status, eda_report_url,        # official Meridian EDA report — status/link only,
                                               # never an embedded PreM3 interpretation of it
    model_ready_data_location_label,          # presentation-safe label, never a raw gs:///BigQuery
                                               # table identifier
    bigquery_publish_verified,                # boolean | null
    required_artifacts: string[],
    integration_checks: [{ label, status }],  # status uses the existing PresentationStatus
                                               # vocabulary, same as StatusBadge elsewhere
    readiness_receipt_label,
    next_approved_modeling_action,
  }
```

- Every field is optional/nullable — a project with no Meridian activity yet returns nulls/empty
  arrays, not a 404, so the frontend can render its honest "not yet available" state per section
  rather than a page-level error.
- No field ever implies PreM3 itself fit or ran a Meridian model — this is a "what's prepared"
  status surface, not a modeling result.
**Consumed by:** `M2-14`.

## P1 — execution workspace

### REQ-007 — Taskmaster read model

**Status:** NOT STARTED
**One-line description (from the prompt pack):** Taskmaster read model.
**Needs specification:** per-stage `status`, `objective`, `known`, `missing`, `owner`,
`evidence`, `artifacts`, `current_task` fields. The frontend must reconstruct Taskmaster state
entirely from this read model — never derive it from `RunStage`, counts, or raw artifacts.
Consumed by `M2-13`.
**M2-13 addition (2026-08-17):** the field list above was a one-liner with no endpoint or exact
shape. Recording the assumed contract `/app/w/[workspaceId]/taskmaster` is built against, so
nothing is invented silently in the frontend:

```text
GET /v1/projects/{workspace_id}/taskmaster
  -> {
    workspace_id, dataset_id, run_id, current_stage_id,
    stages: [{
      stage_id, label, status,             # status: same PresentationStatus vocabulary
                                            # StatusBadge already renders elsewhere
      objective, known: string[], missing: string[],
      owner,                                # same ResponsibleActor vocabulary as
                                            # ResponseAction.owner -- distinguishes
                                            # PREM3 (autonomous) from human owners
      requires_approval, current_task,
      detail: StructuredResponse | null,    # optional full response for this stage --
                                            # when present the frontend renders it with
                                            # the existing ResponsePanel (findings,
                                            # official Meridian, evidence/proof) rather
                                            # than re-deriving a parallel shape
    }],
    model_ready: { title, summary, status, gate: ModelReadyGateEvidence } | null,
  }
```

Reuses existing hand-mirrored contract types (`StructuredResponse`, `ModelReadyGateEvidence`,
`PresentationStatus`, `ResponsibleActor`) rather than inventing a parallel vocabulary, so once
this is real only `src/lib/adapters/api-taskmaster-source.ts` needs to change. Frontend is wired
against this exact shape and fails loudly with the typed 503 `PREM3_API_NOT_CONFIGURED` pattern
until it's real.

### REQ-009 — Registry search/gaps

**Status:** NOT STARTED
**One-line description (from the prompt pack):** registry search/gaps.
**Needs specification:** provider search API and candidate-disambiguation shape for the
authenticated planning intake's provider search (`M2-10`).

### REQ-010 — Planning response types

**Status:** NOT STARTED
**One-line description (from the prompt pack):** planning response types.
**Needs specification:** response contract for the authenticated acquisition-planning workflow,
distinct from the free Planner's local-only output. Consumed by `M2-10`, `M2-14`.
**M2-14 addition (2026-08-18):** the one-liner above has no endpoint or exact shape for the plan
*detail* page specifically (`/app/w/[workspaceId]/plans/[planningRunId]`, distinct from `M2-10`'s
list/intake, which stays out of scope). Recording the assumed contract so nothing is invented
silently:

```text
GET /v1/workspaces/{workspace_id}/plans/{planning_run_id}
  -> {
    planning_run_id, workspace_id, objective,
    recommended_sources: string[], provider_export_requirements: string[],
    fields_to_collect: string[], history_grain_guidance,
    controls_confounders: string[], known_gaps: string[],
    owner_label,                    # same ResponsibleActor-style vocabulary as Taskmaster
    next_actions: string[],
    provenance_label, plan_version, generated_at,
  }
```

There is no way to reach this page with a real `planning_run_id` until `M2-10`'s intake exists
either way — the frontend (`src/lib/adapters/api-plan-source.ts`) is wired against this exact
assumption and fails loudly with the typed 503 `PREM3_API_NOT_CONFIGURED` pattern until both
exist. Read-only share links (`REQ-008`) are optional per the prompt and not built — `REQ-008` is
also `NOT STARTED`.

## P1 — collaboration

### REQ-008 — Revocable plan share token

**Status:** NOT STARTED
**One-line description (from the prompt pack):** revocable plan share token.
**Needs specification:** backend-issued, revocable read-only share token for acquisition plan
detail pages (`M2-14`). Optional — `M2-14` only builds this if REQ-008 exists.
