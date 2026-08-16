# PreM3 Modeling Feasibility — Specification

**Status:** contract only. Do not implement `assess_modeling_feasibility` in this mission.  
**Version:** 1.0  
**Intelligence version:** 2.0.0

---

## Definition

**Modeling feasibility** is broader than `MODEL_READY`.

`MODEL_READY` is the verified pre-modeling contract plus official Meridian EDA with zero ERROR.

A dataset may be `MODEL_READY` while still having:

- `HIGH_PARAMETER_PRESSURE` or `SEVERE_PARAMETER_PRESSURE`
- `LIMITED_HISTORY`
- `LIMITED_EXECUTION_RANGE`
- `CAUSAL_CONTEXT_GAPS`
- `MODELER_REVIEW_RECOMMENDED`

Do not build an opaque magic score. Prefer explicit dimensions.

---

## Dimensions

| Dimension | What it asks | Typical knowledge class |
|---|---|---|
| `DATA_CONTRACT` | Does the input satisfy Meridian load/completeness/summability/grain rules? | `MERIDIAN_NORMATIVE` |
| `HISTORY` | Is the usable window long enough and still structurally relevant? | mixed official guidance + heuristic |
| `GEO_COVERAGE` | Are geos reliable, complete, and informative? | mixed |
| `PARAMETER_PRESSURE` | How many observations relative to proposed complexity? | calculation deterministic; interpretation heuristic |
| `CHANNEL_VARIATION` | Do treatments actually move? | diagnostic |
| `SPEND_RANGE` | Is observed support wide enough for later extrapolation questions? | diagnostic; no pre-fit ROI claims |
| `COLLINEARITY` | Are treatments/controls near-redundant? | official EDA + optional advisory |
| `PRE_PERIOD_MEDIA` | Does media exist before KPI start so adstock is not cold-started? | heuristic / design |
| `SEMANTIC_CAUSAL_CONTEXT` | Are consequential causal roles unresolved? | `MMM_JUDGMENT` |
| `OFFICIAL_MERIDIAN_EDA` | What did official Meridian find? | `MERIDIAN_NORMATIVE` |

---

## Computational readiness vs semantic readiness

**Computational readiness** — what PreM3 can establish objectively from verified data:

data shape; grain; calendar continuity; history; geo coverage; missingness; media/spend consistency; parameter pressure; channel spend shares; variation; spend range; pre-period media; collinearity; population relationships; R&F structure; aggregation evidence.

**Semantic readiness** — what the table cannot establish. See `SEMANTIC_READINESS_INTERVIEW_SPEC.md`.

Both are required for a complete feasibility picture. Only the contract + official ERROR gate determine `MODEL_READY`.

---

## Parameter-pressure policy

Preserve three views:

1. **Lenient / Meridian EDA framing**  
   `n_data_points = n_geos × n_times`  
   `n_parameters = (n_geos - 1) + n_knots + n_controls + n_treatments`  
   Official docs: this is the EDA package calculation and a practical lenient guardrail. Google does not prescribe a single correct minimum.

2. **Strict / no-pooling** — label `PREM3_DIAGNOSTIC`. Not Meridian's effective fitted parameter count.

3. **Shadow complexity** — label `PREM3 SHADOW COMPLEXITY DIAGNOSTIC`. Foundational MMM evidence (extra effective complexity for media dynamics). Never an official Meridian blocker.

Interpretation of a lenient ratio around or below 10:

- `HIGH_PARAMETER_PRESSURE` or `SEVERE_PARAMETER_PRESSURE`
- `review_recommended=true`
- **cannot independently block `MODEL_READY`**

Never drop a confirmed confounder to improve the ratio.

---

## Limited spend range

Named feasibility dimension. Future diagnostics may compute min/max, quantiles, non-zero range, go-dark periods, relative spread, geo variation, and time variation.

Interpretation: limited observed support may constrain eventual extrapolation. Do not make ROI conclusions pre-fit.

---

## Structural "do not model yet"

PreM3 must be willing to conclude **MODELING IS CURRENTLY PROBLEMATIC** when evidence supports it, then guide the user.

Do not force every run toward `MODEL_READY`.

That conclusion is advisory unless an official contract/ERROR rule is also failing.

---

## Relationship to User Resolution Pack

| Feasibility signal | Issue family |
|---|---|
| Contract / nulls / grain / rates | `DATA DEFECT` |
| Missing geos, ragged panel, no pre-period export | `STRUCTURAL DATA GAP` |
| Short history, thin variation | `DATA SUFFICIENCY GAP` |
| High/severe parameter pressure | `PARAMETER PRESSURE` |
| Open causal questions | `CAUSAL CONTEXT GAP` |
| Knots / priors / final spec | `MODELER SPECIFICATION REVIEW` |
| Need better source extract | `SOURCE ACQUISITION GAP` |
