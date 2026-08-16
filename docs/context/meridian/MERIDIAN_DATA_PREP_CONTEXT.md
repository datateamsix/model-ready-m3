# PreM3 Meridian Pre-Modeling — Agent Context Library

**Purpose:** canonical domain reference for PreM3 execution, pre-EDA diagnostics, semantic readiness, and modeler handoff for Google Meridian.
**Scope:** data preparation through verified model-consumption input, pre-modeling diagnostics, official Meridian EDA context, semantic/causal readiness, and handoff guidance. This file does **not** authorize final model specification, posterior sampling, ROI interpretation, or budget optimization.
**Companion file:** `MERIDIAN_ADVISOR_PLAYBOOK.md` — how PreM3 explains, advises, surfaces insights, asks causal questions, and guides users through remediation.
**Product context:** `PREM3_PRODUCT_CONTEXT.md` — why PreM3 exists, who it serves, value proposition, proof, and product boundaries.
**Context version:** 2.0 (PreM3 intelligence alignment)
**Last verified against docs:** 2026-08-16. Re-verify temporally sensitive package/API claims before production changes.  
**Intelligence version:** 2.0.0  
**Boot context:** `PREM3_MMM_BOOT_CONTEXT.md` — load this long file only on execution/readiness paths.

---

## 0. How to use this document

This is a **domain reference**, not a free-form prompt and not a substitute for deterministic tools. When the answer can be calculated from the verified run data, PreM3 should calculate it.

### 0.1 Knowledge authority

| Class | Meaning | Typical use |
|---|---|---|
| `MERIDIAN_NORMATIVE` | Official Meridian/library requirement or official EDA behavior | May support hard gates where Meridian itself does |
| `PREM3_DETERMINISTIC_DIAGNOSTIC` | Objective quantity calculated from the actual run | Evidence; interpretation may still be advisory |
| `MMM_EVIDENCE_HEURISTIC` | Evidence-backed guidance that is not an official Meridian blocker | Review, advice, scenario analysis |
| `MMM_JUDGMENT` | Requires business, causal, or modeling judgment | Human/modeler decision |

### 0.2 Action authority

Knowledge authority and action authority are separate. Use these decision classes:

`AUTO_BLOCK` · `AUTO_SAFE` · `ADVISORY` · `APPROVAL_REQUIRED` · `MODELER_REVIEW_REQUIRED` · `USER_REQUIRED`

**Foundational rule:** a deterministic calculation does not automatically grant autonomous decision authority.

Validated experiential patterns may later augment preparation behavior through `DOMAIN_VIEW`. They cannot override official Meridian requirements, causal guardrails, missingness safety policy, or human-required semantic decisions. Unpromoted observations are not domain knowledge.

### 0.3 Binding hierarchy

| Section | Status | Behavior |
|---|---|---|
| §2 Meridian / PreM3 hard requirements | Binding | Abort or route to resolution when the required contract cannot be satisfied |
| §3–§7 Design guidance | Strong defaults / heuristics | Follow unless evidence or an approved decision supports a deviation; log it |
| §8 Diagnostics + official EDA boundary | Mixed authority | PreM3 diagnostics are evidence; official Meridian `ERROR` owns the EDA block |
| §9–§10 Causal judgment / failure modes | Advisory or human-required | Surface the question or resolution path; do not decide silently |

**Core framing that governs every ambiguous call:** Meridian is a *causal inference* tool, not a forecasting tool. When a preparation choice trades predictive convenience against causal validity, preserve causal validity. Predictive usefulness alone is not sufficient justification for a variable.

### 0.4 The five evidence sources PreM3 must distinguish

1. What official Meridian documentation requires.
2. What the actual verified data proves.
3. What official Meridian EDA finds.
4. What PreM3/Gemini interprets from evidence.
5. What only a human can tell us about business and causal process.

Never collapse these into one source of truth.

---

## 1. Target artifact

### 1.1 Physical shape

One tidy table, one row per `(geo, time)`, wide across variables.

```
time | geo | population | kpi | revenue_per_kpi | <controls...> | <ch>_impression | <ch>_spend | ...
```

For national models, drop `geo` and `population` (single geo, nominal population 1.0).

### 1.2 Accepted formats

CSV, Xarray Dataset, NumPy ndarray, Pandas DataFrame, or anything convertible to a DataFrame (xlsx, Parquet, BigQuery result set).

- CSV → `load.CsvDataLoader` + `load.CoordToColumns`
- DataFrame → `data_frame_input_data_builder.DataFrameInputDataBuilder`
- ndarray → `nd_array_input_data_builder.NDArrayInputDataBuilder`
- Xarray → `load.XrDatasetDataLoader` with `name_mapping`

### 1.3 The column-mapping contract

Column names are free-form; the loader maps them. But the mapping must be *complete and consistent*, so emit it alongside the data.

```python
coord_to_columns = load.CoordToColumns(
    time='time',
    geo='geo',
    controls=['GQV', 'Discount', 'Competitor_Sales'],
    population='population',
    kpi='conversions',
    revenue_per_kpi='revenue_per_conversion',
    media=[f'{c}_impression' for c in channels],
    media_spend=[f'{c}_spend' for c in channels],
)
media_to_channel       = {f'{c}_impression': c for c in channels}
media_spend_to_channel = {f'{c}_spend': c for c in channels}
```

