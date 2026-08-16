# PreM3 Source Update Manifest — repo scaffold

**Date:** 2026-08-15

Canonical decisions synchronized into the repository scaffold:

1. ModelReady is the product.
2. M3 Agent is the autonomous worker.
3. M3 means Map. Mend. Model-Ready. and naturally references Media Mix Modeling.
4. MEL is the evidence-driven experience loop embedded inside M3.
5. BigQuery model-artifact publishing is a first-class M3 action.
6. `MODEL_READY` requires deterministic readiness, BigQuery publish parity, a complete Meridian input contract, provenance, and official pre-modeling EDA with zero ERROR findings.
7. Autonomous Meridian pre-modeling EDA (including EDA-only `sample_prior`) is required. Posterior / model execution remains approval-gated.
8. The hackathon MVP is the first production-minded vertical slice of the future SaaS, but hackathon scope wins over SaaS breadth through Aug 31.
9. Official Meridian input rejection or ERROR findings produce a `USER_REQUIRED` resolution pack. `google-meridian` is not installed in the M3 ADK runtime.

The checked-in implementation must remain consistent with `AGENTS.md` and the documents in `docs/context/`.

---

# Source Update Manifest v3 — PreM3 rebrand

**Date:** 2026-08-15

Canonical changes:

1. ModelReady product → PreM3.
2. M3 Agent user identity → PreM3.
3. M3 → Map. Mend. Model. operating method.
4. MEL → PreM3 Experience Loop.
5. M3 Learning Receipt → PreM3 Learning Receipt in new user-facing artifacts.
6. `MODEL_READY` remains the machine/operational state.
7. BigQuery remains the first-class model-consumption endpoint.
8. Official Meridian EDA is part of autonomous pre-modeling.
9. EDA-only prior use does not authorize final modeling priors.
10. Posterior/model fit remains governed outside autonomous PreM3.
11. `USER_REQUIRED` / resolution guidance is a first-class product output.
12. Infrastructure IDs are intentionally preserved.
13. Complete MEL episode/context upgrade remains the next workstream.
14. GitHub repository is `datateamsix/prem3`. The Python package name remains `model-ready-m3`.

---

# Source Update Manifest v4 — PreM3 intelligence context

**Date:** 2026-08-16  
**Intelligence version:** 2.0.0

Canonical changes:

1. Product/value intelligence is now canonical context (`PREM3_PRODUCT_CONTEXT.md`).
2. Four product behaviors are **ASSESS / ADVISE / INSIGHT / GUIDE**.
3. Advisory guidance is a first-class capability (`MERIDIAN_ADVISOR_PLAYBOOK.md`).
4. Every agent loads `PREM3_MMM_BOOT_CONTEXT.md`; long-form files are path-specific.
5. Computational and semantic readiness remain distinct.
6. Official Meridian rules remain separate from PreM3 heuristics.
7. Run insights must be evidence-linked.
8. Guided remediation must identify actions and owners.
9. Missing media is not automatically zero.
10. KPI/control imputation remains approval-gated.
11. Causal roles are not inferred from correlation.
12. Modeling feasibility remains separate from `MODEL_READY`.
13. Parameter-pressure interpretation is a heuristic and cannot independently block `MODEL_READY`.
14. Rule/diagnostic authority registry is designed (`app/rules/intelligence_registry.yaml`); future diagnostic tools are specified, not implemented.
15. No BigQuery, EDA worker, `MODEL_READY` gate, remediation-tool, Eventarc, or MEL runtime change in this update.

---

# Source Update Manifest v5 — DOMAIN_VIEW

**Date:** 2026-08-16

1. DOMAIN_VIEW introduced as the versioned operational knowledge set.
2. DOMAIN_VIEW is generated and versioned; Markdown is a projection.
3. DOMAIN_VIEW is not raw memory.
4. DOMAIN_VIEW distinguishes source updates from experiential learning.
5. MEL promotion will update DOMAIN_VIEW; it is not implemented yet.
6. EXPERIENCE_APPLIED remains proof of later behavior change.
7. Global / organization / run context are separate.
8. Meridian normative rules cannot be overridden by learned claims.
9. Final modeling priors/spec remain excluded from learned authority.
10. DOMAIN_VIEW v1 has 0 promoted experiential lessons.

