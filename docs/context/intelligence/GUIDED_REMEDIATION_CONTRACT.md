# PreM3 Guided Remediation — Response Contract

**Status:** advisory/response contract. Aligns with the existing PreM3 User Resolution Pack.  
**Version:** 1.0  
**Intelligence version:** 2.0.0

This mission does not rebuild `build_user_resolution_pack` or change EDA-gate runtime.

---

## Canonical issue response

When a meaningful problem is identified, organize the user-facing response as:

1. **WHAT I FOUND**
2. **WHY IT MATTERS**
3. **BEST PRACTICE**
4. **INSIGHT FROM YOUR DATA**
5. **WHAT PREM3 CAN DO**
6. **WHAT YOU SHOULD DO**
7. **MODELER REVIEW**
8. **NEXT STEP**

Use only the sections that add value. Do not dump the template on every short factual answer.

This is how **ASSESS / ADVISE / INSIGHT / GUIDE** appear together.

---

## Actor ownership

Recommended actions must identify who owns the next step.

| Actor | Typical ownership |
|---|---|
| `PREM3` | `AUTO_SAFE` repairs, official EDA execution, verification, interpretation packaging |
| `MARKETER` | campaign inactivity confirmation, budget-setting process, promotion/price intent |
| `ANALYST` | mapping confirmation, scope review, semantic classification |
| `DATA_ENGINEER` | re-export, grain alignment, missing geo/week recovery, source API gaps |
| `MODELER` | final treatment/control role, knots, priors, whether to proceed despite pressure |
| `SYSTEM_ADMIN` | permissions, worker/runtime identity, destination access |

Examples:

- "Google Ads export is missing 14 weeks." Owner: `DATA_ENGINEER` / `MARKETER`
- "Two channel mappings require semantic confirmation." Owner: `ANALYST`
- "Final treatment/control role remains ambiguous." Owner: `MODELER` / `ANALYST`

---

## Authority in the response

Best-practice text must disclose authority:

- Official Meridian requirement
- PreM3 best-practice recommendation
- Foundational MMM guidance
- Modeler judgment

Do not present everything with equal authority.

If verified run data exists, prefer run-specific insight over generic documentation.

---

## Example pattern (illustrative numbers only)

**WHAT I FOUND** — Your proposed national weekly model contains 91 usable KPI weeks.

**WHY IT MATTERS** — Available history is limited relative to the proposed model scope.

**BEST PRACTICE** — Longer history is generally preferred for national weekly MMM, although older history must still be structurally relevant. Authority: official planning guidance + heuristic interpretation.

**INSIGHT FROM YOUR DATA** — Relative to current channel/control scope, parameter pressure is high. *(Production numbers must come from tools.)*

**WHAT PREM3 CAN DO** — Calculate current parameter pressure and simulate how the diagnostic would change with additional periods or reduced scope. It will not silently drop channels or confounders.

**WHAT YOU SHOULD DO** — Check whether an additional 52–65 weeks can be exported from the KPI and media systems.

**MODELER REVIEW** — If additional history is unavailable, review channel/control scope before fitting. Do not drop a confirmed confounder to improve the ratio.

**NEXT STEP** — Rerun PreM3 after adding history or approving a scope change.

---

## Missing-media example (acceptance)

PreM3 does **not** immediately fill zero.

- **ASSESS** the missingness pattern.
- **ADVISE** inactivity vs unknown source absence.
- **INSIGHT** identify affected periods/channels.
- **GUIDE** how to confirm campaign inactivity or re-export source data.

---

## User Resolution Pack alignment

Issue families that should support this contract:

| Family | Typical owner | Agent-fixable? |
|---|---|---|
| `DATA DEFECT` | `DATA_ENGINEER` / `ANALYST` | sometimes `AUTO_SAFE` |
| `STRUCTURAL DATA GAP` | `DATA_ENGINEER` | no |
| `DATA SUFFICIENCY GAP` | `ANALYST` / `MARKETER` | no |
| `PARAMETER PRESSURE` | `MODELER` / `ANALYST` | no |
| `CAUSAL CONTEXT GAP` | `ANALYST` / `MODELER` | no |
| `MODELER SPECIFICATION REVIEW` | `MODELER` | no |
| `SOURCE ACQUISITION GAP` | `MARKETER` / `DATA_ENGINEER` | no |

Each family should eventually carry: evidence; why it matters; best-practice context; `agent_can_fix`; human owner; instructions; retry condition.

Retry condition should state when to rerun PreM3.

---

## Data acquisition guidance

When the right solution is better source data, say so. Examples:

- export additional weeks
- add missing geo breakdown
- retrieve campaign metadata
- export raw impressions rather than CTR
- obtain reach/frequency
- request promotion calendar
- request pricing history
- request inventory/distribution controls

Do not manufacture substitute data where the source can provide better data.

---

## Execution-path guardrail

Execution agents stay execution-focused. Do not append product marketing to a remediation response.
