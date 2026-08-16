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
- billing/auth sophistication
- general-purpose chat
- many providers
- full Meridian model execution beyond the approval-gated stretch path
- fancy dashboarding
- multiple unrelated demos

## Current milestone language (2026-08-16)

Do not rewrite earlier phases as if PreM3 was always the name.

- **COMPLETE:** synchronous golden pre-modeling workflow (`pre-modeling-golden`)
- **COMPLETE:** PreM3 intelligence context + DOMAIN_VIEW foundation
- **COMPLETE:** MEL Episode Core contracts, evaluation, synthetic promotion machinery, sealed Dataset C holdout
- **CURRENT:** first real `EXPERIENCE_LEARNED` / `EXPERIENCE_APPLIED` cycle (no forced lesson)
- **THEN:** Ambient Taskmaster
- **THEN:** competition packaging

Do not treat synthetic unit-test promotion as Dataset A → DOMAIN_VIEW v2 cloud proof.
