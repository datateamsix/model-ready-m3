# prem3-api

**Status:** Mission 06 service/contract qualification — 2026-08-17  
**Does not claim:** live Clerk, live Stripe, Cloud Run deployment, or SaaS isolation proof.

`prem3-api` is the authenticated product HTTP boundary. The public `/planner` does not call it.

## Local run

```text
py -3.13 -m uvicorn app.service.app:app --reload --port 8080
```

Default factory wiring:

- `InMemoryControlPlaneRepository` (no Firestore network on import)
- `UnconfiguredIdentityVerifier` → `AUTH_PROVIDER_NOT_CONFIGURED`
- `UnavailableBillingGateway` → `BILLING_PROVIDER_NOT_CONFIGURED`

Public routes work without providers:

- `GET /healthz`
- `GET /readyz`
- `GET /v1/catalog/plans`

There is no insecure `X-Tenant-ID` development shortcut.

## Public vs authenticated

| Route | Auth |
|---|---|
| `GET /healthz` | public |
| `GET /readyz` | public |
| `GET /v1/catalog/plans` | public |
| `GET /v1/me` | authenticated |
| `GET|POST /v1/workspaces` | authenticated |
| `GET /v1/workspaces/{workspace_id}` | authenticated + workspace auth |
| Dataset routes under a workspace | authenticated + workspace/dataset auth |
| `POST /v1/billing/checkout-session` | authenticated |
| `POST /v1/billing/portal-session` | authenticated |
| `POST /v1/webhooks/billing` | internal callback; currently fail-closed |

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

Frontend owns OpenAPI/TS client generation. This mission does not modify frontend TypeScript.

## Provider seams

- **Identity:** `IdentityVerifier` → future Clerk adapter. Default fail-closed.
- **Billing:** `BillingGateway` → future Stripe Checkout/Portal. Default fail-closed. Webhook does not parse or persist unsigned events.

## Readiness

`/readyz` reports `auth_provider` / `billing_provider` as `configured` or `not_configured`. It does not claim `AUTH_READY` or `BILLING_READY` while adapters are unavailable.
