# PreM3 Mission 2 — Frontend Productization Execution Prompt Pack

**Prepared:** 2026-08-17
**Canonical repo:** `datateamsix/prem3`
**Frontend owner:** Claude Code team
**Backend/service owners:** Cursor / ChatGPT agents in parallel

```text
Mission 2 Status (updated as prompts complete — see repo-relative note below)

M2-00  NOT STARTED
M2-01  NOT STARTED
M2-02  NOT STARTED
M2-03  NOT STARTED
M2-04  NOT STARTED
M2-05  NOT STARTED
M2-06  NOT STARTED
M2-07  NOT STARTED
M2-08  NOT STARTED
M2-09  NOT STARTED
M2-10  NOT STARTED
M2-11  NOT STARTED
M2-12  NOT STARTED
M2-13  NOT STARTED
M2-14  NOT STARTED
M2-15  NOT STARTED
```

This is a temporary execution runbook, not permanent product architecture
documentation. Canonical architectural decisions still belong in the
appropriate permanent source documents (`docs/context/*`,
`docs/contracts/BACKEND_REQUESTS.md`, the Mission 1 frontend design spec,
etc.) — this file just tracks what's been executed against the pack below
and gives handoff continuity between sessions.

**Visual reference (user-specified, applies to every customer-facing
surface in Mission 2):** target Clerk (clerk.com) and Prefect.io-level
visual polish — restrained, confident, functional-first product design.
No gradients, no glassmorphism, no decorative motion, no chat-bubble UI,
no generic feature-card grids or template-SaaS aesthetics. This reinforces
the pack's own standing rule 13 below (colour carries state, not
decoration) rather than replacing it.

## Mission 2 outcome

At the end of Mission 2, PreM3 should be a coherent, polished, commercially structured SaaS product rather than a fixture-only operations console.

The shipped product must include:

- a high-polish public marketing site;
- a dedicated pricing page;
- a public, deterministic **PreM3 Planner** lead-generation tool with no PreM3/GCP runtime calls;
- Clerk authentication and organization-aware identity;
- Stripe monthly subscription flows through hosted Checkout and Customer Portal;
- the commercial packaging model below;
- a customer dashboard organized around MMM Projects;
- first-class Dataset objects inside each MMM Project;
- unlimited re-evaluation runs against project datasets, subject to abuse/rate controls rather than commercial run quotas;
- acquisition planning / getting-organized workflows;
- dataset upload/preparation workflows;
- the Taskmaster execution workspace;
- acquisition-plan detail and project history;
- customer-facing **Meridian Integration** language and surface;
- public fixture demo reliability;
- production-quality responsive, accessible, tested UX.

---

# Mission 2 commercial model — new canonical decision

Customer-facing hierarchy:

```text
Account / Organization
  └── MMM Project
        └── Dataset
              └── Evaluation Run
```

Internal mapping:

```text
tenant_id
  └── workspace_id       # customer-facing: MMM Project
        └── dataset_id   # persistent modeling dataset
              └── run_id # one evaluation / re-evaluation
```

Definitions:

- **MMM Project** — one company, client, brand/market, or coherent MMM program.
- **Dataset** — a durable analytical dataset/model-input configuration inside an MMM Project.
- **Evaluation Run** — one assessment/re-assessment of a Dataset.
- **Unlimited re-evaluations** — commercial plans do not meter or charge by `run_id`. Backend abuse/rate/compute protections still apply.
- Customer-facing language is **Meridian Integration**, not Meridian handoff. Internal legacy artifact names may remain if changing them would add risk.

Monthly packaging:

| Plan | Customer | Included active MMM Projects | Re-evaluations |
|---|---|---:|---|
| Planner | Prospective user / lead | 0 paid project slots | N/A — planning utility only |
| Project | One company / one MMM initiative | 1 | Unlimited |
| Portfolio | Agency / multi-brand team | Up to 10 | Unlimited |
| Enterprise | Large agency / enterprise | Up to 50 | Unlimited |

Do **not** invent dollar amounts. Pricing values and Stripe Price IDs must come from configuration / backend plan catalog. The UI must support real monthly prices once configured without code changes.

The commercial gate is `max_active_projects`, not `dataset_runs_per_month`.

---

# New free-tier decision

The public **PreM3 Planner** is the lead-generation product.

It must not invoke at anonymous runtime:

- Gemini / Vertex AI;
- ADK agents;
- Meridian;
- Meridian EDA;
- BigQuery;
- GCS;
- `prem3-api` planning execution;
- file uploads;
- autonomous registry research.

It may use versioned static/generated planning rules and a generated registry snapshot shipped with the frontend. It must not hand-maintain provider capabilities in React components.

The Planner produces a planning brief / acquisition blueprint. It does **not** declare `COLLECTION_READY`, `MODEL_READY`, or any backend authority state.

Show the useful result before asking for registration. Conversion CTA: save/continue as an MMM Project.

Authenticated PreM3 project workflows remain backend-driven and must use generated contracts / OpenAPI.

---

# Standing rules for every prompt

Before each task:

