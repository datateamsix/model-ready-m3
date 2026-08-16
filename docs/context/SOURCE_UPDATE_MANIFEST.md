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
