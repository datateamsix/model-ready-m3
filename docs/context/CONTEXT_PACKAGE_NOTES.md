# PreM3 Context Package — Update Notes

This package contains three context files intended to be placed in the PreM3 repository before running the MMM + Product Intelligence Context System prompt.

## Files

- `meridian_data_prep_context.md` — execution/domain reference
- `meridian_advisor_playbook.md` — advisory/conversational reference
- `prem3_product_context.md` — product/value intelligence

## Key refinements applied

### Domain / execution
- Added explicit knowledge-authority and action-authority taxonomies.
- Separated PreM3 pre-EDA diagnostics from official Meridian EDA findings.
- Changed the ~10 observations/parameter interpretation from a hard rule to an evidence-backed review heuristic.
- Preserved lenient, strict, and shadow parameter-budget views with clearer authority.
- Corrected missing-media policy: zero-fill only when inactivity is supported by evidence.
- Made KPI/control imputation approval-required rather than silently automatic.
- Made channel consolidation/drop actions approval/modeler-reviewed rather than automatic.
- Added semantic readiness and open causal-question structure.
- Preserved confounder/predictor/mediator, GQV, downstream-search, price/promotion, remarketing/targeting, and budget-setting causal logic.
- Added modeling-feasibility vs `MODEL_READY` distinction.
- Updated the conceptual pipeline to BigQuery verification → PreM3 diagnostics → official Meridian EDA → interpretation/handoff.
- Added Assess / Advise / Insight / Guide as output behavior.

### Advisor playbook
- Reframed the advisor around Assess / Advise / Insight / Guide.
- Added tool-first behavior when verified run data exists.
- Added explicit authority language for official Meridian vs PreM3 diagnostics vs heuristics vs judgment.
- Added product/value question routing.
- Reworked missingness guidance to require inactivity evidence and approval for KPI/control imputation.
- Reworked parameter-pressure and channel-scope advice to avoid false hard gates.
- Added semantic readiness / open causal questions.
- Reworked feasibility triage into technical blockers vs modeling-feasibility concerns.
- Added stronger remediation structure and guardrails.

### Product/value context
- Added canonical product definition and four core behaviors.
- Added major problems solved, buyer/adoption value, audience-specific value, differentiation, trust model, proof-vs-roadmap boundary, defensibility, and common product questions.
- Added guarded answers for "Why PreM3?", "Why not Meridian?", "Why not RAG?", "Why not scripts?", and "Why not consultants?"
- Avoided unsupported quantitative ROI/customer claims.
- Added a judge/diligence Q&A bank covering MEL learning, architecture distinctiveness, agent-vs-workflow boundaries, deterministic proof, autonomous change authority, semantic readiness, Meridian-vs-PreM3 authority, `MODEL_READY`, learning safety, `USER_REQUIRED`, and inspectable proof artifacts.
- Added a canonical `MODEL_READY` explanation: deterministic readiness + authorized remediation + explicit contract + versioned BigQuery publication + independent read-back/fingerprint verification + official Meridian EDA with zero ERROR + completed interpretation/handoff.
- Added a precise MEL answer that distinguishes learning from memory and explicitly separates current design/architecture from the still-to-be-proven end-to-end `EXPERIENCE_APPLIED` milestone.

## Important

These edits were the incoming draft. The 2026-08-16 intelligence-context mission re-verified official Meridian claims, added `prem3_mmm_boot_context.md`, intelligence specs, the specified-not-implemented registry, product-context tests, AGENTS.md routing, and the decision/source-manifest updates.

Do not treat this notes file as the canonical product spec. Use `prem3_product_context.md` and `prem3_mmm_boot_context.md`.
