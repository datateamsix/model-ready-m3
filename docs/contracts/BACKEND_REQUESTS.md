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

**Status:** NOT STARTED
**One-line description (from the prompt pack):** contract schema export.
**Needs specification:** which backend models get exported, export format (JSON Schema per
`M2-02`'s `contracts/schema/` requirement), generation trigger, versioning scheme.

### REQ-002 — OpenAPI freeze

**Status:** NOT STARTED
**One-line description (from the prompt pack):** OpenAPI freeze.
**Needs specification:** `contracts/openapi.yaml` as the integration contract per `M2-02`;
which endpoints are in scope for the initial freeze; process for amending after freeze.

### REQ-003 — Identity `/v1/me` and authenticated context

**Status:** NOT STARTED
**One-line description (from the prompt pack):** identity `/v1/me` and authenticated context.
**Needs specification:** response shape — must include current subscription/plan, entitlement
projection (`max_active_projects`, active project count), organization context. Consumed by
`M2-06` (Clerk/BFF), `M2-07` (Stripe billing settings), `M2-11` (dashboard).
**M2-06 status (2026-08-17):** the frontend side of this boundary is built and waiting —
`src/app/api/prem3/[...path]/route.ts` resolves the caller's Clerk session server-side, forwards
a verified token, and propagates a request ID, but returns a typed `503
PREM3_API_NOT_CONFIGURED` because `PREM3_API_BASE_URL` has nowhere real to point yet. Real
server-side project authorization (M2-06's "unauthorized project selectors return not-found"
acceptance item) is blocked on this endpoint existing, not on any frontend work.

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

**Status:** NOT STARTED
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
- **M2-09 addition (2026-08-17):** this request's original text specified Dataset CRUD in detail
  but left Project (`workspace_id`) list/create endpoints implicit. `/start`'s "continue an
  existing project or create a new one" flow and `M2-11`'s dashboard both need this explicitly,
  so recording the assumed shape here rather than inventing it in frontend code:

  ```text
  GET /v1/projects
    -> ProjectSummary[]   # workspace_id, name, status, dataset_count, latest_activity

  POST /v1/projects
    body: { name }
    -> ProjectSummary     # entitlement (max_active_projects) enforced server-side;
                          # typed PROJECT_LIMIT_REACHED (or equivalent) on rejection
  ```

  `/start`'s frontend is wired against this exact shape via `src/lib/adapters/
  api-projects-source.ts` and fails loudly with the same typed 503
  `PREM3_API_NOT_CONFIGURED` pattern as `ApiBillingSource` until it's real.
**Consumed by:** `M2-09`, `M2-11`, `M2-12`, `M2-13`, `M2-14`.

### REQ-012 — Public Plan Catalog + entitlement fields

**Status:** NOT STARTED
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

**Status:** NOT STARTED
**Filed by:** `M2-00`
**Needs:**

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

**Status:** NOT STARTED
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

## P1 — execution workspace

### REQ-007 — Taskmaster read model

**Status:** NOT STARTED
**One-line description (from the prompt pack):** Taskmaster read model.
**Needs specification:** per-stage `status`, `objective`, `known`, `missing`, `owner`,
`evidence`, `artifacts`, `current_task` fields. The frontend must reconstruct Taskmaster state
entirely from this read model — never derive it from `RunStage`, counts, or raw artifacts.
Consumed by `M2-13`.

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

## P1 — collaboration

### REQ-008 — Revocable plan share token

**Status:** NOT STARTED
**One-line description (from the prompt pack):** revocable plan share token.
**Needs specification:** backend-issued, revocable read-only share token for acquisition plan
detail pages (`M2-14`). Optional — `M2-14` only builds this if REQ-008 exists.