**Naming convention to enforce** (not required by the library, but it makes the mapping dicts generable and diffable):
`{Channel}_impression` / `{Channel}_reach` / `{Channel}_frequency` / `{Channel}_spend`, one `{Channel}` token shared across all four.

For Xarray, the required coordinate names are `geo`, `time`, `control_variable`, `media_channel`; required data variable names are `kpi`, `revenue_per_kpi`, `controls`, `population`, `media`, `media_spend`.

### 1.4 Variable classes Meridian distinguishes

| Class | Spend? | Intervenable? | Gets ROI? | Notes |
|---|---|---|---|---|
| Paid media | Yes | Yes | Yes | Needs exposure metric **or** reach+frequency, plus spend |
| Paid media w/ R&F | Yes | Yes | Yes | Reach + frequency instead of single metric |
| Organic media | No | Yes | Contribution only | Newsletters, blog, social posts, email |
| Organic R&F | No | Yes | Contribution only | |
| Non-media treatment | No | Yes | Contribution only | Price, promo, packaging change |
| Control | No | **No** | No | Confounders and strong predictors only |

The paid/organic/non-media/control split is not cosmetic — it decides whether a variable gets a causal effect estimate and whether it appears in budget optimization. Misclassification is a silent correctness bug, not a formatting one.

---

## 2. Hard rules — violation means abort

1. **No missing values, anywhere.** Meridian requires a complete dataset. `NaN` must be resolved before load. (Resolution policy differs by class — see §6.)
2. **All media values non-negative.**
3. **KPI and media metrics must be summable across geo and time.** Sums must be arithmetically meaningful. Rates, ratios, averages, percentages are forbidden as KPI or media metrics: CTR, CPC, CPM, ROAS, conversion rate, AOV. If the source exports a rate, reconstruct the volume (`clicks = impressions × CTR`) and supply that.
   - **Exception:** summability does *not* apply to R&F channels. Frequency is an average by construction.
4. **Media and media_spend must have identical dimensions.** Same geos, same time periods, same channel count and order.
5. **The time grid must be strictly regular and complete** — every geo has every period, same increment throughout. Weekly means exact 7-day steps.
6. **Every geo covers the full time range.** Ragged panels are not accepted.
7. **No variable may be constant across time.** In a geo model a time-constant variable is perfectly collinear with the geo main effect `τ_g`; in a national model it is a constant with no signal. Either triggers an `ERROR` and blocks sampling.

### 2.0 Hard-rule authority audit

| Rule | Classification | Notes |
|---|---|---|
| Completeness (no NaN in modeled input) | `MERIDIAN_NORMATIVE` | How to resolve missingness is policy, not a single fill rule |
| Non-negative media | `MERIDIAN_NORMATIVE` | |
| Summable KPI / non-R&F media | `MERIDIAN_NORMATIVE` | |
| Media and spend identical dimensions | `MERIDIAN_NORMATIVE` | |
| Regular complete time grid / full geo coverage | `MERIDIAN_NORMATIVE` | |
| No time-constant modeled variable | `MERIDIAN_NORMATIVE` | Official EDA ERROR |
| Campaign → channel aggregation | `DESIGN_DEFAULT` | Not permission to sum arbitrary overlapping campaigns |
| Weekly grain preference | `DESIGN_DEFAULT` | Official best practice, not a loader hard-fail |
| History baselines (2y geo / 3y national) | `MMM_EVIDENCE_HEURISTIC` / official planning guidance | Not a `MODEL_READY` gate |
| ~10 observations/parameter | `MMM_EVIDENCE_HEURISTIC` | Cannot independently block `MODEL_READY` |
| Media zero-fill | `MERIDIAN_NORMATIVE` only for confirmed inactivity; else `PREM3_POLICY_BLOCKER` | Unknown absence ≠ 0 |
| KPI/control imputation method | `MMM_JUDGMENT` + `APPROVAL_REQUIRED` | Completeness is normative; method choice is not AUTO_SAFE |

Do not call guidance "hard" unless its authority warrants it.
---

### 2.1 Strong default — campaign reporting should resolve to modeled channel definitions

PreM3 should normally aggregate compatible campaign rows into stable channel-level treatment definitions before handoff. This is a **design default**, not permission to sum arbitrary campaign data. Verify mutual exclusivity, metric summability, taxonomy, and business meaning first. If campaign/sub-channel separation is genuinely required for the modeling question, treat that as a scope/modeler decision rather than an automatic data-prep choice.

---

## 3. Grain

### 3.1 Time grain

**Weekly is the default and the recommendation.** It balances variation against noise.

- Daily: permitted; substantially longer runtime; noisier.
- Monthly: permitted but discouraged — expect non-convergence or very wide credible intervals. If monthly is all that exists, require ≥3 years.
- Pick one week-start convention (e.g. Monday) and apply it to every source before joining. Mixed week conventions across sources is a top-3 real-world defect.

### 3.2 Geo grain

**Geo-level is strongly preferred when the available geographic detail is reliable and relevant.** The advantages can be structural:

- Larger effective sample size via pooling
- Tighter credible intervals
- Better time-effect estimation (multiple observations per period, supports more knots)
- **More variation in spend** — critical for identifying saturation/Hill parameters
- **Reduced omitted-variable bias**, because geo variation decorrelates media from national confounders

