# First real learning scorecard

Machine companion: `experience/first_learning_status.json`.
Cloud companion: `experience/cloud_learning/cloud_learning_status.json`.

Local intelligence cycle: proven. Cloud Taskmaster cycle on frozen `modelready-m3-00013-c4s`: **EXPERIENCE_APPLIED**. See `docs/proof/CLOUD_FIRST_LEARNING_CYCLE.md`.

Bootstrap `current/domain_view.json` remains v1.0.0 by design.

## CORE CLOUD PRE-MODELING

- [x] Dataset A full cloud assignment (`m3cloudc5b11fe79553` golden; `m3cloud653724094004` generalized)
- [x] Dataset A MODEL_READY
- [x] Dataset A BigQuery parity
- [x] Dataset A official Meridian EDA (`google-meridian==1.8.0`, ERROR = 0)
- [x] Dataset B independent cloud assignment (`m3cloud856c4fdede10` Map/Mend; USER_REQUIRED stop)

## INPUT EVIDENCE

- [x] A real episode (`ep-dataset-a-f33ceb95b4671082`, intelligence evaluation)
- [x] A real reflection (`ref-908e52f6cde7a53e`)
- [x] B real episode (`ep-dataset-b-50929e8b3cfa0afb`, intelligence evaluation)
- [x] B real reflection (`ref-ddea35ba10e83190`)
- [x] independent_context_count >= 2
- [x] A real Cloud Run Map/Mend/`MODEL_READY` episode (`ep-m3cloud653724094004-8839ba8855077a04`)
- [ ] B real Cloud Run Map/Mend/`MODEL_READY` episode (B remains USER_REQUIRED)

## HOLDOUT CONTROL

- [x] C sealed before promotion (`prem3-dataset-c-holdout`)
- [x] C v1 baseline before promotion (local intelligence)
- [x] C excluded from learning
- [x] C sealed package fingerprint unchanged (`f1bfaa5b…`)
- [x] C v1 cloud baseline (`dataset-c-v1-cloud-00013` on `modelready-m3-00013-c4s`)

## LEARNING

- [x] candidate derived from A+B only
- [x] candidate novel
- [x] candidate scope explicit (`GLOBAL`)
- [x] candidate authority permitted (`ROUTING_HINT`)
- [x] negative-control conflicts = 0
- [x] routing regression = PASS
- [x] EXPERIENCE_LEARNED emitted locally (`cand-semantic_question_routing-3ebf87fa174b`)
- [x] EXPERIENCE_LEARNED emitted on cloud cycle (`cand-semantic_question_routing-9e0ebb37bed1`)

## DOMAIN_VIEW

- [x] version changed (`1.0.0` → `1.0.1`)
- [x] fingerprint changed
- [x] promoted experiential claims +1
- [x] experiment registry ACTIVE pointer updated
- [ ] bootstrap `current/domain_view.json` replaced (intentionally not; v1 remains the repo default)

## APPLICATION

- [x] C v2 uses same local assignment code path as C v1
- [x] C v2 uses same Dataset C raw-tree fingerprint as C v1
- [x] learned claim retrieved
- [x] applicability matched
- [x] predeclared behavior changed (`modeler-questions` 2 → 1)
- [x] behavior effect matches declaration
- [x] sealed holdout validator PASS
- [x] negative controls PASS
- [x] invariants PASS
- [x] EXPERIENCE_APPLIED emitted locally (`app-4ebdbca331ea9b09`)
- [x] EXPERIENCE_APPLIED emitted on cloud cycle (`app-2bf74f1f98e5c6d7`)
- [x] C v2 uses the same Cloud Run revision as C v1 (`modelready-m3-00013-c4s`)

## CLOUD PROOF

- [ ] BigQuery experience-ledger table readback for this cycle
- [x] GCS DOMAIN_VIEW registry pointer and versioned views verified
- [x] Cloud Run revision frozen (`modelready-m3-00013-c4s`)
- [ ] official Meridian evidence recorded for Dataset C v1/v2

## FULL SUCCESS

- [ ] every required checkbox true (bootstrap replacement and Dataset C official EDA remain out of scope)

Primary local status remains recorded in `experience/first_learning_status.json`.

Primary cloud status: `EXPERIENCE_APPLIED`  
Principal cloud runtime: `modelready-m3-00013-c4s`