1. Fetch `origin/main`; do not assume the SHA in this document is current.
2. Start from a clean branch created from current `origin/main`, unless the prompt explicitly continues the Mission 2 integration branch.
3. Read:
   - `AGENTS.md`
   - `frontend/CLAUDE.md`
   - `frontend/README.md`
   - `docs/context/14_MULTITENANCY_AND_IDENTITY_BOUNDARY.md`
   - `docs/context/15_FRONTEND_INTEGRATION_AND_SERVICE_SURFACE.md`
   - `docs/context/16_AUTH_BILLING_AND_ENTITLEMENTS.md`
   - `docs/contracts/BACKEND_REQUESTS.md`
   - Mission 1 frontend design spec.
4. Repository truth wins over snippets in these prompts. Report conflicts.
5. Never invent missing backend behavior in frontend code. Add/update a backend contract request instead.
6. Frontend never computes readiness, severity, authority, `MODEL_READY`, or `COLLECTION_READY`.
7. Browser holds no Google Cloud credentials and never calls GCP services directly.
8. Stripe secret keys and Clerk secret keys are server-only.
9. Every prompt ends green:

```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

10. Keep GitHub frontend CI green.
11. Use Satoshi only through the now-approved/self-hosted repo implementation. Do not substitute or redistribute font files.
12. Brand source of truth remains `brand/brand-assets/tokens/prem3.tokens.json`.
13. Visual principle: **colour carries state, not decoration**. No gradients, glassmorphism, decorative motion, chat bubbles, or generic card-grid SaaS aesthetics. Reference bar: Clerk (clerk.com) and Prefect.io-level polish and restraint.

---

# PROMPT M2-00 — Mission 2 contract and source-of-truth update

## Objective

Before building new UI, update the Mission 2 architecture/context documents so every agent is operating from the newly agreed commercial model.

## Work

Update the appropriate project context/spec files to record these superseding decisions:

1. `workspace_id` remains the internal boundary but is customer-facing **MMM Project**.
2. Introduce durable `dataset_id` between workspace/project and run.
3. One project may contain multiple related datasets.
4. One dataset may contain unlimited evaluation/re-evaluation runs.
5. Commercial plans gate by active MMM Project count: 1 / 10 / 50.
6. Free Planner has zero paid project slots and no GCP execution at anonymous runtime.
7. Remove `dataset_runs_per_month` as a commercial entitlement. Keep backend abuse/rate/compute controls separate.
8. User-facing term becomes **Meridian Integration**.
9. Pricing is monthly recurring subscription pricing.
10. Stripe remains source of truth for subscriptions; PreM3 stores an entitlement projection.
11. The public Planner is distinct from the authenticated backend-powered acquisition-planning workflow.

Update `docs/contracts/BACKEND_REQUESTS.md` with new contract requests if they do not already exist:

- `REQ-011` — first-class Project/Dataset resource model and endpoints;
- `REQ-012` — public Plan Catalog + entitlement fields (`max_active_projects`, plan state, display pricing);
- `REQ-013` — Stripe Checkout/Portal endpoints and subscription projection contract;
- `REQ-014` — Dataset lifecycle, evaluation-run history, and dataset-to-run linkage;
- `REQ-015` — deterministic Planner manifest / registry snapshot export contract.

Do not implement the service layer in this prompt.

## Acceptance

- [ ] No source doc still presents `dataset_runs_per_month` as the intended commercial gate.
- [ ] MMM Project / Dataset / Run hierarchy is documented once and consistently referenced.
- [ ] "Meridian handoff" is replaced in customer-facing guidance with "Meridian Integration."
- [ ] Free Planner runtime boundary is explicit.
- [ ] Backend requests exist for every new frontend dependency.

## Deliverable

Commit only source/context/contract-request changes. Report which prior decisions were superseded.

---

# PROMPT M2-01 — Route namespace and final product IA

## Objective

Migrate Mission 1 routes into the final Mission 2 information architecture before building new pages.

## Target routes

Public marketing:

```text
/
/how-it-works
/pricing
/planner
/start
/sign-in
/sign-up
/privacy
/terms
```

Public demo:

```text
/app/demo/runs/[runId]
```

Authenticated product:

```text
/app
/app/w/[workspaceId]
/app/w/[workspaceId]/plans
/app/w/[workspaceId]/plans/[planningRunId]
/app/w/[workspaceId]/datasets
/app/w/[workspaceId]/datasets/[datasetId]
/app/w/[workspaceId]/datasets/[datasetId]/runs/[runId]
/app/w/[workspaceId]/taskmaster
/app/settings/account
/app/settings/billing
```

Customer-facing copy says **MMM Project** even though route and contract identifiers remain `workspaceId` / `workspace_id`.

## Migration

- `/` Mission 1 console moves to `/app`.
- Legacy `/runs/[runId]` redirects to the public fixture demo path until authenticated dataset routing is available.
- Existing Mission 1 run components are preserved.
- Add typed route builders in `src/lib/routes.ts`; internal links must use them.
- Add route-group layouts for marketing, auth, app.
- Add route-specific loading/error/not-found boundaries.
- Unknown workspace/project selectors fail closed once auth integration lands; do not encode authorization assumptions now.

## Do not build

Marketing content, Clerk, Stripe, Planner behavior, upload behavior, or new backend types.

## Acceptance

- [ ] `/` is free for marketing.
- [ ] Mission 1 console works at `/app`.
- [ ] public demo remains signed-out reachable.
- [ ] Dataset nesting exists in route structure without inventing dataset data.
- [ ] hardcoded internal href strings are eliminated where practical.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-02 — Generated contracts, OpenAPI client, and drift CI

## Objective

Replace hand-maintained backend contract mirrors with generated types and establish the shared service contract before real integration.

## Requirements

- Backend JSON Schema exports live under `contracts/schema/`.
- `contracts/openapi.yaml` is the integration contract.
- Generate TypeScript into `frontend/src/types/generated/`.
- Generated files carry a do-not-edit header.
- Frontend-only presentation types live under `frontend/src/types/ui/`.
- Add scripts:

```text
contracts:generate
contracts:check
api:generate
```

- CI regenerates and fails on drift before normal typecheck.
- One module owns backend enum → presentation labels.
- Add exhaustive enum coverage tests.
- Remove broad `as unknown as` fixture casts where generated-schema validation can replace them.

## New contracts to expect

The generated contract must eventually represent:

- Project/workspace;
- Dataset;
- Evaluation Run;
- Plan Catalog / Entitlements;
- Billing redirect responses;
- Planning responses;
- Taskmaster read model.

If any are missing, file the backend request; do not invent them.

## Acceptance

- [ ] backend contract drift breaks CI.
- [ ] no handwritten duplicate backend enum remains without explicit temporary justification.
- [ ] fixtures are validated against generated shapes.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-03 — Commercial domain and navigation foundation

## Objective

Teach the frontend the **presentation model** for Projects, Datasets, plans, and entitlements without moving enforcement client-side.

## Build

Create reusable presentation surfaces for:

- plan badge / plan name;
- project allowance: `used / max_active_projects`;
- upgrade CTA;
- project state rows;
- dataset summary rows;
- evaluation history rows;
- empty states;
- archived/read-only state if contract supports it.

Navigation vocabulary:

- "Projects" = MMM Projects.
- "Datasets" = datasets within a project.
- "Evaluations" = runs / re-evaluations.
- "Meridian Integration" = customer-facing integration outcome.

Do not expose `tenant_id` in customer copy.

## Entitlement rule

Frontend may present entitlement values returned by `/v1/me`, but must never decide whether the server should allow an operation.

If `max_active_projects` is reached, the UI may show Upgrade before Create Project, but the create endpoint must still enforce the limit.

## Acceptance

- [ ] UI can express Planner / Project / Portfolio / Enterprise without hardcoding authorization logic.
- [ ] "unlimited re-evaluations" is represented as a product promise, not a literal infinite loop or client-side bypass.
- [ ] dataset and run are visibly distinct objects.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-04 — Premium marketing system and landing page

## Objective

Build the production-quality PreM3 marketing shell and homepage. This is the primary first impression and must look like a credible specialist analytics product, not an AI-template SaaS page.

## Product story

The homepage has one job: make the visitor understand why pre-modeling is hard, see proof that PreM3 makes it tractable, and choose a next action.

Primary CTA: **Plan my MMM** → `/planner`
Secondary CTA: **See how it works** → `/how-it-works`

Signed-in header may additionally expose **Open PreM3** → `/app`.

## Homepage structure

1. Hero with concise positioning and a real PreM3 state/evidence visual using existing Mission 1 components/fixtures where possible.
2. The pre-modeling problem: fragmented inputs, incomplete history, schema mismatch, control gaps, uncertainty.
3. **Map. Mend. Model.** — explain the operating flow.
4. Product proof / authority: deterministic checks, Official Meridian EDA separated from PreM3 interpretation, evidence and receipts.
5. Three customer situations: planning, getting organized, ready to assess.
6. Meridian Integration section.
7. Pricing teaser: one project to a portfolio; link to `/pricing`, not a full pricing grid.
8. Final CTA to `/planner` and `/start`.
9. Footer with product, pricing, privacy, terms, sign in.

## `/how-it-works`

Build a deeper product page covering:

- Project → Dataset → Evaluation lifecycle;
- Map / Mend / Validate / Meridian EDA / BigQuery / Meridian Integration;
- what PreM3 decides vs what Meridian officially reports;
- what PreM3 intentionally does not do: autonomous model fit without approval.

## Visual quality bar

- Satoshi display typography from repo implementation.
- Brand tokens only.
- No gradients.
- No decorative cyan; cyan reserved for verified/complete state.
- Strong responsive typography, whitespace, subtle rules and data rows.
- Use real product surfaces instead of stock illustrations.
- Avoid generic feature-card grids and fake logo bars.
- Do not invent testimonials, customer logos, usage metrics, or success percentages.

## Quality

- semantic landmarks;
- full keyboard access;
- reduced-motion respect;
- optimized assets;
- excellent mobile treatment;
- target Lighthouse >=95 Performance and Accessibility on representative marketing pages, without gaming the test.

## Acceptance

- [ ] `/` feels complete without needing the pricing grid.
- [ ] `/how-it-works` tells the detailed product story.
- [ ] all claims are supported by real product behavior.
- [ ] pricing and Planner CTAs route correctly.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-05 — Pricing and packaging page

## Objective

Build `/pricing` around the commercial unit the customer actually buys: **active MMM Projects per month**.

## Plans

Render the plan catalog from the backend/public plan contract when available. Use mock catalog data only behind the existing adapter/mock boundary and label it as fixture data in code.

Canonical plan semantics:

### Planner

- Free.
- Public PreM3 Planner.
- No paid MMM Project slot.
- No dataset processing.
- CTA: **Plan my MMM**.

### Project

- 1 active MMM Project.
- Multiple related datasets inside the project.
- Unlimited re-evaluations.
- Mapping/readiness assessment.
- Safe remediation.
- Official Meridian EDA.
- Model-ready validation.
- BigQuery publish/verification.
- Meridian Integration.
- CTA: **Start one project**.

### Portfolio

- Up to 10 active MMM Projects.
- Same project capabilities.
- Intended for agencies / multi-brand teams.
- Team access per entitlement contract.
- CTA: **Choose Portfolio**.

### Enterprise

- Up to 50 active MMM Projects.
- Same project capabilities plus enterprise support/controls only where supported by contract.
- Do not invent SSO, SLAs, procurement, or custom security features unless implemented.
- CTA may be Checkout or Contact Sales based on plan catalog configuration.

## Page structure

- short pricing hero;
- concise plan comparison;
- "Included in every paid MMM Project" workflow strip;
- precise definition of Project / Dataset / Re-evaluation;
- FAQ addressing project counting, datasets, re-evaluations, cancellation, archived projects, and Meridian Integration;
- CTA back to free Planner.

## Pricing truth

Do not hardcode Stripe Price IDs or dollar amounts into components.

Plan catalog should supply:

```text
plan_id
display_name
monthly_price_display
billing_interval
max_active_projects
cta_kind
stripe_checkout_available
feature copy / entitlement summary
```

Server remains authoritative.

## Acceptance

- [ ] 1 / 10 / 50 project structure is unmistakable.
- [ ] Dataset is not presented as the billing unit.
- [ ] unlimited re-evaluations are clearly explained.
- [ ] no invented enterprise promises.
- [ ] prices can change without component edits.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-06 — Clerk authentication, organizations, BFF, and tenant boundary

## Objective

Add production Clerk authentication and the server-side identity boundary for all authenticated product routes.

## Current-doc requirement

Before coding, verify the installed Next.js version and current official Clerk Next.js App Router guidance. Do not rely on old examples. Follow the current `clerkMiddleware()` / route-protection pattern appropriate to this repository.

## Build

- `<ClerkProvider>` at appropriate app root.
- Clerk middleware/proxy integration using the current SDK convention.
- `/sign-in` and `/sign-up` branded Clerk routes.
- Clerk Organizations enabled for B2B identity context.
- personal/default organization provisioning only through supported backend mapping behavior.
- BFF route under `src/app/api/prem3/[...path]/route.ts` or the repo's agreed equivalent.
- verified server token forwarding to `prem3-api`.
- server-only backend base URL.
- request ID propagation, timeout, typed error passthrough.
- `/v1/me` session resolution.
- workspace/project authorization server-side; unauthorized project selectors return not-found.
- public marketing, `/planner`, `/start`, and `/app/demo/**` remain public.

## New conversion behavior

Because the free Planner is local/static, do not create an anonymous GCP planning session merely to browse or complete Planner.

When a user chooses **Save as an MMM Project** or enters a backend-powered workflow, preserve the Planner result locally through auth, then create/persist the authenticated project only after successful identity resolution and entitlement check.

If a legacy anonymous-session claim endpoint still exists, keep compatibility only where genuinely required; do not make it the default lead-gen path.

## Security

- no token in `localStorage`;
- no Clerk secret in client bundle;
- no backend URL in public client bundle if BFF architecture can avoid it;
- no tenant ID accepted from browser as authority;
- CI secret/bundle scan.

## Acceptance

- [ ] auth works end-to-end.
- [ ] organizations can be switched safely.
- [ ] project authorization is server-side.
- [ ] public Planner works signed out.
- [ ] Planner state survives sign-in when user converts.
- [ ] public demo remains public and mutation-free.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-07 — Stripe monthly subscriptions and billing settings

## Objective

Wire the frontend to real monthly subscriptions without creating a custom payment UI.

This prompt has a backend dependency. The frontend must not implement Stripe secret-key or webhook behavior inside client code.

## Current-doc requirement

Verify current Stripe documentation for:

- fixed-price monthly subscriptions with Checkout;
- Checkout Session creation;
- subscription webhooks;
- Customer Portal session creation.

Use hosted Stripe Checkout and Stripe Customer Portal unless the current architecture documents explicitly supersede that choice.

## Required backend contract

Expect server endpoints similar to:

```text
POST /v1/billing/checkout
  body: { plan_id }
  -> { redirect_url }

POST /v1/billing/portal
  -> { redirect_url }

GET /v1/me
  -> current subscription projection + entitlements
```

Stripe webhook processing belongs to `prem3-api`, not frontend.

If the endpoints do not exist, update `REQ-013` and build against an API mock. Do not simulate a paid subscription by changing client state.

## Frontend work

### Pricing checkout

For paid plan CTA:

1. signed-out user authenticates first;
2. frontend/BFF asks backend to create Checkout Session by `plan_id`;
3. redirect to Stripe-hosted Checkout;
4. return to `/app/settings/billing?checkout=success` or stable equivalent;
5. refresh `/v1/me` until the server-side subscription projection reflects the change or a bounded timeout is reached;
6. never grant access because a success query parameter exists.

### Billing settings

Build `/app/settings/billing` showing backend-returned:

- plan;
- subscription state;
- project allowance;
- active project usage;
- renewal/cancel state where contract provides it;
- Upgrade / Change plan;
- **Manage billing** → backend-created Stripe Customer Portal session.

### Edge cases

Handle:

- Checkout canceled;
- webhook/projection delay;
- payment/subscription not active;
- existing customer starting another checkout;
- plan downgrade that would put active project count above entitlement;
- portal unavailable;
- backend typed errors.

Do not decide downgrade policy client-side. Present server guidance.

## Testing

Mock the PreM3 billing API contract, not Stripe SDK internals.

Assert that:

- no Stripe secret exists in frontend;
- success URL cannot activate features;
- plan CTA uses stable `plan_id`, not client-owned Price ID;
- server entitlement is re-read after Checkout.

## Acceptance

- [ ] paid monthly plan checkout redirects through Stripe.
- [ ] entitlement becomes visible only after backend projection updates.
- [ ] Customer Portal opens through authenticated server endpoint.
- [ ] no custom card form.
- [ ] no Stripe secret or authoritative billing logic in frontend.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-08 — Free PreM3 Planner lead-generation tool

## Objective

Build the public lead-generation product at `/planner`.

This is not a demo. It must produce a genuinely useful MMM planning brief while making **zero PreM3/GCP runtime calls** during anonymous use.

## Positioning

Hero:

**Planning an MMM? Find out what data you'll need before you start collecting it.**

The Planner is a deterministic planning utility, not an AI chat experience.

## Runtime architecture

```text
Browser
  -> versioned Planner manifest
  -> deterministic decision rules
  -> local Planner state
  -> MMM Planning Brief
```

No `prem3-api` call while filling out or generating the free brief.

The manifest should be generated/versioned, not manually scattered across React components. Prefer:

```text
contracts/planner/planner_manifest.json
```

or a generated frontend artifact with CI drift verification against its canonical source.

The manifest may include:

- business/objective question definitions;
- channel categories;
- provider snapshot metadata from the curated registry;
- common field requirements;
- history/grain guidance encoded as planning guidance, not readiness authority;
- recommended collection tasks;
- manifest version / source timestamp.

If a generated provider snapshot does not yet exist, file/update `REQ-015`. Do not hand-type a provider capability database into components.

## Intake

Keep it short enough for lead generation. Suggested topics:

- business model / industry;
- primary business outcome/KPI;
- markets/geographies;
- marketing history length;
- channels in use;
- platforms/providers;
- online/offline outcome sources;
- warehouse / central data location;
- export status;
- promotions/pricing/seasonality availability;
- first-party/CRM availability;
- desired MMM use case.

Use progressive sections, not chat bubbles.

## Output

Show the result before registration.

Sections:

1. **MMM Project Blueprint**
2. **Data Acquisition Map**
3. **Likely source exports** where supported by manifest
4. **Meridian preparation checklist** — wording must be advisory, not readiness certification
5. **Known gaps / unknowns**
6. **Your next actions**
7. **Continue with PreM3** CTA

The output must clearly carry something like:

```text
Planning guidance — not a MODEL_READY or COLLECTION_READY assessment.
```

Never display backend authority labels because this is not backend evidence.

## Conversion

Primary after-result CTA:

**Save as an MMM Project**

- signed out → Clerk sign-up preserving Planner state;
- free Planner account with no paid project slot → route to pricing/checkout after sign-up;
- paid user with an available project slot → create project through authenticated backend, then offer to continue acquisition planning;
- paid user at project limit → show upgrade path.

Secondary:

**Start over**.

Do not hide the useful result behind email capture.

## Local persistence

Use local browser storage only for the anonymous Planner draft/result, versioned and expiration-aware. Store no secret credentials or raw uploaded files.

## Analytics

Track only non-sensitive funnel events:

```text
planner_started
planner_section_completed
planner_result_viewed
planner_save_clicked
planner_signup_started
planner_checkout_started
```

Do not emit business descriptions, provider free text, KPI values, or other business content into analytics.

## Acceptance

- [ ] network test proves no PreM3/GCP runtime request occurs during anonymous planning/result generation.
- [ ] result is useful without registration.
- [ ] result cannot be mistaken for readiness certification.
- [ ] provider metadata is generated/versioned, not component-hardcoded.
- [ ] state survives sign-in conversion.
- [ ] mobile and keyboard UX are excellent.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-09 — `/start` customer-stage chooser and funnel router

## Objective

Build `/start` as the universal triage page connecting marketing, free Planner, and authenticated product workflows.

## Cards

### Planning

**I have not collected the data yet.**
Routes to `/planner`.

No backend session required.

### Getting organized

**I have some data, but not a complete plan or dataset.**
Signed-out/free user: explain that this continues inside an MMM Project, preserve intended path through auth/pricing.
Entitled user: create/select MMM Project and start `DATA_GAP_PLANNING` through the backend contract.

### Ready to assess

**My data is assembled.**
Signed-out/free user: preserve intended path through auth/pricing.
Entitled user: create/select MMM Project and route to Dataset creation/upload.

Cards remain equal visual weight.

## Existing project behavior

If authenticated user already has MMM Projects, allow:

- continue in an existing project;
- create a new project if entitlement permits.

Do not automatically create a project on page load.

## Acceptance

- [ ] Planning is fully useful without auth or backend execution.
- [ ] paid paths honor project entitlement without client-side enforcement.
- [ ] returning users can choose existing project.
- [ ] intended path survives auth/checkout.
- [ ] no orphan backend runs are created just by visiting `/start`.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-10 — Authenticated acquisition planning and getting-organized intake

## Objective

Build the full backend-powered planning workflow inside an entitled MMM Project.

This is different from the free Planner. Here the backend owns question text/order/branching, provenance, registry resolution, and persisted planning state.

## Routes

Use project-scoped planning routes consistent with final IA, for example:

```text
/app/w/[workspaceId]/plans/new
/app/w/[workspaceId]/plans/[planningRunId]
```

Do not create a second public anonymous intake that duplicates `/planner`.

## Build

- generated question renderer from backend `answer_type`;
- tri-state YES / NO / UNKNOWN;
- provider search using registry API;
- candidate disambiguation;
- per-field provenance panel;
- progress returned by backend, never computed from question count unless contract explicitly supplies progress;
- autosave / retry / offline-safe draft behavior where practical;
- change workflow path through backend endpoint;
- typed errors and recoveries;
- project context always visible.

## Understanding panel

Show:

- what PreM3 currently knows;
- source/provenance;
- what remains unknown;
- user-confirmed vs extracted/registry/assumed.

Do not visually imply `COLLECTION_READY` unless backend explicitly returns it.

## Planner import

If a user converted from free Planner, offer to seed candidate answers from the local Planning Brief. They remain **unconfirmed candidate inputs** until backend accepts and records provenance. Do not silently promote local Planner output to backend truth.

## Acceptance

- [ ] no question catalog hardcoded in React.
- [ ] provenance visible and accurate.
- [ ] local Planner import is explicitly candidate/unconfirmed.
- [ ] backend owns branching and progress.
- [ ] typed recovery paths exist.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-11 — Customer dashboard and MMM Project lifecycle

## Objective

Replace the Mission 1-style console entry with a customer dashboard aligned to the subscription model.

## `/app`

Show:

- current plan;
- active MMM Projects usage, e.g. `3 of 10 active projects`;
- recent project activity;
- recent evaluations;
- CTA to create MMM Project;
- CTA to run free Planner if user has no project context;
- upgrade CTA when appropriate.

No dashboard vanity metrics unless backed by contract.

## Create MMM Project

Minimal creation flow:

- project name;
- optional display context only if backend supports it;
- entitlement check performed server-side;
- typed `PROJECT_LIMIT_REACHED` or equivalent error maps to upgrade UI.

Do not ask for technical dataset fields at project creation.

## `/app/w/[workspaceId]`

Project home should answer:

- what is this MMM Project?
- what datasets belong to it?
- what planning artifacts exist?
- what is the latest evaluation state?
- what is the next useful action?

Primary sections:

- Datasets;
- Planning;
- Taskmaster / latest execution;
- Meridian Integration status if contract provides it;
- recent activity/evidence.

## Project limits

Project limit is a subscription concept. If archive/reactivate exists in the backend, present it. Do not invent slot-freeing semantics client-side.

## Acceptance

- [ ] UI's core object is MMM Project, not raw run.
- [ ] project allowance is visible.
- [ ] project creation fails gracefully at plan limit.
- [ ] no tenant IDs shown.
- [ ] project home gives a clear next action without fake progress.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-12 — Dataset management, upload, and unlimited evaluation history

## Objective

Make Dataset a durable first-class object and connect Mission 1 evaluation UI to that hierarchy.

## Dataset list

`/app/w/[workspaceId]/datasets`

For each Dataset show only contract-backed fields such as:

- name;
- intended KPI / grain if available;
- source count if returned;
- latest evaluation state;
- latest evaluated timestamp;
- number of evaluations;
- next action.

## Dataset detail

`/app/w/[workspaceId]/datasets/[datasetId]`

Sections:

- dataset identity/context;
- source inventory;
- upload/connect state;
- latest readiness/evaluation summary;
- evaluation history;
- artifacts;
- **Run another evaluation**.

Unlimited re-evaluations means the UI does not show a commercial run balance.

## Upload

Use backend-issued signed upload URLs / upload contracts only.

Frontend must never:

- construct a `gs://` URI;
- hold a service-account credential;
- write BigQuery directly;
- upload through an unbounded Next.js server body if direct signed upload is the approved architecture.

Show upload progress, retry, cancellation where supported, and typed server validation errors.

## Evaluation creation

Creating an evaluation returns a run ID / long-operation state through the API. Route into the existing run workspace under the Dataset path.

Preserve Mission 1 evidence components and truth rules.

## History

Each run must be visibly linked to the same persistent Dataset. Show comparisons only for contract-supplied comparable fields; do not infer readiness deltas client-side.

## Acceptance

- [ ] Dataset != upload != evaluation run.
- [ ] repeated evaluations appear as history for one Dataset.
- [ ] no run quota UI.
- [ ] uploads never expose GCP credentials/URIs.
- [ ] Mission 1 run detail works in nested Dataset route.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-13 — Taskmaster workspace integration

## Objective

Evolve the Mission 1 run console into the authenticated Taskmaster execution surface without duplicating backend state logic.

## Route

```text
/app/w/[workspaceId]/taskmaster
```

Dataset/run context should be selectable or linked according to the backend read model.

## Read model

Consume the backend Taskmaster contract containing each stage's:

- status;
- objective;
- known;
- missing;
- owner;
- evidence;
- artifacts;
- current task.

The frontend must not derive any of these from RunStage, counts, or raw artifacts.

## Experience

The screen should feel like an operations workbench:

- persistent stage rail/ledger;
- current task emphasized;
- evidence close to state;
- user actions clearly separated from autonomous actions;
- approval-required states obvious;
- Meridian official findings separate;
- Model Ready state uses verified cyan only when backend truth says so.

## Reuse

Reuse Mission 1:

- response renderer;
- finding cards;
- evidence/proof drawer;
- Model Ready gate;
- MEL/reflection/domain view;
- artifact presentation.

Do not rewrite working components for aesthetics alone.

## Acceptance

- [ ] Taskmaster state reconstructs entirely from server read model.
- [ ] no frontend stage inference.
- [ ] approval branches are explicit.
- [ ] public demo remains fixture-backed and stable.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-14 — Acquisition plan detail and Meridian Integration surface

## Objective

Build the durable project artifacts users can act on after planning/evaluation.

## Acquisition plan

`/app/w/[workspaceId]/plans/[planningRunId]`

Render backend plan versions with:

- project objective;
- recommended data sources;
- provider/export requirements;
- fields/metrics to collect;
- history/grain recommendations where backend supports them;
- controls/confounders to consider;
- known gaps;
- assigned/expected owners where contract supports it;
- ordered next actions;
- provenance / authority labels;
- plan version and timestamp.

Support read-only share link only through backend-issued revocable token if `REQ-008` exists.

## Meridian Integration

Create a project/dataset integration surface that communicates what PreM3 has prepared for Meridian.

User-facing terminology: **Meridian Integration**.

May include contract-backed:

- official Meridian EDA report status/link;
- model-ready data location/reference safe for user display;
- BigQuery publish verification;
- Meridian input contract;
- required artifacts;
- integration checks;
- readiness receipt;
- next approved modeling action.

Do not claim PreM3 fit a Meridian model unless a separate approved modeling workflow actually did so.

Do not rename internal backend artifact fields solely for marketing consistency if that risks contract drift; map labels in the presentation layer.

## Acceptance

- [ ] plan is an actionable artifact, not chat transcript.
- [ ] Meridian Integration terminology is consistent.
- [ ] official Meridian vs PreM3 interpretation remains distinct.
- [ ] no unsupported model-fit claim.
- [ ] lint/typecheck/test/build green.

---

# PROMPT M2-15 — Account/settings, trust surfaces, final product polish, and release gate

## Objective

Finish Mission 2 as a coherent product and run a release-quality review across the complete user journey.

## Account/settings

Build only useful settings:

- `/app/settings/account` — identity/account context using Clerk-supported surfaces;
- `/app/settings/billing` — already integrated billing surface;
- organization switcher / basic membership surface if supported by current scope.

Do not build a custom identity-management suite.

## Legal/trust

Ensure public routes exist and are production-presentable:

- `/privacy`
- `/terms`

Do not fabricate compliance certifications.

Add concise security/trust copy where useful based only on implemented boundaries:

- no browser GCP credentials;
- server-side tenant isolation;
- verified evidence / authority separation;
- data not presented as model-ready without backend proof.

## SEO/share

- metadata per marketing route;
- canonical titles/descriptions;
- social preview assets using approved brand system;
- sitemap/robots where appropriate;
- no fake review schema or unsupported structured claims.

## End-to-end journeys

Verify at minimum:

### Journey A — anonymous lead

```text
/ -> /planner -> planning brief -> sign up -> pricing/checkout -> project created
```

### Journey B — paid user with data

```text
/start -> Ready to assess -> project -> dataset -> upload -> evaluation -> Taskmaster -> MODEL_READY proof -> Meridian Integration
```

### Journey C — agency/portfolio user

```text
/app -> multiple projects -> project switching -> dataset history -> billing allowance
```

### Journey D — public demo

```text
/ -> public demo -> fixture run detail
```

### Journey E — billing recovery

```text
pricing -> checkout canceled / delayed projection / portal -> correct safe UI
```

## Visual QA

At 390px, tablet, 1280px, and 1440px:

- no overflow;
- no clipped controls;
- no generic placeholder pages;
- consistent shell/navigation;
- spacing/typography hierarchy deliberate;
- cyan only carries verified/complete state;
- empty/loading/error states polished.

## Accessibility/performance

- keyboard-only pass;
- focus visibility;
- accessible names;
- form error association;
- reduced motion;
- no serious browser console warnings;
- representative Lighthouse target >=95 Performance and Accessibility on marketing pages;
- reasonable performance on authenticated app pages without hiding real work.

## Security/contract review

Confirm:

- no client GCP credential;
- no Clerk/Stripe secret in client bundle;
- no tenant-as-client-authority;
- no hardcoded Stripe Price IDs in UI;
- no frontend readiness inference;
- contract drift CI green;
- public demo cannot mutate authenticated data;
- Planner anonymous runtime makes no PreM3/GCP execution call.

## GitHub/release

- run full frontend CI locally;
- inspect GitHub Actions;
- open Mission 2 PR(s) according to repo convention;
- review actual diff and unresolved comments;
- do not merge failing checks;
- produce a Mission 2 release note summarizing shipped routes, workflows, known backend dependencies, and deferred scope.

## Mission 2 definition of done

- [ ] polished marketing site live-ready;
- [ ] `/pricing` reflects monthly Planner / 1 / 10 / 50 packaging;
- [ ] Clerk auth integrated;
- [ ] Stripe Checkout + Customer Portal frontend integration complete against backend contract;
- [ ] PreM3 Planner useful, public, and zero-GCP-execution at anonymous runtime;
- [ ] MMM Project is customer-facing primary object;
- [ ] Dataset is first-class under Project;
- [ ] unlimited re-evaluation history works;
- [ ] project allowance/upgrade UX works;
- [ ] planning/getting-organized workflow works;
- [ ] dataset upload/evaluation workflow works;
- [ ] Taskmaster uses backend read model;
- [ ] acquisition-plan detail works;
- [ ] Meridian Integration surface works;
- [ ] public demo preserved;
- [ ] contract drift, secret checks, lint, typecheck, tests, and build all green.

---

# Parallel backend dependency checklist

Frontend Mission 2 can proceed with mocks, but it cannot truthfully claim full integration until the backend provides these contracts.

## P0 — before live auth/planning integration

- REQ-001 contract schema export.
- REQ-002 OpenAPI freeze.
- REQ-003 identity `/v1/me` and authenticated context.
- REQ-004 question schema.
- REQ-005 field provenance.
- REQ-006 workflow change.

## P0 — new commercial model

- REQ-011 Project/Dataset resources.
- REQ-012 Plan Catalog + `max_active_projects` entitlement.
- REQ-013 Stripe Checkout/Portal + webhook-backed subscription projection.
- REQ-014 Dataset/evaluation linkage and history.
- REQ-015 generated deterministic Planner manifest / public registry snapshot.

## P1 — execution workspace

- REQ-007 Taskmaster read model.
- REQ-009 registry search/gaps.
- REQ-010 planning response types.

## P1 — collaboration

- REQ-008 revocable plan share token.

---

# Recommended execution order

```text
M2-00  Source-of-truth update
  ↓
M2-01  Routes / final IA
  ↓
M2-02  Generated contracts + OpenAPI
  ↓
M2-03  Commercial presentation foundation
  ├───────────────┐
  ↓               ↓
M2-04 Marketing   M2-06 Clerk/BFF
  ↓               ↓
M2-05 Pricing     M2-07 Stripe
  ↓               ↓
M2-08 Free Planner
  ↓
M2-09 /start
  ↓
M2-10 Full planning intake
  ↓
M2-11 Customer dashboard / Projects
  ↓
M2-12 Datasets / uploads / evaluations
  ↓
M2-13 Taskmaster
  ↓
M2-14 Plans + Meridian Integration
  ↓
M2-15 Final polish / E2E / release
```

M2-04 and M2-06 can proceed in parallel after the route/contract/commercial foundations are stable. M2-05 can be built before live Stripe endpoints by using the generated plan-catalog mock. M2-08 is intentionally runtime-independent of `prem3-api` and can also proceed while backend integration work is underway.

---

# Explicitly deferred beyond Mission 2 unless already implemented

Do not let these expand Mission 2 uncontrollably:

- autonomous Meridian model fitting;
- custom Stripe payment forms;
- usage-based/metered billing;
- custom invoicing/tax engine;
- enterprise SSO unless a real contract exists;
- complex seat/invitation administration;
- registry administration UI;
- autonomous registry curator UI;
- mobile native app;
- full product analytics warehouse;
- arbitrary external data connectors beyond the defined upload/service surface;
- custom SLA/compliance claims.