If some channels are geo-level and others national-only, population allocation can preserve a geo model when the assumption is defensible (§6.2). Treat this as a documented design option rather than an automatic transformation, and surface the loss of independent geo variation to the modeler.

### 3.3 Geo selection

- Small/low-signal geos can deserve scope review because they may add noise relative to the information they contribute. Do not drop them automatically.
- A **top 50–100 US DMA** scope is a practical rule of thumb, not a universal Meridian hard requirement. Evaluate actual KPI/population coverage.
- Prefer an explicit geo-inclusion rationale over arbitrary aggregation. Excluding or aggregating geos changes the modeling population and remains a scope/modeler decision.
- Note for the modeler: control variables like temperature do not aggregate by summing. Media metrics generally do.

### 3.4 Pre-period media (the `media_time` extension)

Media (paid and organic) may carry **extra earlier time periods than the KPI** — indices `t < 1` — so adstock is correctly initialized at the start of the modeling window. If absent, Meridian assumes zero media execution before `t=1`, which biases early-period effects.

**Practical guidance:** pull enough earlier media/spend to cover the intended carryover window. Where the intended `max_lag` is known, align the pre-period to it. An 8–13 week planning range is common in MMM practice, but it is not a universal Meridian hard rule and should not be silently promoted into final model configuration.

---

## 4. Timeframe

| Model type | Planning baseline | Preferred planning range |
|---|---|---|
| Geo, weekly | ~2 years (104 wk) | 2–3 years |
| National, weekly | ~3 years (156 wk) | 3+ years |
| Monthly (any) | ~3 years | more |

Treat these as planning guidance, not a substitute for the actual parameter-pressure, variation, and structural-break assessment.

Longer is not strictly better: "Adding more data will reduce the variance in inference, but might make the inference less relevant." Structural breaks (rebrand, pandemic, channel launch, measurement change) argue for a shorter, more relevant window. Flag suspected breaks rather than silently extending history.

---

## 5. How many columns — the parameter budget

This is the question the agent must be able to answer numerically, not by feel.

### 5.1 Meridian's ratio (lenient / EDA package)

```
n_data_points = n_geos × n_times
n_parameters  = (n_geos - 1) + n_knots + n_controls + n_treatments

ratio = n_data_points / n_parameters
```

`n_treatments` = paid media + paid R&F + organic media + organic R&F + non-media treatments.
This assumes **perfect pooling** across geos and is deliberately lenient — a guardrail against severe under-determination, not a target.

### 5.2 The strict (no-pooling) counterpart

```
n_parameters_strict = (n_treatments × n_geos) + (n_controls × n_geos) + n_knots + (n_geos - 1)
```

Meridian's worked example: 105 geos × 156 weeks = 16,380 points; 12 media, 6 controls, 100 knots →
- strict: 2,094 params → **~8 points/param**
- lenient: 222 params → **~74 points/param**

Because Meridian uses partial pooling, the true effective ratio sits between the two. Google deliberately declines to prescribe a single minimum: "The only way to determine the hierarchical variance parameters (`eta_m` and `xi_c`) is by actually fitting the model."

### 5.3 National models — no pooling to rescue you

Every effect is an independent parameter. Google's worked example illustrates the pressure clearly: 12 media + 6 controls + 8 knots = 26 params against 104 weekly points = **4 points/param**. The example improves the diagnostic to roughly 15 points/parameter by reducing scope and extending history. Treat that as an illustration of improved information-to-complexity, not as a guarantee that the resulting model will be statistically or causally adequate.

### 5.4 Independent benchmarks for "points per parameter"

| Source | Guidance |
|---|---|
| Chan & Perry (Google, 2017) | "A rule-of-thumb for a minimum number of data points for a stable linear regression... are **7–10 data points per parameter**, of which typical MMMs fall short." |
| Meta Robyn | "**1 independent variable : 10 observations**"; minimum 2 years weekly |
| Chan & Perry, on adstock+saturation | "To adequately model a lagged effect and a diminishing return might require **3–4 parameters for each channel**" |

The 3–4 params/channel point matters: Meridian's ratio formula counts one parameter per treatment and explicitly says it ignores Adstock and Hill parameters "for simplicity." A conservative agent should compute a **shadow ratio** that charges 3 params per media channel, and report both.

### 5.5 Practical parameter-pressure interpretation

Derived from the sources above:

- Compute the lenient ratio, the strict diagnostic, and the conservative shadow ratio for the proposed scope.
- Treat a lenient ratio around or below 10 as **high parameter pressure / review recommended**, not as an official Meridian hard blocker. The numeric calculation is deterministic; the interpretation is an `MMM_EVIDENCE_HEURISTIC`.
- Generate **read-only scope scenarios** rather than silently changing the model input. Candidate scenarios include: consolidating semantically compatible low-spend channels, extending history, adding valid geo granularity, reviewing optional predictors, or evaluating modeler-governed time-complexity choices.
- Channel consolidation, channel removal, control removal, and final knot choices are not `AUTO_SAFE`.
- Never drop a genuine confounder merely to improve a ratio. Under-controlling is a bias problem; over-parameterizing is primarily a variance/identifiability problem.

