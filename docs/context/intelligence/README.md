# PreM3 intelligence contracts

Context-only package for the intelligence model. These files are the human-readable contracts for the deterministic MMM diagnostic suite in `app/intelligence/`. They are not the runtime implementation.

| File | Role |
|---|---|
| `intelligence_version.json` | Version stamp for product, boot, domain, and registry context |
| `RULE_REGISTRY_DESIGN.md` | Authority fields and source-of-truth model |
| `SEMANTIC_READINESS_INTERVIEW_SPEC.md` | Dynamic causal-question contract |
| `MODELING_FEASIBILITY_SPEC.md` | Feasibility dimensions vs `MODEL_READY` |
| `SCOPE_SCENARIO_SPEC.md` | Read-only scope simulations |
| `GUIDED_REMEDIATION_CONTRACT.md` | Assess / Advise / Insight / Guide response format |
| `SOURCE_VERIFICATION_DISCREPANCY_REPORT.md` | Official Meridian re-verification |

Machine-readable specified diagnostics: `app/rules/intelligence_registry.yaml` (not loaded by the run coordinator).

Operational compilation: `docs/context/domain-view/` and `app/domain/intelligence/`. DOMAIN_VIEW.md is generated. v1 has 0 promoted experiential lessons.
