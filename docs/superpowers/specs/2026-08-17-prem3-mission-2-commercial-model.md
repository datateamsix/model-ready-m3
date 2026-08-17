# PreM3 Mission 2 — Commercial Model & Product Hierarchy (Source of Truth)

**Recorded:** 2026-08-17
**Status:** canonical — supersedes any earlier informal commercial-model assumptions
**Origin:** `PREM3_MISSION_2_FRONTEND_EXECUTION_PROMPT_PACK.md` (`frontend/docs/mission-2/`), prompt M2-00
**Scope:** frontend and cross-team reference. Backend implementation of the entitlement/billing
enforcement itself is tracked separately in `docs/contracts/BACKEND_REQUESTS.md`.

This document exists because the Mission 2 prompt pack is explicitly a temporary execution
runbook, not permanent architecture documentation. The decisions below are the durable record;
the pack tracks execution status against them.

## 1. Customer-facing object hierarchy

```text
Account / Organization
  └── MMM Project
        └── Dataset
              └── Evaluation Run
```

Internal mapping (unchanged internal identifiers, new customer-facing names):

```text
tenant_id
  └── workspace_id       # customer-facing: MMM Project
        └── dataset_id   # persistent modeling dataset (new)
              └── run_id # one evaluation / re-evaluation
```

- **`workspace_id` remains the internal boundary but is customer-facing "MMM Project."** Route
  segments and contract fields keep the `workspaceId`/`workspace_id` name; only user-facing copy
  says "MMM Project" (see Mission 2 route IA, `M2-01`).
- **`dataset_id` is a new durable identifier** introduced between workspace/project and run. It
  did not exist as a first-class object in Mission 1 — Mission 1 rendered one fixture run
  directly under a workspace with no persistent Dataset concept.
- **One MMM Project may contain multiple related Datasets.**
- **One Dataset may contain unlimited evaluation/re-evaluation runs**, all linked to that same
  persistent Dataset as history, not as independent unrelated runs.

## 2. Commercial packaging

Plans gate by **active MMM Project count**, not by run/evaluation volume:

| Plan | Customer | Included active MMM Projects | Re-evaluations |
|---|---|---:|---|
| Planner | Prospective user / lead | 0 paid project slots | N/A — planning utility only |
| Project | One company / one MMM initiative | 1 | Unlimited |
| Portfolio | Agency / multi-brand team | Up to 10 | Unlimited |
| Enterprise | Large agency / enterprise | Up to 50 | Unlimited |

- **The commercial gate is `max_active_projects`, not `dataset_runs_per_month`.**
  `dataset_runs_per_month` (or any run-volume metering) is explicitly **removed** as a commercial
  entitlement. Backend abuse/rate/compute protections on run volume still apply, but as
  infrastructure protection, not a billed/metered product dimension.
- **"Unlimited re-evaluations"** means commercial plans do not meter or charge by `run_id`. The
  UI must never present a run balance, run quota, or "runs remaining" counter for a paid plan.
- Pricing values and Stripe Price IDs are **never hardcoded** in frontend components. They come
  from a backend-supplied plan catalog (`REQ-012`) so real monthly prices can change without a
  frontend code change.
- Stripe is the source of truth for subscription state; PreM3's backend stores and serves an
  **entitlement projection** derived from Stripe (via webhook), not the frontend re-deriving
  entitlement from raw Stripe objects.

## 3. Free tier: the PreM3 Planner

The public **PreM3 Planner** (`/planner`) is the lead-generation product, distinct from the
authenticated, backend-powered acquisition-planning workflow (`M2-10`).

- Zero paid MMM Project slots.
- **No GCP/PreM3 runtime execution at anonymous runtime** — no Gemini/Vertex AI, ADK agents,
  Meridian, Meridian EDA, BigQuery, GCS, `prem3-api` planning execution, file uploads, or
  autonomous registry research while an anonymous visitor is using the Planner.
- Uses only versioned static/generated planning rules and a generated registry snapshot shipped
  with the frontend build (`REQ-015`) — never a hand-maintained provider-capability database
  inside React components.
- Produces a planning brief / acquisition blueprint. **It never declares `COLLECTION_READY`,
  `MODEL_READY`, or any other backend authority state** — those remain exclusively
  backend-computed, evidence-backed states for authenticated, dataset-backed workflows.
- The useful result renders before any registration ask. Conversion CTA is
  **"Save as an MMM Project."**

## 4. Terminology

- **"Meridian Integration"** is the customer-facing term. "Meridian handoff" (Mission 1's
  internal/judge-facing term) is replaced in all customer-facing copy going forward. Internal
  legacy artifact/field names may remain unchanged where renaming would risk contract drift —
  the presentation layer maps labels, not the backend contract.
- **"Projects"** in navigation/UI copy always means MMM Projects (`workspace_id`).
- **"Datasets"** always means the Dataset objects nested under a Project.
- **"Evaluations"** always means runs/re-evaluations against a Dataset.
- `tenant_id` is never exposed in customer-facing copy.

## 5. Billing model

- Monthly recurring subscription pricing only (Mission 2 scope). No usage-based/metered billing,
  no custom invoicing/tax engine — both explicitly deferred beyond Mission 2 per the prompt pack.
- Stripe hosted Checkout and Stripe Customer Portal are the integration surfaces; no custom
  payment form.
- Frontend entitlement checks are presentation-only. The UI may show an Upgrade prompt before a
  blocked action, but the authoritative enforcement (e.g. `max_active_projects`) always happens
  server-side. The frontend must never decide whether an operation is allowed.

## Relationship to the Mission 1 design spec

`docs/superpowers/specs/2026-08-16-prem3-frontend-scaffold-design.md` remains the record of
Mission 1's fixture-driven operations-console scope and stays valid for the surfaces it
describes (truth-preservation rules, the `PreM3DataSource` boundary, the run workspace, brand
tokens). This document does not revise Mission 1 decisions; it establishes the *new* commercial
and hierarchy layer Mission 2 builds on top of Mission 1's foundation.

## Gap flagged, not silently filled

The Mission 2 prompt pack's "Standing rules for every prompt" (rule 3) lists three required
reading files that **do not exist anywhere in this repository as of this commit**:

- `docs/context/14_MULTITENANCY_AND_IDENTITY_BOUNDARY.md`
- `docs/context/15_FRONTEND_INTEGRATION_AND_SERVICE_SURFACE.md`
- `docs/context/16_AUTH_BILLING_AND_ENTITLEMENTS.md`

`docs/context/` currently only goes up to `13_CLOUD_TASKMASTER_EXECUTION_MODEL.md`. Per the
pack's own standing rule 4 ("Repository truth wins over snippets in these prompts. Report
conflicts"), this is flagged here rather than fabricated: this document does not attempt to
invent multitenancy/identity-boundary, frontend-service-surface, or auth/billing/entitlement
backend architecture content that would need to originate from whoever owns that scope
(presumably the backend/service-owner agents referenced in the pack's header). Frontend prompts
that depend on those docs' content (`M2-06` Clerk/BFF, `M2-07` Stripe) should re-check for their
existence before proceeding, and file a request if they still don't exist by then.