A run may still reach `MODEL_READY` while carrying `HIGH_PARAMETER_PRESSURE` and `review_recommended=true` if the actual hard contract and official Meridian EDA gate pass.

### 5.6 Low-spend channels

Low spend share is a **scope-review signal**, not an automatic removal rule. The EDA report surfaces the bottom channels by spend share to support review, but the documentation does not provide a universal percentage cutoff. PreM3 may rank consolidation candidates using spend share, exposure share, variation, taxonomy, and business purpose; any merge/drop remains `APPROVAL_REQUIRED` or `MODELER_REVIEW_REQUIRED`.

---

## 6. Missing data policy

Meridian requires complete model inputs, but **missing does not mean zero**. Resolve missingness by variable class and by evidence.

| Class | PreM3 policy | Action authority |
|---|---|---|
| **Media / spend** | Fill `0` **only when source evidence supports channel inactivity at that geo-time grain**. Unknown absence may indicate a broken export, missing geo, reporting gap, excluded campaign, or other source defect. | Confirmed inactivity may be `AUTO_SAFE`; unknown absence is `USER_REQUIRED` / source investigation |
| **KPI** | Never zero-fill merely to satisfy completeness. Candidate imputation techniques may be discussed, but choosing one changes the observed outcome series. | `APPROVAL_REQUIRED` |
| **Controls** | Never zero-fill by default. Candidate interpolation/fill methods require causal and source semantics. | `APPROVAL_REQUIRED` |
| **Non-media treatments** | Resolve by meaning. A missing promo flag may plausibly represent no promotion; a missing price cannot mean price `0`. | `APPROVAL_REQUIRED` unless semantics are explicitly established |
| **Reach / frequency** | When inactivity is confirmed, reach `0` and frequency `0` are the dark-period convention. Unknown absence still requires investigation. | Conditional `AUTO_SAFE` only with inactivity evidence |

### 6.1 Missingness evidence classes

Use explicit evidence labels where practical:

- `CONFIRMED_INACTIVE`
- `LIKELY_SOURCE_GAP`
- `UNKNOWN`
- `KPI_MISSING`
- `CONTROL_MISSING`
- `TREATMENT_SEMANTIC_REQUIRED`

PreM3 should preserve the evidence that justified any fill or imputation decision in provenance and the run manifest.

### 6.2 National-only channels in a geo model

Impute down to geo. Documented method: allocate the national value to each geo **in proportion to that geo's share of total population**. Accurate geo data is preferable, but imputation still yields useful parameter information (see Sun et al. 2017 §4.4).

Caveat for the agent: a population-allocated national variable **does not vary across geos**. If full time-effect complexity creates perfect collinearity, flag an `EDA_COMPATIBILITY_CONFIGURATION` / modeler-review issue. A scoped EDA compatibility setting may be used where already proven, but **final knot selection and final ModelSpec remain modeler-governed**. Do not automatically drop the variable or promote an EDA-only setting into final modeling policy.

---

## 7. Aggregation

### 7.1 Campaign → channel

Group by `(week_start, geo)` and **sum** spend and the execution metric across all campaigns in the channel.

**Assumption this makes:** campaigns are mutually exclusive — every impression, click, and dollar belongs to exactly one campaign, no overlap or double counting. Verify before summing; overlapping audience/retargeting structures can double-count.

### 7.2 Choosing the media execution metric

Per paid channel, supply spend **plus exactly one of**:
- a single exposure metric (impressions, clicks), **or**
- reach + frequency.

Preference order: impressions > clicks > spend-as-proxy.

**Spend as exposure proxy is a documented trap.** If spend stands in for exposure, the model reads high-cost periods as high-volume periods. When CPMs spike during competitive windows, real impressions may be flat while spend rises — producing wrong effectiveness estimates. Use it only when no volume metric exists, and flag it in the manifest.

### 7.3 Reach and frequency specifics

- Must be at the **same geo and time grain** as KPI and controls.
- Reach = unique individuals exposed **within each period** — *not* cumulative reach across consecutive periods. De-duplicating across weeks is a common upstream error; check that weekly reach does not monotonically increase.
- Frequency = total impressions ÷ reach, for that period.
- R&F channels are exempt from the summability rule.

### 7.4 Geo → national (if building national)

Sum media units, organic units, reach, and KPI across geos. For frequency: sum RF impressions (reach × frequency) and sum reach across geos, then divide totals. Do not average frequencies.

Binary or rate-type controls may need `mean` rather than `sum` — Meridian's EDA exposes `AggregationConfig(control_variables={'rating': np.mean})` for exactly this.

---

## 8. PreM3 diagnostics and official Meridian EDA

PreM3 should run cheap deterministic checks before constructing the Meridian object, then run **official Meridian EDA** against the independently verified model-consumption input. Keep provenance separate:

- `PREM3_PRE_EDA_DIAGNOSTIC` — locally computed evidence or mirrored fail-fast check.
- `OFFICIAL_MERIDIAN_EDA_FINDING` — produced only by the official Meridian EDA package.

Do not call a PreM3 diagnostic an official Meridian finding. Where a local check mirrors an official default, record the Meridian version/source and the threshold authority.

### 8.1 PreM3 mirrored ERROR prechecks — fail fast

