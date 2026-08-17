# First real learning scorecard

Machine companion: `experience/first_learning_status.json`.

FULL SUCCESS requires every required item true. This cycle is **not** full success because cloud learning proof is incomplete.

Core Dataset A cloud pre-modeling on revision `modelready-m3-00012-8xq` is separately **READY**. See `docs/proof/CLOUD_PREMODELING_GOLDEN_RUN.md`.

## CORE CLOUD PRE-MODELING

- [x] Dataset A full cloud assignment (`m3cloudc5b11fe79553`)
- [x] Dataset A MODEL_READY
- [x] Dataset A BigQuery parity
- [x] Dataset A official Meridian EDA (`google-meridian==1.8.0`, ERROR = 0)
- [x] Dataset B independent cloud assignment (initialize fail-closed; Map/Mend not generalized)

## INPUT EVIDENCE

- [x] A real episode (`ep-dataset-a-f33ceb95b4671082`, intelligence evaluation)
- [x] A real reflection (`ref-908e52f6cde7a53e`)
- [x] B real episode (`ep-dataset-b-50929e8b3cfa0afb`, intelligence evaluation)
- [x] B real reflection (`ref-ddea35ba10e83190`)
- [x] independent_context_count >= 2
- [x] A real Cloud Run Map/Mend/`MODEL_READY` episode (`ep-m3cloudc5b11fe79553-81ff06ae999bf918`)
- [ ] B real Cloud Run Map/Mend/`MODEL_READY` episode

## HOLDOUT CONTROL

- [x] C sealed before promotion (`prem3-dataset-c-holdout`)
- [x] C v1 baseline before promotion (local intelligence; not cloud)
- [x] C excluded from learning
- [x] C sealed package fingerprint unchanged (`f1bfaa5b…`)
- [ ] C v1 cloud baseline

## LEARNING

- [x] candidate derived from A+B only
- [x] candidate novel
- [x] candidate scope explicit (`GLOBAL`)
- [x] candidate authority permitted (`ROUTING_HINT`)
- [x] negative-control conflicts = 0
- [x] routing regression = PASS
- [x] EXPERIENCE_LEARNED emitted (`cand-semantic_question_routing-3ebf87fa174b`)

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
- [ ] C v2 uses the same Cloud Run revision as C v1 (cloud pair not executed)

## CLOUD PROOF

- [ ] BigQuery experience rows read back for this cycle
- [ ] GCS artifacts verified for this cycle
- [x] Cloud Run revision recorded (`modelready-m3-00012-8xq`) — Dataset A golden; learning holdout pair not executed
- [ ] official Meridian evidence recorded for Dataset C v1/v2

## FULL SUCCESS

- [ ] every required checkbox true

Primary status: `PREM3_FIRST_REAL_LEARNING_CYCLE_NOT_READY`  
Principal reason: `CLOUD_PROOF_INCOMPLETE`
