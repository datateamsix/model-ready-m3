# Authentication, Billing, and Entitlements

**Status:** Mission 2 canonical auth/billing constraint — revised 2026-08-17
**Applies to:** Clerk identity, MMM Project access/capacity, monthly subscriptions, Stripe, entitlements, Planner conversion, paid execution
**Depends on:** `14_MULTITENANCY_AND_IDENTITY_BOUNDARY.md`, `15_FRONTEND_INTEGRATION_AND_SERVICE_SURFACE.md`
**Providers:** Clerk (identity), Stripe (billing)
**Architecture reconciliation:** Mission 2 frontend productization plan, 2026-08-17

> Provider API surfaces change. Verify webhook event names, SDK method signatures, and session-token claims against current Clerk and Stripe documentation at implementation time rather than relying on this document or on model memory.

---

## 1. The one idea that determines everything else

**Authentication, entitlement, and billing are three separate layers. Mission 2 now requires all three, but they remain independent contracts.**

```text
Clerk           → who is this person, and which tenant are they acting in?
Entitlements    → what is this tenant allowed to do right now?
Stripe          → why does the tenant have that entitlement, and what monthly plan is active?
```

The public **PreM3 Planner** sits outside paid entitlement enforcement: it is a deterministic anonymous lead-generation tool and creates no paid MMM Project. Paid execution begins when an authenticated tenant creates/uses an MMM Project.

Build the entitlement layer before wiring Stripe-specific decisions through product code. Every gated operation calls `require_entitlement(...)` / project-capacity enforcement. Stripe changes the entitlement projection; it does not become the authorization library.

## 2. Identity: Clerk

### 2.1 Mapping to the PreM3 tenancy model

| PreM3 concept | Clerk concept |
|---|---|
| `user_id` | Clerk User ID |
| `tenant_id` | PreM3-issued, mapped from a Clerk Organization |
| personal tenant | Clerk Organization may be auto-created on sign-up as an **identity** onboarding policy. That creates a PreM3 `tenant_id` mapping only. It does **not** create an MMM Project. |
| `workspace_id` / MMM Project | **PreM3-owned. Clerk has no equivalent.** Project creation is explicit and capacity-gated. |
| `dataset_id` / Dataset | **PreM3-owned. Clerk has no equivalent.** |
| roles | Clerk Organization roles, projected onto PreM3 roles |

Two rules follow:

- **Enable Clerk Organizations from the start**, including solo-user support. If personal organizations are auto-created, treat that as an identity onboarding policy rather than an isolation shortcut; PreM3 still issues its own `tenant_id`.
- **Account provisioning must not auto-create a paid MMM Project.** Clerk user/org webhooks may create the tenant mapping and a Planner-tier entitlement (`max_active_projects = 0`). Creating a `workspace_id` requires an explicit user action plus a passing project-capacity check.
- **PreM3 issues its own `tenant_id`.** Do not use the Clerk org ID as a Firestore document ID, storage-path segment, or BigQuery-dataset component. Provider IDs change format, providers get replaced, and those identifiers end up in immutable object paths and dataset names. Keep a mapping table.

### 2.2 Verification

- The frontend obtains a Clerk session token. `prem3-api` verifies it server-side against Clerk's JWKS, with cached keys and clock-skew tolerance.
- Verified claims produce a `TenantContext` (per `14_*` §3). **Tenant is derived from the verified token and the mapping table — never from a request body, query parameter, or path segment.**
- Membership is re-checked per request against the mapping table, not trusted from a possibly-stale token claim, for any operation that reads or writes tenant data.
- Public `/planner` never hits `prem3-api` and never receives `TenantContext`. Do not bind an `ANONYMOUS` tenant context, default workspace, or backend session merely because a visitor opened the Planner.
- Other unauthenticated requests, if any, also receive **no** `TenantContext`. `require_tenant()` fails closed. There is no anonymous backend planning session.

### 2.3 Clerk webhooks

Endpoint: `POST /v1/webhooks/identity`, signature-verified, idempotent by event ID.

| Event | PreM3 action |
|---|---|
| user created | ensure Clerk user mapping; if a personal org is created, issue `tenant_id` and Planner-tier entitlement (`max_active_projects = 0`). **Do not create an MMM Project.** |
| user deleted | enqueue tenant-deletion job (`14_*` §8) if sole member |
| organization created | issue `tenant_id`, create mapping, provision Planner/free entitlement with **zero** active-project capacity. **Do not auto-create a paid MMM Project.** |
| organization deleted | enqueue tenant deletion |
| membership created/deleted | update membership projection |

Webhooks are advisory and may arrive late, out of order, or twice. Treat every handler as idempotent and never make a security decision that depends on a webhook having already been processed — re-check membership at request time instead.

