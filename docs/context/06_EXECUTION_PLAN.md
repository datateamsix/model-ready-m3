# Execution Plan

## Deadline

August 31, 2026 — 5:00 PM PT

The plan is intentionally demo-first and scope-controlled.

## Phase 0 — War Room lock
**Aug 13–14**

Deliver:
- canonical docs;
- repo;
- architecture;
- demo scenario;
- synthetic data design;
- rule catalog v0;
- deploy skeleton.

Exit:
Everyone/coding agents build against same context.

## Phase 1 — Vertical slice
**Aug 14–17**

Build one complete path:
- upload;
- event;
- Cloud Run;
- ADK orchestration;
- profile;
- detect 3–5 issues;
- make 1–2 transforms;
- validate;
- publish validated artifact to BigQuery;
- verify publish parity;
- generate report.

Exit:
One dataset runs end-to-end in cloud and reaches `MODEL_READY` with a verified BigQuery model artifact.

## Phase 2 — Meridian depth
**Aug 17–21**

Add:
- core Meridian readiness rules;
- provider registry seed;
- Google Ads + Meta + GA4 + commerce mappings;
- normalized representation;
- provenance;
- BigQuery model contract;
- generated Meridian input config/mapping;
- output adapter.

Exit:
Demo dataset reaches believable readiness workflow and is immediately consumable from BigQuery.

## Phase 3 — Experience Loop
**Aug 20–24**

Add:
- episode storage;
- BigQuery analytics;
- evaluator;
- candidate lessons;
- promotion gate;
- Memory Bank retrieval;
- repeated-case demo;
- PreM3 Learning Receipt;
- Experience Applied receipt.

Exit:
Second run uses validated prior experience and visibly proves the changed behavior.

## Phase 4 — Hardening
**Aug 24–27**

Add:
- idempotency;
- retries;
- approval path;
- regression suite;
- ADK evals;
- failure fixtures;
- polished run timeline;
- architecture diagram.

Exit:
Repeated demo runs are reliable.

## Phase 5 — Competition packaging
**Aug 27–29**

Complete:
- README;
- install/deploy;
- screenshots;
- article;
- social post;
- Devpost copy;
- bonus evidence;
- license/disclosures.

Record draft video.

## Phase 6 — Freeze
**Aug 29–30**

- code freeze except critical fixes;
- run full eval suite;
- final cloud deployment;
- final video;
- final repo audit;
- submission dry run.

## Submission day
**Aug 31**

Submit early.

Do not schedule final critical engineering on Aug 31.

## Priority ladder

### P0
- cloud-triggered autonomous M3 run
- Gemini
- ADK
- deterministic validators
- Meridian readiness
- BigQuery model artifact publishing
- publish parity validation
- generated Meridian input contract
- output artifacts
- video-ready UI

### P1
- experiential learning
- PreM3 Learning Receipts
- Memory Bank
- BigQuery agent analytics
- provider registry
- polished reporting
- approvals
- approval-gated Meridian execution path

### P2
- additional providers
- additional Google models
- deeper Unified Schema support
- advanced optimization

### Cut first if schedule slips
- general-purpose chat
- many providers
- full Meridian model execution beyond the approval-gated stretch path
- fancy dashboarding
- multiple unrelated demos

Mission 2 **does not** cut Clerk identity, Stripe Checkout/Customer Portal, entitlements, or `prem3-api`. Those are now canonical in `14_*` / `15_*` / `16_*`. The earlier "billing/auth sophistication" slip item is superseded for the Mission 2 SaaS surface.

## Current milestone language (2026-08-16)

Do not rewrite earlier phases as if PreM3 was always the name.

- **COMPLETE:** synchronous golden pre-modeling workflow (`pre-modeling-golden`)
- **COMPLETE:** PreM3 intelligence context + DOMAIN_VIEW foundation
- **COMPLETE:** MEL Episode Core contracts, evaluation, synthetic promotion machinery
- **COMPLETE:** Stride & Field Dataset B learning-evidence fixture (independent of Music Center Dataset B; not a predetermined lesson)
- **COMPLETE:** Summit & Pine Dataset C sealed holdout (`datasets/summit_and_pine/dataset_c/`), DOMAIN_VIEW v1 baseline, training/reflection firewalls. Sealed before the first real multi-episode promotion attempt. Prerequisite for the `EXPERIENCE_APPLIED` experiment.
- **COMPLETE (local intelligence):** first A+B `EXPERIENCE_LEARNED` / sealed-holdout `EXPERIENCE_APPLIED` cycle (`docs/proof/FIRST_REAL_LEARNING_CYCLE.md`). Bootstrap DOMAIN_VIEW remains v1.0.0. Cloud Taskmaster proof for the same cycle is incomplete.
- **CURRENT:** provider-agnostic coordinator + multi-dataset backend qualification (local PASS; new cloud revision not yet frozen)
- **THEN:** controlled cloud A+B → DOMAIN_VIEW v2 → sealed C EXPERIENCE_APPLIED on the generalized revision
- **THEN:** Ambient Taskmaster
- **THEN:** competition packaging

Do not treat synthetic unit-test promotion as Dataset A → DOMAIN_VIEW v2 cloud proof. Dataset B generation is not `EXPERIENCE_LEARNED`. Dataset C generation is not `EXPERIENCE_APPLIED`.

## Mission 2 architecture baseline (2026-08-17)

Canonical SaaS/tenancy/service/auth documents are now in-repo:

- `docs/context/14_MULTITENANCY_AND_IDENTITY_BOUNDARY.md`
- `docs/context/15_FRONTEND_INTEGRATION_AND_SERVICE_SURFACE.md`
- `docs/context/16_AUTH_BILLING_AND_ENTITLEMENTS.md`
- `docs/contracts/BACKEND_REQUESTS.md`

These supersede earlier anonymous Planner session/claim, default-workspace-on-signup, and run/month commercial-limit assumptions. They do not implement runtime `prem3-api`. Historical Phase 0–4 language above is left as the original hackathon plan.
