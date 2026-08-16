# PreM3 Semantic Readiness Interview — Specification

**Status:** contract only. Do not implement `generate_semantic_readiness_interview` in this mission.  
**Version:** 1.0  
**Intelligence version:** 2.0.0

---

## Definition

**Semantic readiness** is what causal and business information must be understood that the table itself cannot establish.

It is first-class readiness, distinct from computational readiness.

Ideal user experience:

> I computed everything the data can tell me. There are N important things the data itself cannot establish.

Then list only the **open causal questions** triggered by this run. Do not deliver a generic 30-question survey.

---

## Question contract

Each open causal question must include:

| Field | Required |
|---|---|
| `question_id` | yes |
| `family` | yes |
| `question` | yes |
| `why_prem3_is_asking` | yes |
| `trigger_evidence` | yes |
| `possible_causal_concern` | yes |
| `affected_variables` | yes |
| `what_changes_depending_on_the_answer` | yes |
| `required_human_role` | yes |
| `blocks_current_preparation` | yes |
| `requires_modeler_review_only` | yes |
| `knowledge_class` | always `MMM_JUDGMENT` |
| `decision_class` | `USER_REQUIRED` or `MODELER_REVIEW_REQUIRED` |

Correlation, overlap, and temporal ordering may populate `trigger_evidence`. They must not populate a causal-role assignment.

---

## Question families

Generate a question only when the run actually contains the relevant variables or patterns.

### Budget-setting

Trigger: material spend spikes, planned flights, or unknown allocation process.

Ask how total budget, channel allocation, and high-spend weeks were determined, and whether expected demand, prior KPI, launches, inventory, promotions, or external events influenced spend.

Why: a variable that influences both media treatment and demand may be a confounder.

### Promotion

Trigger: a promotion flag or calendar is present.

Ask: were promotions scheduled independently, or deliberately coordinated with media campaigns?

Why: promotion may be confounder, treatment, predictor, or mediator depending on the business process. Overlap alone does not decide.

### Price / discount

Trigger: price or discount variables exist.

Ask: were price changes determined independently of media, or timed to support advertising?

Do not automatically classify price as a control.

### Google Query Volume / search demand

Trigger: a query-volume-like variable **and** paid search **and** upper-funnel media.

Ask: did upper-funnel campaigns materially drive branded search or query volume during the modeling period?

Do not reduce this to "GQV is always a control." For paid search, query activity may influence opportunity/spend. For upper-funnel, media may influence search behavior. One GQV variable can have different causal implications across channels.

### Downstream media

Trigger: paid search plus upper-funnel, or remarketing plus site-visit-like structure.

Recognize possible structures such as TV → branded search → paid search, or social/display → site visit → remarketing.

Do not silently assume every channel is exogenous.

### Remarketing / targeting

Trigger: remarketing, retargeting, CRM, or high-intent targeting labels.

Ask: was this media delivered because the user had already demonstrated demand or intent, and was that demand itself influenced by other marketing?

Possible concerns: selection bias, endogeneity, downstream treatment.

### Organic media

Trigger: organic media is present and material.

Ask what drove its timing: independent, campaign-coordinated, event-driven, or promotion-driven?

### Seasonality / lagged controls

Do not automatically port Robyn-style seasonality columns into Meridian. Controls require causal justification. Lag only with a plausible causal rationale. Lags consume complexity.

---

## Generation rules

1. Build the interview from actual variables, channels, providers, detected patterns, known causal risks, and unresolved mappings.
2. Prefer the smallest sufficient question set.
3. If no semantic triggers fire, say so. Do not invent questions.
4. If an unanswered question changes current variable classification, it may block preparation (`USER_REQUIRED`).
5. If it affects later specification only, proceed with `MODELER_REVIEW_REQUIRED` / `review_recommended=true`.
6. Never assign confounder / predictor / mediator from correlation alone.

---

## Alignment with User Resolution Pack

Family mapping:

| Interview family | Issue family |
|---|---|
| Budget-setting, GQV, promotion, price, remarketing, organic | `CAUSAL_CONTEXT_GAP` |
| Unresolved mapping that prevents classification | `DATA DEFECT` or `CAUSAL_CONTEXT_GAP` |
| Missing source calendar / GQV / R&F / pricing history | `SOURCE ACQUISITION GAP` |
| Final treatment/control role | `MODELER SPECIFICATION REVIEW` |
