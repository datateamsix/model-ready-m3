# prem3-api

**Status:** Mission 07 Clerk identity — 2026-08-17  
**Does not claim:** live Stripe, Cloud Run deployment, or SaaS isolation proof against production Clerk.

`prem3-api` is the authenticated product HTTP boundary. The public `/planner` does not call it.

## Local run

```text
py -3.13 -m uvicorn app.service.app:app --reload --port 8080
```

Default factory wiring:

- `InMemoryControlPlaneRepository` (no Firestore network on import)
- Clerk verifier when `CLERK_SECRET_KEY` is set; otherwise `UnconfiguredIdentityVerifier`
- `UnavailableBillingGateway` → `BILLING_PROVIDER_NOT_CONFIGURED`

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
| `POST /v1/billing/checkout-session` | authenticated, then billing fail-closed |
| `POST /v1/billing/portal-session` | authenticated, then billing fail-closed |
| `POST /v1/webhooks/identity` | Clerk signature; no user session |
| `POST /v1/webhooks/billing` | internal callback; Stripe still fail-closed |

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

Stripe remains unconfigured. Authenticated checkout/portal return `BILLING_PROVIDER_NOT_CONFIGURED`.
