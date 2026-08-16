# PreM3 Pre-Model Scope Scenarios — Specification

**Status:** contract only. Do not implement `simulate_model_scope_scenarios` in this mission.  
**Version:** 1.0  
**Intelligence version:** 2.0.0

---

## Purpose

Read-only scenarios calculate how a diagnostic would change if the proposed scope changed.

They support judgment. They do not mutate production input.

---

## Allowed scenario types

| Scenario | What it varies | Decision class if applied later |
|---|---|---|
| Additional history | more KPI/media periods | `USER_REQUIRED` (source export) |
| Additional valid geos | more complete geo coverage | `APPROVAL_REQUIRED` |
| Candidate channel consolidation | merge semantically compatible low-spend / low-variation channels | `APPROVAL_REQUIRED` |
| Different optional predictor scope | drop or add non-confounder predictors | `MODELER_REVIEW_REQUIRED` |
| Modeler-reviewed time complexity | different knot / time-effect complexity | `MODELER_REVIEW_REQUIRED` |

Forbidden autonomous applications:

- merge/drop channels
- drop a confirmed confounder
- change final `ModelSpec` knots or priors
- write a new production model-input table from a scenario

---

## Output philosophy

Allowed:

> If these two compatible candidate channels were consolidated, the diagnostic ratio would change from X to Y.

Not allowed:

> Therefore these channels should definitely be merged.

Numeric X and Y in production must come from tools, never from invented examples in agent prose.

---

## Candidate ranking (not action)

Channel consolidation candidates may be ranked using:

- low spend
- low exposure
- low variation
- shared taxonomy
- shared business purpose
- co-movement

Correlation alone cannot prove semantic compatibility. Final merge remains `APPROVAL_REQUIRED`.

---

## Guardrail

`PREM3-SCN-001` in `app/rules/intelligence_registry.yaml`:

- `decision_class`: `ADVISORY`
- `blocks_model_ready`: false
- `agent_can_fix`: false
- scenarios are read-only
