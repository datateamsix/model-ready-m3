# prem3-api

**Status:** Mission 09 Cloud Run packaging — 2026-08-18  
**Does not claim:** Dataset Evaluation → ADK bridge, live Clerk cloud identity, or production Stripe charges.

`prem3-api` is the authenticated product HTTP boundary. The public `/planner` does not call it.

## Cloud Run

Service `prem3-api` in `modelready-m3` / `us-central1` runs as
`m3-runtime@modelready-m3.iam.gserviceaccount.com`. It is a distinct service from
historical `modelready-m3` (ADK proof). Packaging lives in `deployment/prem3_api/`.

Cloud Run Invoker IAM is disabled so Clerk and Stripe callbacks can reach the
service. Infrastructure reachability is not product authentication:

- public: `/healthz`, `/readyz`, `/v1/catalog/plans`
- Clerk session: `/v1/me`, workspaces, datasets, Checkout/Portal
- provider signatures: `/v1/webhooks/identity`, `/v1/webhooks/billing`

Cloud runtime (`PREM3_API_RUNTIME=cloud` or Cloud Run `K_SERVICE`) constructs
`FirestoreControlPlaneRepository`, Clerk, and Stripe from deployment
configuration. Local default remains in-memory and fail-closed. `/readyz` reports
adapter configuration and does not call Stripe.

Operator scripts (never pytest/CI):

```text
py -3.13 scripts/provision_prem3_api_cloud.py --execute
py -3.13 scripts/deploy_prem3_api.py --execute
py -3.13 scripts/qualify_prem3_api_cloud.py --execute --write-evidence
```

Evidence is gitignored at `artifacts/deployment/prem3_api_cloud_proof.json`.

## Local run

```text
py -3.13 -m uvicorn app.service.app:app --reload --port 8080
```

Default factory wiring (local):

- `InMemoryControlPlaneRepository` (no Firestore network on import)
- Clerk verifier when `CLERK_SECRET_KEY` is set; otherwise `UnconfiguredIdentityVerifier`
- Stripe Checkout/Portal/webhooks when `STRIPE_SECRET_KEY` is set; otherwise `UnavailableBillingGateway` → `BILLING_PROVIDER_NOT_CONFIGURED`

Cloud factory wiring (`PREM3_API_RUNTIME=cloud` or `K_SERVICE`):

- `FirestoreControlPlaneRepository` against Native `(default)`
- same Clerk/Stripe rules as local, using Secret Manager-injected values
- live Stripe `sk_live_` and Clerk `sk_live_` refused unless explicitly allowed

Public routes work without providers:

- `GET /healthz`
- `GET /readyz`
- `GET /v1/catalog/plans`

There is no insecure `X-Tenant-ID` development shortcut.

## Clerk configuration (server-only)

Placeholders live in `.env.example`. Never `NEXT_PUBLIC_*` for these values.

- `CLERK_SECRET_KEY`
- `CLERK_PUBLISHABLE_KEY` (optional server copy; frontend publishable key is a frontend concern)
- `CLERK_WEBHOOK_SIGNING_SECRET`
- `CLERK_JWT_KEY` (optional PEM for networkless session verification)
- `CLERK_AUTHORIZED_PARTIES` (comma-separated origins for `azp`)
- `CLERK_API_TIMEOUT_SECONDS` (default 5)

## Public vs authenticated

| Route | Auth |
|---|---|
| `GET /healthz` | public |
| `GET /readyz` | public |
| `GET /v1/catalog/plans` | public |
| `GET /v1/me` | Clerk session + org + current membership |
| `GET|POST /v1/workspaces` | authenticated |
| Dataset routes under a workspace | authenticated + workspace/dataset auth |
| `POST /v1/billing/checkout-session` | Clerk session + org + current membership |
| `POST /v1/billing/portal-session` | Clerk session + org + current membership; Stripe customer mapping required |
| `POST /v1/webhooks/identity` | Clerk signature; no user session |
| `POST /v1/webhooks/billing` | Stripe-Signature; no user session |

## Authority

```text
Clerk session token
  → authenticate_request(accepts_token=["session_token"])
  → org_id required
  → Clerk Backend API current membership
  → IdentityProviderOrganizationMapping → PreM3 tenant_id
  → TenantContext
```

A verified Clerk Organization with no mapping is provisioned as a PreM3 tenant with Planner entitlement (`max_active_projects = 0`). No MMM Project and no Stripe customer are created.

If Clerk membership lookup is unavailable, protected routes fail closed (`AUTH_PROVIDER_UNAVAILABLE`). Local membership projections do not override current Clerk truth.

Organization deletion marks the tenant `DISABLED` and blocks access. It does not delete workspaces, datasets, GCS, or BigQuery data.

## Identity webhook

`POST /v1/webhooks/identity` verifies Standard Webhooks / Svix headers against the raw body, then claims the event through `ControlPlaneRepository`.

Handled types:

- `organization.created`
- `organization.deleted`
- `organizationMembership.created`
- `organizationMembership.updated`
- `organizationMembership.deleted`

Unknown verified events are acknowledged and ignored. Out-of-order membership events for an unmapped organization are ignored (no guessed tenant). Request-time provisioning or a later `organization.created` heals the mapping.

## Generated contracts

```text
python scripts/export_contracts.py
python scripts/export_openapi.py

python scripts/export_contracts.py --check
python scripts/export_openapi.py --check
```

Frontend handoff artifacts (do not hand-edit):

- `contracts/openapi.yaml`
- `contracts/schema/api.schema.json`
- existing `contracts/schema/*.json`

## Billing

Stripe is the subscription source of truth. PreM3 stores a `SubscriptionProjection` and an immutable `EntitlementSnapshot`. Only the snapshot authorizes product capability.

Server-only configuration (placeholders in `.env.example`):

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_PROJECT` / `STRIPE_PRICE_PORTFOLIO` / `STRIPE_PRICE_ENTERPRISE`
- optional catalog presentation amounts/display strings
- optional `STRIPE_PORTAL_CONFIGURATION_ID`
- `PREM3_FRONTEND_ORIGIN` for Checkout/Portal redirects
- `WEBHOOK_CLAIM_LEASE_SECONDS` (default 120)

Pinned SDK: `stripe==15.5.0`. `StripeClient` uses the SDK default API version `2026-07-29.dahlia` (not a separately selected preview).

```text
POST /v1/billing/checkout-session
  plan_id + optional relative return_path
  optional Idempotency-Key
  → Stripe-hosted Checkout URL

POST /v1/billing/portal-session
  optional relative return_path
  → Stripe-hosted Customer Portal URL

POST /v1/webhooks/billing
  raw body + Stripe-Signature
  → claim → retrieve current Subscription → project entitlement
```

Checkout Session creation and the success redirect do **not** write `EntitlementSnapshot`. `/v1/me` reads the Firestore/control-plane snapshot only; it does not call Stripe.

Portal access requires authentication and a Stripe customer mapping. It does not require `ACTIVE` entitlement.

Handled webhook types: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`. Unknown verified events are acknowledged as ignored.

Optional live test-mode proof: `py -3.13 scripts/qualify_stripe_billing.py --execute` (refuses `sk_live_`).