| Check | Threshold | Fix |
|---|---|---|
| Any null in any modeled column | any | §6 policy |
| KPI transformed std dev | < 1e-4 | No signal. Check inputs; reconsider feasibility. |
| Variable constant across time | std ≈ 0 | Drop the variable. |
| Variable constant across geo **and** `knots = n_times` | — | Set `knots < n_times` or drop. |
| Pairwise correlation between any two treatments/controls | \|r\| > 0.999 | Remove one; they are redundant. |
| VIF (across geos+times, or across times for national) | > 1000 | Drop or combine linear-combination variables. |
| Negative media value | any | Source error. |
| media vs media_spend dimension mismatch | any | Realign. |

### 8.2 ATTENTION — warn and surface

| Check | Threshold | Meaning |
|---|---|---|
| Spend > 0 with media units = 0, or vice versa | any occurrence | Spend/exposure inconsistency |
| Cost per media unit outlier | outside `Q1 − 1.5×IQR` … `Q3 + 1.5×IQR` | Likely data entry error |
| Outliers in any scaled variable | IQR rule | Verify genuineness |
| Variable std dev → 0 after removing outliers | — | Sparsity: variable only varies *because of* outliers. Common with go-dark periods. |
| Per-geo VIF | > 1000 | Geo-specific collinearity |
| Per-geo pairwise correlation | \|r\| > 0.999 | |
| Low channel spend share | bottom 5 by spend | Combine candidates |

Thresholds are tunable via `EDASpec` (`VIFSpec`, `PairwiseCorrSpec`, `KpiInvariabilitySpec`, `StandardDeviationSpec`). The 1000 VIF / 0.999 correlation defaults are deliberately extreme and catch near-perfect redundancy. If PreM3 later adds tighter checks such as VIF 50 or correlation 0.95, classify them as **optional `MMM_EVIDENCE_HEURISTIC` / PreM3 advisory diagnostics**, not official Meridian defaults, and do not silently change the golden EDA configuration.

### 8.3 INFO — review, don't block

| Check | Expectation |
|---|---|
| Spearman corr(geo population, raw media units / raw reach) | Should be **positive**. Low or negative → data error. |
| Spearman corr(population, scaled paid/organic media) | High → the variable may already be population-scaled upstream. Check the pipeline. |
| Spearman corr(population, scaled controls/non-media) | High → should probably set `control_population_scaling_id` / `non_media_population_scaling_id`. |
| R² of variable ~ geo (categorical) | High → low time variation → weakly identifiable |
| R² of variable ~ time (categorical) | High → low geo variation → problematic with many knots |

### 8.4 Running official Meridian EDA

```python
from meridian.model import model
from meridian.model.eda import meridian_eda

mmm = model.Meridian(input_data=data, model_spec=spec)
mmm_eda = meridian_eda.MeridianEDA(mmm)
mmm_eda.generate_and_save_report(filename=fname, filepath=fpath)
```

The official EDA package requires a constructed `Meridian` object. In PreM3's proven architecture, the final EDA pass should read the **independently verified BigQuery model-consumption input**, verify its fingerprint, construct the Meridian input in the isolated EDA worker, and persist official structured findings plus the untouched official HTML report.

Official `ERROR` findings block `MODEL_READY`. `ATTENTION` findings may permit `MODEL_READY` with `review_recommended=true`. PreM3/Gemini may interpret findings but may not alter their severity or provenance.

---

## 9. Variable classification — the part that requires judgment

This is where data prep stops being mechanical. Misclassification here biases the ROI estimates the whole exercise exists to produce.

### 9.1 The three roles

- **Confounder** — causally affects both the treatment and the KPI. **Include as control.** Omitting it biases causal estimates.
- **Predictor** — affects KPI only. **Include selectively.** Reduces variance; does nothing for bias. Too many inflate variance and raise misspecification risk.
- **Mediator** — sits on the causal path between treatment and KPI (treatment → mediator → KPI). **Exclude.** Including it biases the treatment's causal estimate.

### 9.2 The practical elicitation heuristic

Enumerating everything that affects KPI is impossible; enumerating what affects *media decisions* is tractable — and most things that drive media decisions also drive KPI, making them confounders. Questions to put to the marketing planner:

1. How was total budget set annually/quarterly?
2. How was allocation across channels decided?
3. Within a year, how were high vs low budget weeks chosen?
4. Do spend spikes correspond to holidays, launches, events?
5. What data sources correlate with those decisions (prior-year KPI, economic indicators)?
6. Was there organic media, and what drove the decision to run it?
7. Were there non-media treatments (price changes, promos), and how were they timed?

An agent cannot answer these from data alone. It should **produce the questionnaire and surface unanswered items as open risks** rather than guessing.

### 9.2.1 Semantic readiness interview

PreM3 should treat these unanswered business-process questions as **semantic readiness**, distinct from computational readiness. The interview must be generated from the actual variables, channels, and patterns present in the run rather than delivered as a generic questionnaire.

Each open causal question should capture:

- the question;
- why PreM3 is asking;
- the evidence/pattern that triggered it;
- the possible causal concern;
- affected variables/channels;
- what changes depending on the answer;
- required human role;
- whether it blocks the current input or only requires modeler review.

Canonical examples:

**Promotion timing** — Were promotions scheduled independently, or deliberately coordinated with media campaigns?  
Why: promotion may be a treatment/confounder in one process and partly a mediator in another.