### 2.4 Where the account and paid-project gates sit

| Branch | Gate |
|---|---|
| Public `/planner` | No auth, no paid entitlement, no GCP/PreM3 runtime execution. Show the useful result before registration. |
| Save Planner result as MMM Project | Auth required; paid project capacity required before creating a new active MMM Project. |
| `ACQUISITION_PLANNING` inside a project | Auth + authorized workspace + paid project entitlement. |
| `DATA_GAP_PLANNING` | Auth + authorized workspace + paid project entitlement; upload additionally requires Dataset/upload entitlement. |
| `DATASET_PREPARATION` | Auth + authorized workspace + Dataset creation/upload entitlement. |
| Evaluation / safe remediation / BQ / official Meridian EDA / Meridian Integration | Paid project + corresponding server-side feature entitlement. |

A signed-out user choosing Getting Organized or Ready to Assess may be routed through Clerk and pricing while preserving intent, but no backend MMM Project, Dataset, PlanningRun, or Evaluation should be created until identity and capacity checks succeed. Sign-up alone is not project creation.

### 2.5 Planner conversion handshake

The old anonymous-session / claim-handshake model is **SUPERSEDED** for the public Planner. `/planner` does not create backend state and does not receive `TenantContext`.

```text
local PlannerBriefV1
      ↓
Clerk sign-up / sign-in
      ↓
verified tenant + membership
      ↓
plan/project-capacity check
      ↓
create/select MMM Project
      ↓
create authenticated Planning Run if requested
      ↓
POST candidate Planner brief import
```

The imported Planner brief is validated against a versioned schema/manifest and stored only as **candidate, unconfirmed** context until the backend question/provenance engine accepts or confirms fields. The client never supplies `tenant_id`, entitlement state, or authoritative project capacity.

Test conversion failures deliberately: stale Planner manifest, abandoned sign-up, auth completed in another tab, no available project slot, checkout completed but projection delayed, user already belongs to multiple organizations.

## 3. Entitlements

### 3.1 Contract

```python
class Feature(StrEnum):
    PROJECT_CREATE = "project_create"
    PLANNING_RUN = "planning_run"
    PLAN_COMPILE = "plan_compile"
    PLAN_EXPORT = "plan_export"
    DATASET_CREATE = "dataset_create"
    DATA_UPLOAD = "data_upload"
    DATASET_ASSESSMENT = "dataset_assessment"
    SAFE_REMEDIATION = "safe_remediation"
    BIGQUERY_PUBLISH = "bigquery_publish"
    OFFICIAL_MERIDIAN_EDA = "official_meridian_eda"
    MERIDIAN_INTEGRATION = "meridian_integration"
    REGISTRY_RESEARCH = "registry_research"
    TEAM_SEATS = "team_seats"


class Entitlement(BaseModel):
    tenant_id: str
    plan_id: str                     # "planner" | "project" | "portfolio" | "enterprise"
    features: set[Feature]
    limits: dict[str, int]           # max_active_projects, seats, upload_bytes, etc.
    status: Literal["ACTIVE", "PAST_DUE", "CANCELED", "TRIALING", "INCOMPLETE"]
    valid_until: datetime | None
    source: Literal["DEFAULT", "BILLING_PROVIDER", "MANUAL_GRANT"]
    snapshot_id: str
```

```python
def require_entitlement(feature: Feature, *, quantity: int = 1) -> None:
    """Fail closed. Resolves tenant from TenantContext, never from an argument."""
```

Commercial capacity is `max_active_projects`, not `dataset_runs_per_month`. A Dataset may have unlimited Evaluation Runs commercially; backend abuse/concurrency/storage/compute controls remain independent.

### 3.2 Rules

- Enforcement is **server-side only**. The frontend may read entitlements from `/v1/me` to hide buttons; that is presentation, not enforcement.
- The agent cannot call `require_entitlement` and cannot pass a tenant, plan, or feature to it. Gating is applied by the tool wrapper around the operation, not by model reasoning. This mirrors the existing rule that agent prose never determines `MODEL_READY`.
- Fail closed. If entitlement resolution errors, deny and surface a typed error — do not default to the permissive plan.
- `entitlement_snapshot_id` is recorded on every run and plan, so you can later explain why an operation was allowed.
- Capacity/limits are enforced at the point of mutation with server-owned state. Active-project capacity must be checked atomically when creating/reactivating a project. Operational request/compute controls are separate from the commercial plan.

### 3.3 Mission 2 monthly packaging

The plan catalog is backend/configuration-owned. Frontend renders it; Stripe Price IDs and dollar amounts are never hardcoded into components.

