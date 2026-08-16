# Meridian Data-Prep Context — Migration Report

**Source file:** `docs/context/meridian/meridian_data_prep_context.md`  
**From:** supplied PreM3 context package (already intelligence-aligned)  
**To:** intelligence system v2.0.0  
**Date:** 2026-08-16

This is not an opaque rewrite. Each major section is classified.

| Code | Meaning |
|---|---|
| KEEP | Preserve substance |
| REFINE | Clarify wording, authority, or routing |
| RECLASSIFY | Change claimed hardness / authority |
| VERIFY | Re-check against official sources |
| SPLIT | Move some content to another file |
| DEPRECATE | Remove or stop treating as binding |

---

## Header / how to use

**REFINE + SPLIT.** Keep as the long-form execution/domain reference. Startup constitution moves to `prem3_mmm_boot_context.md`. Product/value questions move to `prem3_product_context.md`. Conversation patterns stay in `meridian_advisor_playbook.md`.

## §0 Knowledge / action authority

**KEEP.** Taxonomies match the mission. Added explicit mapping from intelligence decision classes to current runtime `AUTO_SAFE` / `APPROVAL_REQUIRED` / `BLOCKED`.

## §1 Target artifact / formats / variable classes

**KEEP + VERIFY.** Official supported formats still include CSV, Xarray, ndarray, DataFrame, and DataFrame-convertible files. Variable classes (paid, paid R&F, organic, organic R&F, non-media treatments, controls) remain causal/modeling roles, not just schema labels. `DataFrameInputDataBuilder` remains the DataFrame path; `CoordToColumns` remains the CSV mapping contract.

## §2 Hard rules

**RECLASSIFY + VERIFY.** Completeness, non-negative media, summability, media/spend dimension match, regular panel, and time-constant-variable ERROR remain `MERIDIAN_NORMATIVE`. Campaign-to-channel aggregation is a **DESIGN_DEFAULT**, not a hard library rule. Resolution of missingness is no longer a single hard "fill zero" rule; see §6.

## §3 Grain

**KEEP + REFINE.** Weekly default and geo preference remain official best practice / strong default, not universal hard blockers. Top 50–100 DMA language stays a rule of thumb. Pre-period media is first-class; 8–13 weeks is planning guidance, not a universal Meridian hard rule.

## §4 Timeframe

**KEEP + RECLASSIFY.** 2-year geo / 3-year national / 3-year monthly remain official planning baselines, not `MODEL_READY` gates. Structural-break caution kept.

## §5 Parameter budget

**RECLASSIFY + VERIFY.** Lenient formula confirmed against official Amount of data needed / EDA docs (2026-08-16). Strict no-pooling example confirmed. Shadow complexity remains foundational MMM, never official Meridian. The former "<10 must reduce scope" language is **deprecated as a hard rule** and replaced by high/severe parameter pressure + `review_recommended=true`. Official docs explicitly avoid a single correct minimum and say not to remove important confounders.

## §6 Missing data

**RECLASSIFY.** Official collect-data page permits media zero-fill when a channel was inactive and recommends imputation techniques for KPI/controls. PreM3 policy now requires inactivity evidence for media zeros and `APPROVAL_REQUIRED` for KPI/control imputation. This is a policy refinement, not a contradiction of Meridian's completeness requirement.

## §6.2 National-only channels / knots

**KEEP + REFINE.** Population allocation remains a documented design option. EDA compatibility `knots < n_times` stays scoped and is not final ModelSpec policy.

## §7 Aggregation / R&F / exposure metric

**KEEP.** Spend-as-proxy trap, per-period reach (not cumulative), and control aggregation config remain.

## §8 PreM3 diagnostics vs official EDA

**KEEP + REFINE.** Provenance split is now a first-class product rule. Official VIF 1000 and |r| 0.999 defaults re-verified. Tighter thresholds remain optional PreM3 advisory diagnostics.

## §9 Variable classification / GQV / mediators

**KEEP.** Confounder / predictor / mediator definitions preserved. Budget-setting elicitation, GQV nuance, downstream media, remarketing, price/promotion questions preserved. Semantic readiness interview extracted to its own spec; the long-form examples stay here.

## §10 Known failure modes

**REFINE.** Substance kept. Added failure-mode metadata table (detectable_from_data, decision class, knowledge class).

## §11 Implementation notes

**REFINE + VERIFY.** Python 3.11/3.12 official; worker pin remains `google-meridian==1.8.0` on Python 3.12. Do not treat public index latest as the proven pin.

## §12 Output model / four behaviors

**KEEP.** Aligns with product intelligence. Guided remediation and feasibility vs `MODEL_READY` now have dedicated specs.

## §13 Sources

**KEEP + VERIFY.** Tier 1 URLs still resolve. Last-verified date set to 2026-08-16.

---

## Files created rather than merged into data-prep

| File | Why SPLIT |
|---|---|
| `prem3_mmm_boot_context.md` | Every-agent constitution; keep prompts small |
| `prem3_product_context.md` | Product/value intelligence; keep execution agents from becoming sales bots |
| `meridian_advisor_playbook.md` | Conversation / gold-standard answers |
| `intelligence/*` specs | Contracts for the next diagnostic-tool mission |
| `app/rules/intelligence_registry.yaml` | Machine-readable specified-not-implemented catalog |
