# First PreM3 learning cycle — status

This is the inspectable proof surface for MEL Episode Core. It is **not** a claim that the full Dataset A → DOMAIN_VIEW v2 → Summit & Pine `EXPERIENCE_APPLIED` cycle is cloud-proven.

Architecture:

- MEL lifecycle: `docs/architecture/PREM3_MEL_LEARNING_CYCLE.mmd`
- reflective self-model: `docs/architecture/PREM3_SELF_MODEL.mmd`
- learning pillars: `docs/architecture/PREM3_CORE_LEARNING_PILLARS.mmd`

## 1. DOMAIN_VIEW v1

- version: `1.0.0`
- fingerprint: `b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf`
- promoted experiential lessons: **0**

## 2. Source episode

Episode Core can close `MODEL_READY`, `USER_REQUIRED`, `EDA_BLOCKED`, and `FAILED` runs. Non-terminal runs cannot close. `complete_dataset_run` records an episode after a terminal assignment; MEL failure cannot change `MODEL_READY`. See `app/mel/episode.py`.

## 2b. ExperienceReflection

Closed episodes can be reflected (`app/mel/reflect.py`, artifact `experience/experience_reflection.json`). Memory is recall. Reflection is evaluation. Learning is validated change. Reflection has no operational authority and does not change DOMAIN_VIEW.

## 3. CandidateLesson

Candidates are typed, fingerprinted, and extracted from an `ExperienceReflection` plus referenced episode evidence. They are not pre-inserted into `promoted_lessons.yaml`. No reflection means no production candidate extraction.

## 4. Evaluation

Deterministic stages: structure, novelty, authority, policy, scope, evidence, privacy, behavior effect, regression, promotion authority.

## 5. Promotion

Synthetic unit fixtures can promote a routing hint, stage DOMAIN_VIEW, regress, activate, and emit `EXPERIENCE_LEARNED`. That fixture is labeled `synthetic_fixture=true` and is not Dataset A production learning.

## 6. DOMAIN_VIEW v1 → v2

Bootstrap DOMAIN_VIEW remains v1.0.0 with 0 promoted lessons. Runtime activation writes versioned data to a registry directory; it does not rewrite Python.

## 7. Holdout

Summit & Pine Dataset C is synthetic and sealed at `tests/fixtures/summit_and_pine/dataset_c/learning/holdout_manifest.json` with `lesson_ids_visible_at_seal: []`.

## 8–11. Baseline / learned behavior / EXPERIENCE_APPLIED

Not proven on the sealed holdout against a real promoted Dataset A lesson.

## 12. Limitations

- Cloud Dataset A golden `MODEL_READY` exists; Gemini may skip intelligence tools on a given run. Episode evidence is present-when-available.
- No Eventarc/Ambient.
- No AUTO_SAFE learned policy.
- No final model fit.
- Memory is not learning. Reflection is not learning. A candidate is not learning. `EXPERIENCE_APPLIED` is the strongest proof and is not claimed here.
