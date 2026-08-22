# Mission 2 backend status

**Paused:** 2026-08-18 after Mission 11 Google connections + import/publish governance.  
**Resume:** `feature/prem3-google-governance`  
**Next:** M2-12 — Governed Source Materialization + Publish Adapters

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
| 10 Dataset upload + Evaluation API | `feature/prem3-dataset-evaluation-api` | `1fd1d48e3c74db3f938d4ec43612835da1cac5ec` |
| 11 Google connections + import/publish governance | `feature/prem3-google-governance` | `8bec3b0156448fcc8afe5ad2d955a6ad11a3bd7b` |

## Ready for frontend (contract-first)

- `contracts/openapi.yaml` — Google OAuth start/callback, Drive/BQ bindings, import/publish receipts
- `contracts/schema/api.schema.json`
- Canonical states: `IMPORT_READY`, `MODEL_READY`, `PUBLISH_READY`
- Canonical Drive depot name `prem3-modeling`; canonical BQ dataset ID `prem3_modeling`

## Cloud notes

- Service `prem3-api` is distinct from historical `modelready-m3`.
- Deployed revision `prem3-api-00003-d4z` does **not** include this mission until a later deploy.
- Live Google OAuth / Drive / BigQuery connection proofs were not run in this mission.

## Pickup reading

`docs/context/17_IMPORT_AND_PUBLISH_GOVERNANCE.md`, `docs/context/PREM3_API.md`, `deployment/prem3_api/README.md`
