# Source Verification / Discrepancy Report

**Verification date:** 2026-08-16  
**Official package pin in this repo:** `google-meridian==1.8.0` (isolated EDA worker, Python 3.12)  
**Official install docs:** Python 3.11 or 3.12 required  
**Intelligence version:** 2.0.0

---

## A. Required discrepancy resolutions

### 1. Parameter ratio

**Previously too strong:** language that a ratio below 10 *must* reduce scope, treated as a hard rule.

**Official current framing** ([Amount of data needed](https://developers.google.com/meridian/docs/pre-modeling/amount-data-needed), [Perform EDA](https://developers.google.com/meridian/docs/pre-modeling/perform-eda)):

- `n_data_points = n_geos × n_times`
- `n_parameters = (n_geos - 1) + n_knots + n_controls + n_treatments`
- This lenient formula is what the EDA package uses.
- Strict/no-pooling is documented as a thought exercise / lower bound.
- Google "avoid[s] prescribing a single 'correct' minimum ratio."
- Official national example treats ~4 points/parameter as too low to estimate reliably and shows a scope+history illustration near ~15.
- Official guidance: do not remove important confounders.

**Resolution:** calculation is deterministic; ~10 interpretation is `MMM_EVIDENCE_HEURISTIC`; high/severe pressure sets `review_recommended=true`; **cannot independently block `MODEL_READY`.**

### 2. Missing media

**Official collect-data:** if media is missing *because a channel was inactive*, fill `0`.

**PreM3 refinement:** inactivity must be evidenced (`CONFIRMED_INACTIVE`). Unknown absence (failed export, API gap, missing geo, outage, excluded campaign, partial file) is not zero.

**Resolution:** not a contradiction. Meridian states the inactivity case. PreM3 refuses to assume inactivity.

### 3. KPI / control imputation

**Official collect-data:** do not zero-fill KPI/controls; use imputation techniques (forward-fill, interpolation, historical mean, etc.).

**PreM3 policy:** those techniques may be documented. Selection is `APPROVAL_REQUIRED`. Never `AUTO_SAFE` merely to satisfy completeness.

**Resolution:** Meridian requires a complete input and suggests methods. PreM3 does not autonomously choose a method.

### 4. VIF / correlation

**Official EDA defaults (re-verified 2026-08-16):** VIF `1000`; pairwise `|r|` `0.999`. Docs call these extreme and tunable via `EDASpec`.

**Resolution:** official defaults stay official. Any tighter PreM3 checks (e.g. VIF 50, `|r|` 0.95) are `PREM3 ADVISORY DIAGNOSTICS` and must not change golden `EDASpec` or be labeled official Meridian.

### 5. Model configuration / knots

**Official:** geo default can be `knots = n_times`; a time-only / national-level variable is collinear with time under full knots. Resolution is either `knots < n_times` or drop the time-only variable.

**Proven PreM3 fact:** Dataset A used a scoped EDA compatibility setting (`knots=130`) with `approved_for_final_modeling=false`.

**Resolution:** EDA compatibility ≠ final ModelSpec. Final knots/priors remain modeler-governed.

### 6. Technical version claims

| Claim | Status 2026-08-16 |
|---|---|
| Python 3.11 or 3.12 required | **Confirmed** — official installing page |
| Isolated worker Python 3.12 + `google-meridian==1.8.0` | **Confirmed** — repo pin / deployment docs |
| Public index may list a newer release | **Acknowledged** — do not treat index latest as proven pin |
| `DataFrameInputDataBuilder` | **Confirmed** as current DataFrame builder name in PreM3 domain context; load path still documented via DataFrame / `CoordToColumns` |
| `MeridianEDA`, `EDAOutcome`, `EDAFinding` | **Confirmed** — official API / EDA docs |
| `ModelSpec(knots=...)` not `n_knots` | **Confirmed** — official ModelSpec / EDA text |
| Population scaling is internal; do not pre-scale | **Confirmed** — input-data / collect-data guidance |
| Supported formats: CSV, Xarray, ndarray, DataFrame, DataFrame-convertible | **Confirmed** |
| No supported standalone `meridian` CLI | **Confirmed** in prior source manifest; not contradicted |

---

## B. Confirmed (keep)

- Completeness required before load
- Non-negative media
- Summable KPI and non-R&F media metrics
- Media and spend same dimensions
- Regular complete geo-time panel
- Time-constant variable is an official ERROR
- Paid / organic / R&F / non-media / control class split
- GQV optional; omitting it may create bias
- Seasonality dummies not required because of time-varying intercept
- Do not remove important confounders to improve the ratio
- Official ERROR blocks `MODEL_READY`; ATTENTION may allow review-recommended

---

## C. Changed in this mission (context only)

- Parameter-pressure hardness → heuristic + review recommended
- Missing media blanket zero → evidence-gated
- KPI/control imputation examples → approval-gated
- Three parameter views labeled with distinct authority
- Computational vs semantic readiness named
- Modeling feasibility named as broader than `MODEL_READY`
- Product intelligence and four behaviors made canonical
- Rule-registry design added without wiring new tools

---

## D. Unresolved / deferred

- Exact public PyPI latest vs `1.8.0` drift — track at next worker upgrade; do not change the pin here
- Whether official EDA HTML/API field names changed after 1.8.0 — not re-run in this context PR
- Future diagnostic tool implementations — next mission
- Attaching `intelligence_version` to live run manifests — deferred (would be a runtime schema change)

---

## E. Attestation for this PR

No PreM3 heuristic is represented as an official Meridian requirement.  
No parameter-pressure heuristic independently blocks `MODEL_READY`.  
No missing media value is assumed zero without inactivity evidence.  
No KPI or control imputation became `AUTO_SAFE`.  
No causal role is inferred from correlation alone.  
No confirmed confounder is dropped merely to improve parameter ratios.  
No channel consolidation became autonomous.  
No final modeling knots or priors became autonomous.  
No PreM3 diagnostic is labeled as an official Meridian EDA finding.  
No scope scenario mutates production data.  
No unsupported product ROI claim was introduced.  
No roadmap capability is represented as proven production behavior.  
No MEL runtime, Eventarc, or Ambient behavior was implemented.  
No BigQuery / EDA / `MODEL_READY` / remediation-tool runtime was changed.
