# Mission 2 backend status

**Paused:** 2026-08-18 after Mission 09 (`PREM3_M2_API_CLOUD_RUNTIME_READY`).  
**Resume:** `feature/prem3-api-cloud-runtime` @ `cc3db545270007a471eaebf9142e10f0e5b383b3`  
**Next:** Mission 10 — Dataset Upload + Evaluation resource API.

Do not branch from `origin/main`. Do not push or merge unless asked.

## Completed in this repo

| Mission | Branch | HEAD |
|---|---|---|
| 04 Dataset execution authority | `feature/prem3-execution-authority-refactor` | `36ce58b18f32057aaec501f6617108ad34502084` |
| 05 Firestore control plane | `feature/prem3-firestore-control-plane` | `cbf7cfb122a9fe806ea5016e08bfbfbdee424f1a` |
| 06 prem3-api + frozen OpenAPI | `feature/prem3-api-contract` | `e045b4294e2bba36efa74b132e976e0959e2644b` |
| 07 Clerk tenant authentication | `feature/prem3-clerk-auth` | `c86fe5d85dea9fd32b4060b5ef59e422b37fd8f6` |
| 08 Stripe subscription billing | `feature/prem3-stripe-billing` | `d9461a7c7beb103a6bb56ab87509df5c33a5bdba` |
| 09 prem3-api Cloud Run | `feature/prem3-api-cloud-runtime` | `cc3db545270007a471eaebf9142e10f0e5b383b3` |

## Ready for frontend (contract-first)

- `contracts/openapi.yaml` — public liveness is `GET /health` (not `/healthz`)
- `contracts/schema/api.schema.json`
- Cloud Run `prem3-api` is infrastructure-reachable; product routes still require Clerk or provider signatures

## Cloud notes

- Service `prem3-api` is distinct from historical `modelready-m3`.
- Invoker IAM is disabled so Clerk/Stripe callbacks can reach the service. FastAPI remains the authz boundary.
- Live Clerk cloud identity and live Stripe webhook/Checkout proofs were not run in this revision.

## Pickup reading

`docs/context/PREM3_API.md`, `deployment/prem3_api/README.md`, `docs/context/16_AUTH_BILLING_AND_ENTITLEMENTS.md`