| Plan | Customer | Active MMM Projects | Evaluation runs | Product access |
|---|---|---:|---|---|
| **Planner** | Prospect / lead | 0 paid slots | N/A | Public deterministic Planner only |
| **Project** | One company / one MMM initiative | 1 | Unlimited | Full paid PreM3 project workflow |
| **Portfolio** | Agency / multi-brand team | Up to 10 | Unlimited | Same core workflow across project portfolio |
| **Enterprise** | Large agency / enterprise | Up to 50 | Unlimited | Larger project capacity; enterprise support/controls may expand later |

Every paid MMM Project may include multiple related Datasets. The plan does not meter `run_id`; “Run another evaluation” should remain available subject to operational protections and subscription status.

Paid project workflow includes, subject to the final plan catalog:

- authenticated acquisition/data-gap planning;
- Dataset creation/upload;
- readiness assessment;
- AUTO_SAFE remediation where allowed;
- BigQuery publish + parity;
- official Meridian EDA;
- **Meridian Integration**;
- evaluation history and unlimited re-evaluations.

Do not invent price amounts in code or documentation. `/v1/catalog/plans` (or the frozen equivalent) supplies display price, billing interval, active-project capacity, feature summary, and checkout eligibility.

### 3.4 Active-project counting

Backend owns what counts as active. If archive/reactivate is implemented, the slot-release semantics must be explicit and tested; frontend must not assume archiving frees capacity. A tenant at capacity receives a stable typed error such as `PROJECT_LIMIT_REACHED`, which the UI maps to upgrade/billing recovery.

## 4. Cost controls are not billing

The public Planner is deliberately designed to avoid variable PreM3/GCP execution cost at anonymous runtime. It should not call Gemini/Vertex AI, ADK, Meridian/EDA, BigQuery, GCS, autonomous registry research, upload endpoints, or the planning compiler service merely to produce the lead-generation result.

It may use a versioned static/generated Planner manifest and local browser state. Analytics must contain only non-sensitive funnel events; do not send business descriptions, provider free text, KPI values, or Planner answers as marketing analytics payloads.

Authenticated paid workflows still need operational safeguards independent of billing:

- per-user/tenant request rate limits;
- concurrency limits for expensive run operations;
- payload and upload size/file-count caps;
- provider research budgets/cache where live research exists;
- outbound research allowlist/circuit breaker;
- quotas or circuit breakers for expensive GCP operations as safety controls, **not commercial run credits**.

A customer with “unlimited re-evaluations” can still be throttled for abuse, concurrency, safety, or platform health. That must never be presented as a purchased run balance.

## 5. Billing: Stripe

### 5.1 Mission 2 requirement

Stripe is now part of Mission 2. The frontend must support monthly subscription conversion for Project / Portfolio / Enterprise while the backend remains the authority for plan catalog, Checkout session creation, subscription projection, and entitlement changes.

Use **Stripe-hosted Checkout and Customer Portal**, not custom card/payment forms.

Required flow:

```text
/pricing or Planner conversion
      ↓
select monthly plan
      ↓
POST backend checkout-session endpoint
      ↓
Stripe Checkout
      ↓
webhook-confirmed subscription projection
      ↓
return to PreM3
      ↓
/v1/me reflects active entitlement/project capacity
```

A Checkout success redirect is not proof of entitlement. The webhook/provider read-back projection is authoritative.

### 5.2 Plan catalog and provider mapping

- One Stripe Customer per PreM3 `tenant_id`.
- Stripe Customer IDs and Price IDs are mapped in Firestore, never used as Firestore document IDs, GCS path segments, or BigQuery dataset names.
- `tenant_id` may be placed in narrowly scoped Stripe metadata for reconciliation; no raw business/Planner content belongs in billing metadata.
- Backend plan configuration maps `plan_id` → monthly Stripe Price ID → `max_active_projects` → features.
- Frontend receives only presentation-safe plan catalog fields and publishable/client-safe Stripe configuration if needed.
- Price amount, currency, interval, and checkout eligibility come from the catalog/backend, not duplicated React constants.

### 5.3 Subscription projection

**Stripe is source of truth for subscriptions; PreM3 stores a Firestore projection used by entitlements.** Webhook processing is signature-verified and idempotent (idempotency records live in Firestore). For material subscription events, refetch the current provider object and project from current state instead of applying unordered event deltas.

Handle at minimum the current Stripe event equivalents for:

- checkout completion;
- subscription created/updated/deleted;
- invoice/payment success;
- invoice/payment failure.

Provider event names/API shapes must be verified against current Stripe documentation at implementation time.

### 5.4 Failure modes