**Search demand / GQV** — Did upper-funnel campaigns materially drive branded search or query volume?  
Why: query volume may confound paid search while mediating upper-funnel effects.

**Budget timing** — How were high-spend weeks selected?  
Why: if expected demand influenced budget timing, an omitted demand signal may affect both treatment and KPI.

**Remarketing / targeting** — Was remarketing volume created by prior intent or visits generated by other channels?  
Why: downstream treatment and selection-bias risk.

Correlation or timing patterns may **trigger** these questions; they do not answer them.

### 9.3 Standard control candidates

Competitor activity/sales, price (with the caveat below), distribution, promotions, macroeconomic indicators, weather, category sales, Google Query Volume.

### 9.4 Seasonality — usually do *not* add columns

Meridian handles trend and seasonality through the **time-varying intercept** (knots). Separate seasonality/holiday dummies are **not required** and consume parameter budget. Only add them if automatic seasonality adjustment has been deliberately disabled.

This is a meaningful difference from Robyn (which does Prophet-based trend/season/holiday decomposition). Do not port a Robyn control set over unchanged.

### 9.5 Google Query Volume — the unresolvable case

GQV is a **confounder for search ads** (a query typically precedes a search ad) but a **mediator for upper-funnel media** (TV drives searches). One model, one decision.

Google's own lean: **treat it as a confounder and include it**, because the query↔search-media relationship is strong. But the decision depends on which channels most need unbiased estimates. Note that GQV is optional — omitting it "might create bias" but the model runs. GQV from the MMM Data Platform arrives *indexed* rather than raw; that is fine, since scaling a control doesn't affect fit.

### 9.6 Mediator traps to check for explicitly

- **Funnel effects:** TV → search queries → paid search clicks. Putting exogenous and downstream channels in one additive regression biases the upstream channel. "Downstream ads should not be included with exogenously-determined ads in a single regression equation."
- **Price set in response to own advertising:** if discounts are timed to support campaigns, price is partly a mediator, and controlling for it does not properly control.
- **Site visits driving remarketing volume:** the visits are downstream of other media.

Flag these; do not resolve them silently.

### 9.7 Lagged controls

Include `Z_{t-1} … Z_{t-L}` **only if** the lagged values plausibly have a causal effect on KPI at `t`. If controls have no lagged effect (only treatments do), lagged controls are unnecessary by the backdoor criterion. Truncate `L` to avoid inflating variance; ignoring weak lagged effects is a defensible bias-variance trade.

### 9.8 Population scaling — what the agent must NOT do

Meridian scales internally. Do not pre-scale.

| Variable | Default internal scaling |
|---|---|
| KPI | ÷ population, then centered/standardized (mean 0, sd 1) |
| Paid & organic media | ÷ population, then ÷ median non-zero value per channel |
| Reach | same as media |
| Controls | standardized; **not** population-scaled by default |
| Non-media treatments | standardized; **not** population-scaled by default |

Two consequences for data prep:
1. **Supply raw units.** Pre-scaled inputs will be double-scaled. The EDA population-correlation check exists to catch exactly this.
2. A documented escape-hatch transformation can alter how a variable behaves under internal population scaling, but PreM3 should **not apply it autonomously** merely because a diagnostic fires. Treat it as `MODELER_REVIEW_REQUIRED` unless an approved rule already exists.

Population-scaling controls (competitor impressions, etc.) is configured in `ModelSpec`; final model configuration remains outside autonomous PreM3 authority. EDA compatibility context may be surfaced without promoting it into final modeling policy.

---

## 10. Known failure modes

Ranked by how often they appear in practice.

1. **Mixed week-start conventions across sources.** Silent. Produces phantom lag structure.
2. **No pre-period media**, so adstock starts cold. Silent. Biases early periods.
3. **Rates fed as metrics** (CTR, CPC, ROAS). Caught by summability, but only if checked.
4. **Cumulative reach** instead of per-period reach. Silent and severe.
5. **Zero-filled KPI or controls.** Skews baseline; looks like clean data.
6. **Pre-scaled media** hitting Meridian's internal scaler. Double scaling.
7. **Campaign-level rows** left unaggregated, or overlapping campaigns double-counted.
8. **Too many channels** relative to data. Wide credible intervals read as "inconclusive model" rather than "under-determined data."
9. **Correlated spend across channels.** Advertisers move budgets together; the model then cannot separate them. Chan & Perry: many response surfaces fit equally well and "the estimated relationship can change radically due to small changes in the data or the addition or subtraction of seemingly unrelated variables."
10. **Limited spend range.** Extrapolation to "what if I double spend" or "what if I go to zero" is unsupported by the data. Marginal ROI may be fine while average ROI is poor.
11. **Selection bias from targeting.** Remarketing and paid search target already-interested users. Without a demand proxy, the model credits the ad for pre-existing intent.
12. **Unclear SKU↔campaign mapping.** Advertising runs at brand level, sales data at SKU level. Assignment is "partially subjective and could lead to error through under- or over-attributing."

### 10.1 Failure-mode metadata

