# First real PreM3 learning cycle

Status: **local intelligence cycle proven. Cloud Taskmaster cycle proven on frozen `modelready-m3-00013-c4s`.** See `docs/proof/CLOUD_FIRST_LEARNING_CYCLE.md`.

This is machine-backed evidence that PreM3 promoted one A+B routing hint into DOMAIN_VIEW v1.0.1 and that the same sealed Summit & Pine assignment changed a **predeclared** handoff rank under DOMAIN_VIEW v2. It is **not** a claim that Dataset B or Dataset C completed Cloud Run `MODEL_READY`, and it is **not** a claim that bootstrap `app/domain/intelligence/data/current/domain_view.json` was replaced.

Proof artifacts: `experience/` and `evaluation/`.

## Controls

| Control | Value |
|---|---|
| Experiment | `prem3-first-real-learning-cycle-20260816` |
| Baseline git SHA | `43df9304e199157d8c637a6e5d2a5d14b60312c4` |
| DOMAIN_VIEW v1 | `1.0.0` / `b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf` |
| Promoted lessons at v1 | 0 |
| Dataset A role | `TRAINING_EXPERIENCE` (Music Center) |
| Dataset B role | `LEARNING_EVIDENCE` (Stride & Field) |
| Dataset C role | `SEALED_HOLDOUT` (Summit & Pine) |
| Sealed Dataset C package fingerprint | `f1bfaa5ba98b8f6d94cccb6b7a19c1e50ab8e315567e82fa3cf22129193bf18f` |
| First-cycle authority cap | `ROUTING_HINT` |
| Max promotions | 1 |
| Holdout access | `EVALUATION_ONLY` |

Dataset C expected-contract fingerprint at seal remains `d09c95deed895576765b4923f90c8a831c923687ab9016221d8e3c576a7dd522`. Model-input content fingerprint at seal remains `0a79f1c411a5268f15822d9d1d8afced8ac0171d0b6549479571640f134a4cee`.

The experiment compared v1 vs v2 using the same raw-tree fingerprint `a52101c2b400349cf1591c208b1a77bdfa9ab2e6d977d3051db4553be7846197` for Dataset C `raw/`. That is the independent-variable control for this run pair, not a replacement of the sealed package fingerprint.

## What ran

Assignment mode: `INTELLIGENCE_EVALUATION`. Pre-EDA diagnostics, semantic interview, and structured assessment were executed against each dataset's generated/sealed model-ready table. Missing BigQuery publish and official Meridian EDA were marked absent. Map/Mend for Dataset B/C is still Dataset-A-specific in `RunCoordinator` and was not generalized here.

Chronology:

1. Dataset C sealed on `main` (`prem3-dataset-c-holdout`)
2. Dataset C v1 intelligence baseline under DOMAIN_VIEW v1
3. Dataset A episode + reflection
4. Dataset B episode + reflection
5. A+B candidate extraction (C excluded)
6. Deterministic evaluation + routing regression
7. One lesson promoted → DOMAIN_VIEW `1.0.1`
8. Application plan sealed
9. Dataset C v2 under DOMAIN_VIEW v2, same input fingerprints
10. `evaluate_holdout_application` emitted `EXPERIENCE_APPLIED`

## Candidates

Six candidates were reported. Per-episode candidates were rejected for missing regression or insufficient independent support. One merged A+B candidate passed.

Selected (A+B only, ranking declared before C v2):

- `cand-semantic_question_routing-3ebf87fa174b`
- type: `semantic_question_routing`
- authority: `ROUTING_HINT`
- independent_context_count: 2
- novelty: `NOVEL`
- statement: When semantic-readiness questions are generated for a run, surface those questions before advisory spend or parameter commentary so causal gaps are not treated as settled numeric facts.

Predeclared effect, sealed before C v2:

- `HANDOFF_PRIORITY_UP`
- target `modeler-questions`
- baseline rank 2
- success `rank <= 1`
- direction `LOWER_IS_BETTER`

## DOMAIN_VIEW

| | v1 | v2 |
|---|---|---|
| version | `1.0.0` | `1.0.1` |
| fingerprint | `b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf` | `3a05706d0430f67baf853c24101a96a0485f8a2c6739578dd48c6a9d0765fd76` |
| promoted experiential claims | 0 | 1 |

Claim: `DV-EXP-cand-semantic_question_routing-3ebf87fa174b`

Bootstrap `current/domain_view.json` remains v1.0.0. Runtime activation for this experiment is `experience/domain_view_registry/`.

## Holdout application

| Metric | v1 | v2 | Pass |
|---|---|---|---|
| `modeler-questions` rank | 2 | 1 | yes |
| SEMANTIC_INTERVIEW presentation rank | 4 | 2 | yes (allowed companion change) |
| retrieved claim | none | `DV-EXP-cand-semantic_question_routing-3ebf87fa174b` | yes |
| Dataset C question families | 5 sealed positive families | same 5 | yes |
| causal roles assigned | false | false | yes |
| model-input fingerprint | unchanged | unchanged | yes |

Receipt: `experience/experience_applied_receipt.json` (`app-4ebdbca331ea9b09`).

## What this does not prove

- Cloud Run Dataset A/B/C `MODEL_READY` on one controlled revision
- BigQuery experience-ledger readback for this cycle
- GCS artifact proof for this cycle
- Official Meridian EDA invariance on Dataset C (EDA not run)
- Bootstrap DOMAIN_VIEW replacement

Current deployed Cloud Run (observed, not used as this experiment's runtime): revision `modelready-m3-00010-vjk`, image digest `sha256:5a618a17f8f854e81d419833bc7ff88a52c1a6d4abf280425f19c98644830c4d`, service account `m3-runtime@modelready-m3.iam.gserviceaccount.com`. That revision does not include this branch's routing-consumption code. Using it for C v1 and a later deploy for C v2 would be an uncontrolled comparison.

## Reproduction

```text
python scripts/run_first_learning_experiment.py
```

## Regression (this branch, local)

Commands:

- `py -3.13 -m ruff check app tests scripts` — all checks passed
- `py -3.13 -m pytest tests/unit --tb=no -q` — 292 passed, 1 skipped, 0 failed

Dataset B/C checked-in CSV SHA comparisons use LF-canonical hashing so Windows autocrlf working trees do not false-fail sealed fingerprints. Git blob for Dataset C `raw/google_ads_daily.csv` matches `HEAD`. Sealed package fingerprint remains `f1bfaa5b…`.