| Failure | Handling |
|---|---|
| Webhook out of order | Refetch current subscription and reproject; do not apply deltas blindly. |
| Duplicate delivery | Firestore processed-event / idempotency record keyed by event ID. |
| Webhook missed | Reconciliation job/provider refresh; do not trust redirect state. |
| Checkout complete, projection delayed | Show pending/retry state; do not prematurely create paid project beyond entitlement. |
| Payment fails | `PAST_DUE` grace/read-only policy; never delete customer data for non-payment. |
| Downgrade below active-project count | Do not delete projects. Define read-only/archive/reduction policy before allowing self-serve downgrade. |
| Org deletion with active subscription | Cancel/resolve billing before tenant deletion workflow. |
| Upgrade mid-cycle | Let Stripe handle proration; PreM3 does not compute it. |

### 5.5 Never

- Gate on a client-supplied plan claim or Stripe redirect query string.
- Store card data or implement a custom card vault.
- Put Stripe IDs in GCS paths or BigQuery dataset names.
- Let frontend enforce project capacity as the security boundary.
- Meter commercial access by Evaluation Run.
- Expose Stripe secret keys or webhook secrets to frontend.

## 6. Security requirements

- All provider webhooks signature-verified before parsing. Reject unverified payloads without processing.
- Secrets (Clerk secret key, Stripe secret key, webhook signing secrets) live in server-side secret storage/runtime injection, never the repository and never `NEXT_PUBLIC_*`.
- Frontend receives only publishable keys.
- Authentication and access events (sign-in, tenant switch, project creation denial, entitlement denial, Planner conversion/import failure) are audit-logged with `tenant_id` when available, `user_id`, and a request ID.
- No raw business content in analytics or billing metadata — this extends the existing rule from the Planning scope §4.5 to the billing surface, where it is easy to violate by attaching a "company description" to a Stripe customer.
- Preserve intended route/Planner conversion state without embedding tenant IDs, entitlements, or sensitive Planner content into URLs.
- If any server session cookie is introduced outside Clerk, it must be httpOnly, Secure, SameSite=Lax, and TTL-bounded.

---

## 7. Test requirements

Identity / isolation:

- `test_unauthenticated_project_create_denied`
- `test_unauthorized_workspace_returns_not_found`
- `test_entitlement_fails_closed`
- `test_agent_cannot_supply_tenant_workspace_dataset_or_feature`

Planner conversion:

- `test_public_planner_requires_no_backend_execution`
- `test_planner_import_is_candidate_unconfirmed`
- `test_stale_planner_manifest_rejected_or_reconciled`

Commercial capacity:

- `test_project_plan_allows_one_active_project`
- `test_portfolio_plan_allows_ten_active_projects`
- `test_enterprise_plan_allows_fifty_active_projects`
- `test_project_limit_enforced_atomically`
- `test_evaluation_run_not_counted_as_commercial_quota`

Stripe:

- `test_webhook_signature_required`
- `test_webhook_idempotent`
- `test_checkout_redirect_not_entitlement_proof`
- `test_subscription_projection_updates_entitlement`
- `test_past_due_degrades_without_data_deletion`
- `test_no_business_content_in_clerk_or_stripe_metadata`

Frontend contract tests should additionally prove that price IDs/secrets are absent from client bundles and project-capacity UI is driven by backend-returned plan/entitlement data.

## 8. Sequencing

| Order | Work | Mission 2 dependency |
|---|---|---|
| 1 | Entitlement contract + plan catalog + `max_active_projects` | pricing, project creation |
| 2 | Clerk verification → tenant/org mapping | all authenticated product routes |
| 3 | MMM Project + Dataset authorization/capacity enforcement | planning, uploads, evaluations |
| 4 | Stripe Checkout + Customer Portal endpoints | paid conversion |
| 5 | Stripe webhook subscription projection → entitlements | trustworthy paid access |
| 6 | Planner conversion/import contract | free-to-paid funnel |
| 7 | Billing settings/read models + recovery states | customer UI completion |
| 8 | Reconciliation/dunning hardening | production launch / GA |

Do not wait for Stripe to implement the entitlement interface, but do not defer Stripe beyond Mission 2: the finished Mission 2 customer journey includes monthly Checkout and Customer Portal integration.

## 9. Non-goals

- Custom in-app billing UI, invoicing, or tax handling.
- Usage-based/metered pricing or per-Evaluation charging.
- Annual pricing in the first Mission 2 cut unless explicitly added to the plan catalog.
- SSO, SAML, SCIM.
- Per-seat provisioning workflows beyond a seat count limit.
- Self-serve plan downgrades that would require destructive project deletion or ambiguous slot reduction; define a non-destructive downgrade policy first.

Record each in `08_DECISION_LOG.md` as deferred, with the trigger that would make it necessary.