---

# Source Update Manifest v6 — computational + semantic run intelligence

**Date:** 2026-08-16

1. Deterministic pre-EDA diagnostic surface implemented (`app/intelligence/`).
2. Semantic readiness interview is dynamic and evidence-triggered.
3. Modeling feasibility is dimensional and distinct from `MODEL_READY`.
4. Scope scenario engine is read-only and does not mutate production input.
5. New receipts: `intelligence/pre_eda_diagnostic_receipt.json`, human report, feasibility, semantic interview, optional scope scenarios.
6. Authority boundaries preserved: PreM3 pre-EDA ≠ official Meridian EDA; heuristics cannot independently block `MODEL_READY`.
7. DOMAIN_VIEW is consumed (version + fingerprint recorded); it is not mutated.
8. No MEL learning, `EXPERIENCE_LEARNED`, or `EXPERIENCE_APPLIED` introduced.
9. No final-model authority (priors, knots, ModelSpec) introduced.
10. High-level agent tools registered on the existing PreM3 orchestrator. No decorative specialist agents.
11. Official Meridian worker, EDASpec defaults, and `MODEL_READY` gate remain unchanged.
12. Default CI remains credential-free; production diagnostics fail closed without a verified BigQuery endpoint.

---

# Source Update Manifest v7 — structured response architecture

**Date:** 2026-08-16

1. `RESPONSE_STYLE_GUIDE` added as canonical presentation context.
2. Structured response taxonomy added (`app/response/`).
3. Response status taxonomy added (distinct from official Meridian ERROR/ATTENTION/INFO).
4. Evidence, action, and authority contracts added. Knowledge authority and decision authority remain unflattened.
5. Official Meridian presentation boundary preserved.
6. Progressive disclosure defined (summary / details / proof).
7. Output QA architecture defined; full evaluation harness deferred.
8. No MEL promotion added.
9. No DOMAIN_VIEW update added.
10. Presentation tools consume existing intelligence; they do not recalculate diagnostics.

---

# Source Update Manifest v8 — docs filename convention and context cleanup

**Date:** 2026-08-16

1. Live context markdown filenames use `ALL_CAPS_SNAKE_CASE` (`PREM3_PRODUCT_CONTEXT.md`, `PREM3_MMM_BOOT_CONTEXT.md`, `MERIDIAN_DATA_PREP_CONTEXT.md`, `MERIDIAN_ADVISOR_PLAYBOOK.md`).
2. Brand naming lives at `docs/brand/PREM3_BRAND_AND_NAMING.md`.
3. `README.md` files remain `README.md` (GitHub index convention).
4. Removed completed-phase / one-shot context: `CURSOR_HANDOFF.md`, `CONTEXT_PACKAGE_NOTES.md`, `intelligence/CONTEXT_MIGRATION_REPORT.md`, `PREM3_REBRAND_MIGRATION.md`.
5. Frozen DOMAIN_VIEW v1.0.0 provenance paths are unchanged.
6. No `MODEL_READY`, EDA worker, BigQuery, Eventarc, or MEL runtime change.

---

# Source Update Manifest v9 — MEL Episode Core

**Date:** 2026-08-16

1. ExperienceEpisode implemented.
2. EDA alignment implemented.
3. CandidateLesson implemented.
4. Lesson evaluation implemented.
5. Promotion policy implemented (`app/rules/mel_promotion_policy.yaml`).
6. EXPERIENCE_LEARNED implemented for synthetic promotion tests.
7. Runtime DOMAIN_VIEW staging/activation implemented as data.
8. Holdout protocol implemented; Dataset C Summit & Pine sealed before candidate extraction.
9. ExperienceApplication implemented.
10. EXPERIENCE_APPLIED implemented in synthetic unit tests; not proven on the sealed holdout.
11. No final-model learning introduced.
12. No AUTO_SAFE learned policy in the first cycle.
13. No Eventarc/Ambient trigger.
14. MODEL_READY gate unchanged.
15. Episode closure is system-owned after `complete_dataset_run` and cannot change run status.
16. ExperienceReflection is a first-class MEL artifact between episode and candidate extraction. It has no operational authority.
17. Production CandidateLesson extraction requires a reflection. Possible improvements are not lessons.

