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

1. Product/value intelligence is now canonical context (`prem3_product_context.md`).
2. Four product behaviors are **ASSESS / ADVISE / INSIGHT / GUIDE**.
3. Advisory guidance is a first-class capability (`meridian_advisor_playbook.md`).
4. Every agent loads `prem3_mmm_boot_context.md`; long-form files are path-specific.
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
