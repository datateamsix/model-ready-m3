# PICKUP — cloud first learning cycle

Saved 2026-08-17. Resume from this file. Do not re-run the experiment from scratch without reading **Already live in GCP**.

## Status

Cloud cycle **succeeded**: `EXPERIENCE_APPLIED` on frozen `modelready-m3-00013-c4s`.

Git **did not land**. Commit spawn aborted. Branch is local-only, unpushed, uncommitted.

## Git

- Branch: `feature/prem3-cloud-first-learning-cycle`
- HEAD: `f5ac8eeb0782358abb1b2d7af60ec96ab02cfc5c` (same as origin `feature/prem3-provider-agnostic-coordinator` / PR #10)
- Stacked on: PR #10, which is stacked on PR #9
- Do not merge #9/#10/#this automatically
- Do not commit: `brand/brand-assets/fonts/`, `PREM3_MISSION_2_FRONTEND_EXECUTION_PROMPT_PACK.md`, `frontend/`

## Already live in GCP (do not redo blindly)

DOMAIN_VIEW **v1.0.1 is already the active GCS pointer**. Cloud Run `00013-c4s` will load it.

- Registry: `gs://modelready-m3-912257136465-artifacts/experiments/cloud_first_learning_cycle_001/domain_view_registry/`
- Active version: `1.0.1`
- Active fingerprint: `5847aaf4c1740cc25b52c664114ba5d2c97ec587bb44f2a22e18c0f5154e42f1`
- Promoted lesson: `cand-semantic_question_routing-9e0ebb37bed1`

Re-running `scripts/run_cloud_learning_experiment.py` will **fail C-v1 control** unless the pointer is first restored to v1.0.0 (`b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf`, 0 lessons). Prefer commit/push of existing evidence. Do not rebuild the image.

Frozen runtime (unchanged):

- Service: `modelready-m3` / `us-central1`
- Revision: `modelready-m3-00013-c4s` (100% traffic)
- Image: `sha256:7dffe4904c1a3ce9e2bb7426793954608bb3d3b5c274b2dc592fcefb0246f6d6`
- Image code SHA: `1222eb6fcdabec5ea6132347c8b6df2bc907f705`
- Preserve golden: `modelready-m3-00012-8xq` / run `m3cloudc5b11fe79553`

## Proven results (do not re-infer)

| Step | Result |
|---|---|
| C-v1 before promotion | `dataset-c-v1-cloud-00013`; DOMAIN_VIEW 1.0.0; `modeler-questions` rank **2**; retrieved claims `[]` |
| A reflection | cloud episode `ep-m3cloud653724094004-8839ba8855077a04` from `m3cloud653724094004` |
| B reflection | intelligence eval `ep-dataset-b-cloud-learning-00013-2f2de878cf841b6d` (Map/Mend `m3cloud856c4fdede10` stayed `REMEDIATING`) |
| Candidate | `cand-semantic_question_routing-9e0ebb37bed1` (A+B only; C excluded) |
| EXPERIENCE_LEARNED | `experience/cloud_learning/experience_learned_receipt.json` |
| C-v2 | `dataset-c-v2-cloud-00013`; rank **1**; claim `DV-EXP-cand-semantic_question_routing-9e0ebb37bed1` |
| EXPERIENCE_APPLIED | `app-2bf74f1f98e5c6d7` |
| Declared effect | `HANDOFF_PRIORITY_UP` target `modeler-questions` 2→1; `inference_used: false`; undeclared field changes `[]` |
| C seal | still `f1bfaa5ba98b8f6d94cccb6b7a19c1e50ab8e315567e82fa3cf22129193bf18f` |
| Bootstrap file | `app/domain/intelligence/data/current/domain_view.json` still **1.0.0** |

C-v1/C-v2 used `INTELLIGENCE_EVALUATION` on the sealed table. Cloud Run cannot run pre-EDA without publish; C correctly did not publish.

This v2 fingerprint is **not** the local-cycle fingerprint `3a05706d…`.

## Remaining work

1. Commit the uncommitted files listed below (not fonts / frontend prompt pack).
2. `git push -u origin feature/prem3-cloud-first-learning-cycle`
3. Open PR stacked on PR #10 (`feature/prem3-provider-agnostic-coordinator`). Merge order: **#9 → #10 → this PR**. Rebase after each merge.
4. Do not reset GCS v1.0.1 unless repeating the experiment.

Suggested commit message:

```
Prove the first cloud learning cycle on frozen revision 00013-c4s.

Capture C-v1 before promotion, activate DOMAIN_VIEW v2 as GCS data, rerun the same sealed C, and measure the predeclared handoff-rank change without inference.
```

## Uncommitted paths to include

- `app/mel/cloud_learning.py`
- `scripts/run_cloud_learning_experiment.py`
- `tests/unit/test_mel_cloud_learning_experiment.py`
- `docs/proof/CLOUD_FIRST_LEARNING_CYCLE.md`
- `docs/proof/FIRST_REAL_LEARNING_CYCLE.md`
- `docs/proof/FIRST_REAL_LEARNING_SCORECARD.md`
- `docs/context/02_SYSTEM_ARCHITECTURE.md`
- `docs/context/06_EXECUTION_PLAN.md`
- `docs/context/08_DECISION_LOG.md`
- `docs/context/SOURCE_UPDATE_MANIFEST.md`
- `evaluation/cloud_*.json`
- `evaluation/dataset_c_v1_cloud_baseline.json`
- `evaluation/dataset_c_v2_cloud_application.json`
- `experience/cloud_learning/`

Unit tests were run after the new tests; ruff clean on the new files. Re-confirm `pytest tests/unit` counts on resume if needed.

## Do not

- Modify `frontend/`
- Build `prem3-api`
- Rebuild/deploy a new Cloud Run revision for this cycle
- Treat Dataset C Map/Mend as MODEL_READY
- Claim bootstrap DOMAIN_VIEW replacement
- Extract new lessons from Dataset C