| Failure mode | detectable_from_data | pre_eda_possible | requires_business_context | agent_can_fix | decision_class | knowledge_class |
|---|---|---|---|---|---|---|
| Mixed week starts | PARTIAL | yes | no | sometimes | `APPROVAL_REQUIRED` / `AUTO_SAFE` if unambiguous | `MERIDIAN_NORMATIVE` / policy |
| Missing pre-period media | PARTIAL | yes | yes | no | `USER_REQUIRED` | `MMM_EVIDENCE_HEURISTIC` |
| Rates as additive media | YES | yes | no | no if no components | `AUTO_BLOCK` / reconstruct | `MERIDIAN_NORMATIVE` |
| Cumulative reach | PARTIAL | yes | no | no | `USER_REQUIRED` | `MERIDIAN_NORMATIVE` |
| KPI/control zero-fill | YES if applied | yes | yes | no | `APPROVAL_REQUIRED` | policy |
| Double population scaling | PARTIAL | yes | no | no | `MODELER_REVIEW_REQUIRED` | `MERIDIAN_NORMATIVE` |
| Campaign aggregation errors | PARTIAL | yes | yes | no if overlap unknown | `APPROVAL_REQUIRED` | `DESIGN_DEFAULT` |
| Excess channel complexity | YES | yes | yes | no | `ADVISORY` | `MMM_EVIDENCE_HEURISTIC` |
| Correlated spend | YES | yes | yes | no | `ADVISORY` | diagnostic + judgment |
| Limited spend range | YES | yes | no | no | `ADVISORY` | diagnostic |
| Selection bias / targeting | NO / PARTIAL | trigger only | yes | no | `MODELER_REVIEW_REQUIRED` | `MMM_JUDGMENT` |
| Unclear product/campaign mapping | PARTIAL | no | yes | no | `USER_REQUIRED` | `MMM_JUDGMENT` |

Recommended resolution pattern for all rows: guided remediation (`WHAT I FOUND` … `NEXT STEP`).

---

## 11. Implementation notes (Python / GCP)

- Re-verify Python/package/API compatibility against the exact Meridian version used by the current deployment before changing runtime requirements. The repository and deployed isolated EDA worker are the operational source of truth.
- Keep the official Meridian dependency isolated from the ADK runtime where the current architecture already does so.
- BigQuery is the model-consumption layer, not merely staging: build the explicit schema, write a versioned table, independently read it back, verify physical/data parity, and expose the stable Meridian-facing endpoint before the official EDA pass.
- Suggested PreM3 pipeline:  
  `extract → conform grain → classify → aggregate → resolve approved missingness → deterministic validation → manifest → BigQuery publish → independent BigQuery verification → PreM3 pre-EDA diagnostics → official Meridian EDA → PreM3 interpretation → user/modeler handoff`.
- **Emit auditable run metadata**: geo list and exclusions, time window/grain, channel definitions/source campaigns, variable classification and rationale, missingness decisions/evidence, exposure-metric choice, parameter diagnostics (lenient/strict/shadow), pre-period coverage, scope-review signals, semantic-readiness status, open causal questions, and threshold/source authority.
- Do not duplicate the full official EDA report inside the manifest. Link to the official EDA receipt/artifact and preserve source provenance.
- Google's MMM Data Platform remains an important source option for Google media inputs; source-specific guidance should be re-verified when the platform changes.

---

## 12. PreM3 readiness and advisory output model

PreM3 should keep four user-value behaviors distinct:

1. **ASSESS** — establish state, defects, contract readiness, and modeling-feasibility signals.
2. **ADVISE** — explain official requirements and evidence-backed MMM best practice with source authority.
3. **INSIGHT** — turn actual run calculations and official EDA evidence into run-specific interpretation without overstating causality.
4. **GUIDE** — tell the user what PreM3 can fix, what data/context the user must provide, what requires modeler review, and the exact retry/handoff condition.

### 12.1 Computational readiness vs semantic readiness

**Computational readiness** is what PreM3 can establish objectively from the verified data: grain, history, missingness, variation, parameter pressure, spend distribution, pre-period media, collinearity, geo coverage, population relationships, and similar evidence.

**Semantic readiness** is what the table cannot establish: why budgets changed, whether promotions were coordinated with campaigns, whether branded search is upstream or downstream for specific media, whether targeting reflects prior intent, and other causal/business-process facts.

### 12.2 Modeling feasibility vs `MODEL_READY`

`MODEL_READY` is the verified pre-modeling contract plus official Meridian EDA gate. **Modeling feasibility** is a broader advisory assessment. A run may be `MODEL_READY` and still carry `HIGH_PARAMETER_PRESSURE`, limited spend range, or unresolved modeler-review questions.

### 12.3 Canonical issue response

For any material problem, the advisory layer should be able to organize the response as:

- **WHAT I FOUND**
- **WHY IT MATTERS**
- **BEST PRACTICE**
- **INSIGHT FROM YOUR DATA**
- **WHAT PREM3 CAN DO**
- **WHAT YOU SHOULD DO**
- **MODELER REVIEW**
- **NEXT STEP**

This is guidance, not permission to override decision authority.

### 12.4 User Resolution Pack issue families

Align material issues to:

`DATA DEFECT` · `STRUCTURAL DATA GAP` · `DATA SUFFICIENCY GAP` · `PARAMETER PRESSURE` · `CAUSAL CONTEXT GAP` · `MODELER SPECIFICATION REVIEW` · `SOURCE ACQUISITION GAP`

