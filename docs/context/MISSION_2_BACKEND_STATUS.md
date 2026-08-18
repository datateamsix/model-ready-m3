# Mission 2 backend status

**Paused:** 2026-08-18 after Mission 08 (Stripe billing).  
**Resume:** `feature/prem3-stripe-billing`  
**Next:** Mission 09 — prem3-api Cloud Run packaging + workload identity + Firestore IAM + controlled Clerk → tenant → entitlement → Project SaaS qualification. Keep Dataset execution/ADK invocation separate.

Do not branch from `origin/main`. Do not push or merge unless asked. Do not deploy Cloud Run or grant Firestore IAM in the next slice unless that mission explicitly requires it.

## Completed in this repo

| Mission | Branch | HEAD |
|---|---|---|
| 04 Dataset execution authority | `feature/prem3-execution-authority-refactor` | `36ce58b18f32057aaec501f6617108ad34502084` |
| 05 Firestore control plane | `feature/prem3-firestore-control-plane` | `cbf7cfb122a9fe806ea5016e08bfbfbdee424f1a` |
| 06 prem3-api + frozen OpenAPI | `feature/prem3-api-contract` | `e045b4294e2bba36efa74b132e976e0959e2644b` |
| 07 Clerk tenant authentication | `feature/prem3-clerk-auth` | `c86fe5d85dea9fd32b4060b5ef59e422b37fd8f6` |
| 08 Stripe subscription billing | `feature/prem3-stripe-billing` | (this mission) |

## Ready for frontend (contract-first)

- `contracts/openapi.yaml`
- `contracts/schema/api.schema.json`
- Public catalog / health work locally
- Authenticated routes require Clerk configuration
- Billing Checkout/Portal/webhooks work with Stripe test configuration or the fake provider in tests

## Still fail-closed / not in cloud

- No `prem3-api` Cloud Run
- `m3-runtime` does not have `roles/datastore.user`
- Live Stripe qualification is optional (`LIVE_STRIPE_BILLING_NOT_RUN` unless `scripts/qualify_stripe_billing.py --execute`)

## Pickup reading

`docs/context/PREM3_API.md`, `docs/context/16_AUTH_BILLING_AND_ENTITLEMENTS.md`, `docs/contracts/BACKEND_REQUESTS.md`, `app/service/stripe_gateway.py`, `app/service/billing_events.py`
