# PreM3 intelligence contracts

Context-only package for the 2026-08-16 intelligence model. These files define knowledge architecture. They do not implement the deterministic MMM diagnostic tool suite.

| File | Role |
|---|---|
| `intelligence_version.json` | Version stamp for product, boot, domain, and registry context |
| `RULE_REGISTRY_DESIGN.md` | Authority fields and source-of-truth model |
| `SEMANTIC_READINESS_INTERVIEW_SPEC.md` | Dynamic causal-question contract |
| `MODELING_FEASIBILITY_SPEC.md` | Feasibility dimensions vs `MODEL_READY` |
| `SCOPE_SCENARIO_SPEC.md` | Read-only scope simulations |
| `GUIDED_REMEDIATION_CONTRACT.md` | Assess / Advise / Insight / Guide response format |
| `CONTEXT_MIGRATION_REPORT.md` | KEEP / REFINE / RECLASSIFY / VERIFY / SPLIT / DEPRECATE |
| `SOURCE_VERIFICATION_DISCREPANCY_REPORT.md` | Official Meridian re-verification |

Machine-readable specified diagnostics: `app/rules/intelligence_registry.yaml` (not loaded by the run coordinator).