Each family needs evidence, why it matters, best-practice context, `agent_can_fix`, human owner, instructions, and retry condition. See `docs/context/intelligence/GUIDED_REMEDIATION_CONTRACT.md`.

### 12.5 Computational readiness dimensions

Where applicable, computational readiness includes: data shape; grain; calendar continuity; history; geo coverage; missingness; media/spend consistency; parameter pressure; channel spend shares; variation; spend range; pre-period media; collinearity; population relationships; R&F structure; aggregation evidence.

---

## 13. Sources

### Tier 1 — normative (Meridian documentation)

| Topic | URL |
|---|---|
| Collect and organize your data | https://developers.google.com/meridian/docs/pre-modeling/collect-data |
| Amount of data needed | https://developers.google.com/meridian/docs/pre-modeling/amount-data-needed |
| Geo-level modeling & geo selection | https://developers.google.com/meridian/docs/pre-modeling/geo-selection-national-data |
| Exploratory data analysis (thresholds) | https://developers.google.com/meridian/docs/pre-modeling/perform-eda |
| Input data & scaling functions | https://developers.google.com/meridian/docs/advanced-modeling/input-data |
| Control variables | https://developers.google.com/meridian/docs/advanced-modeling/control-variables |
| Organic & non-media variables | https://developers.google.com/meridian/docs/advanced-modeling/organic-and-non-media-variables |
| Reach and frequency | https://developers.google.com/meridian/docs/advanced-modeling/reach-frequency |
| Paid search modeling (GQV confounder) | https://developers.google.com/meridian/docs/advanced-modeling/paid-search-modeling |
| Causal graph | https://developers.google.com/meridian/docs/causal-inference/causal-graph |
| Supported data types and formats | https://developers.google.com/meridian/docs/user-guide/supported-data-types-formats |
| Load geo data (CoordToColumns) | https://developers.google.com/meridian/docs/user-guide/load-geo-data-without-rf |
| Model debugging (low-spend channels) | https://developers.google.com/meridian/docs/post-modeling/model-debugging |
| Sample datasets | https://github.com/google/meridian/tree/main/meridian/data/simulated_data/csv |

### Tier 2 — foundational papers

- **Chan, D. & Perry, M. (2017).** *Challenges and Opportunities in Media Mix Modeling.* Google. — The canonical account of what goes wrong. Source of the 7–10 points/parameter rule, the 3–4 params/channel estimate, and the taxonomy of data limitations / selection bias / model uncertainty. Their five-plausible-model example (all R² 0.98–0.99, budget recommendations differing by up to 50%) is the argument for why data prep discipline matters more than model tuning.
- **Sun, Y., Wang, Y., Jin, Y., Chan, D. & Koehler, J. (2017).** *Geo-level Bayesian Hierarchical Media Mix Modeling.* Google. — Underpins Meridian's geo model. §4.3 on omitted-variable-bias reduction, §4.4 on national→geo imputation.
- **Jin, Y., Wang, Y., Sun, Y., Chan, D. & Koehler, J. (2017).** *Bayesian Methods for Media Mix Modeling with Carryover and Shape Effects.* Google. — Adstock and Hill functional forms.
- **Chen, A., Chan, D., Perry, M., Jin, Y., Sun, Y., Wang, Y. & Koehler, J. (2018).** *Bias Correction for Paid Search in Media Mix Modeling.* arXiv:1807.03292. — Backdoor-criterion justification for query volume as a control.
- **Wang, Y., Jin, Y., Sun, Y., Chan, D. & Koehler, J. (2017).** *A Hierarchical Bayesian Approach to Improve Media Mix Models Using Category Data.* Google. — Pooling across brands when single-brand data is too thin.
- **Zhang, S. & Vaver, J. (2017).** *Introduction to the Aggregate Marketing System Simulator.* Google. — Simulating datasets with known ground truth; useful for testing a data-prep pipeline end to end.
- **Google (n.d.).** *Bayesian Hierarchical Media Mix Model Incorporating Reach and Frequency Data.* — Basis for the R&F formulation.

### Tier 3 — cross-framework corroboration

- **Meta Robyn** — analyst guide and `robyn_inputs()` docs. 10:1 observations-to-variable ratio, 2-year weekly minimum, spend/exposure variable pairing. Useful as an independent check on parameter budgeting. Note its Prophet-based seasonality decomposition does **not** transfer to Meridian (§9.4).
- **Ng, E., Wang, Z. & Dai, A. (2021).** *Bayesian Time Varying Coefficient Model with Applications to Marketing Mix Modeling.* arXiv:2106.03322. — Concise statement of the four structural problems: small-n-large-p, granularity vs sparsity trade-off, correlated errors, endogeneity/multicollinearity.
- **Robyn team (2024).** *Packaging Up Media Mix Modeling.* arXiv:2403.14674. — Documents the conventional MMM dataset layout (`_S` spend, `_I` impressions, `_P` clicks suffixes).
- **PyMC-Marketing** — alternative Bayesian MMM; useful for contrasting prior/variable-selection conventions.

### A note on tiering

Tier 1 is normative for *this pipeline* — it defines what the library accepts. Tier 2 explains *why*, and is what the agent should reason from when Tier 1 is silent. Tier 3 is corroboration; where Tier 3 conflicts with Tier 1 (seasonality handling being the clearest case), Tier 1 wins.