---

# Source Update Manifest v10 — Dataset B Stride & Field learning evidence

**Date:** 2026-08-16

1. Independent synthetic Dataset B (Stride & Field) added at `datasets/stride_and_field/dataset_b/`.
2. Generator `scripts/generate_dataset_b.py` extends Music Center helpers in `app/synthetic/mmm.py` (extracted from `scripts/generate_demo_data.py`).
3. Music Center `datasets/music_center/dataset_b/` is unchanged and is not this MEL evidence package.
4. Dataset C Summit & Pine holdout fingerprints from the Episode Core stub were replaced by the hospitality seal in v11; Dataset B must not write Dataset C.
5. Expected run-intelligence values are computed from generated truth, not hand-authored ratios.
6. Semantic expected answers match question families, not exact wording.
7. CandidateLesson may report cross-episode fields; reporting is not promotion.
8. Minimal Klaviyo directory stub added; not executable mapping.
9. No `EXPERIENCE_LEARNED`, DOMAIN_VIEW v2, or `EXPERIENCE_APPLIED` from dataset generation.
10. No MEL threshold change. No Eventarc/Ambient. No final-model learning. No `PREM3_PRODUCT_CONTEXT.md` learning claim.
11. Cloud Dataset B `MODEL_READY` run is deferred.
12. Proof surface: `docs/proof/DATASET_B_STRIDE_AND_FIELD.md`.

---

# Source Update Manifest v11 — Dataset C Summit & Pine sealed holdout

**Date:** 2026-08-16

1. Dataset C created as Summit & Pine regional mountain lodging holdout at `datasets/summit_and_pine/dataset_c/`.
2. Business type: synthetic outdoor hospitality / bookings KPI.
3. Seed `20260816` kept; generator version `2.0.0` replaced the Episode Core furniture stub.
4. Package fingerprint `f1bfaa5ba98b8f6d94cccb6b7a19c1e50ab8e315567e82fa3cf22129193bf18f`.
5. Holdout role `SEALED_HOLDOUT`; sealed before learning; DOMAIN_VIEW `1.0.0` / `b3ad518e…`; 0 visible lessons at seal.
6. Training, candidate, and reflection-training access denied via typed `DatasetRole` / `ReflectionRole`.
7. DOMAIN_VIEW v1 baseline captured locally; official Meridian EDA and cloud run not executed in the generator.
8. Negative controls included to detect overgeneralization.
9. Canonical dataset root `datasets/`; full A/B/C packages are not duplicated under `tests/fixtures/`.
10. No DOMAIN_VIEW change. No `EXPERIENCE_LEARNED`. No `EXPERIENCE_APPLIED`.
11. Minimal `synthetic_pms` directory stub added; registry count 52.
12. Proof surface: `docs/proof/DATASET_C_SUMMIT_AND_PINE_HOLDOUT.md`.

---

# Source Update Manifest v12 — First real local learning cycle

**Date:** 2026-08-16

1. First A+B candidate cycle executed without Dataset C training access.
2. At most one lesson promoted: `ROUTING_HINT` semantic-question handoff priority.
3. DOMAIN_VIEW `1.0.0` → `1.0.1` in the experiment registry; bootstrap `current/domain_view.json` unchanged.
4. Predeclared `HANDOFF_PRIORITY_UP` for `modeler-questions` sealed before Dataset C v2.
5. Local Summit & Pine application test emitted `EXPERIENCE_APPLIED`.
6. No `promoted_lessons.yaml` hand edit. No Python rewritten to encode the lesson text.
7. MEL first-cycle authority cap remains `ROUTING_HINT`.
8. Cloud Taskmaster / BigQuery / GCS proof for this cycle is incomplete.
9. Frontend was not modified.
10. Proof surface: `docs/proof/FIRST_REAL_LEARNING_CYCLE.md`.

