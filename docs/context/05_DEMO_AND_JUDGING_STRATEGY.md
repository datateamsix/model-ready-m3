# Demo and Judging Strategy

## Demo goal

In four minutes, make judges believe three things:

1. This agent solves a painful real workflow.
2. It actually performs autonomous work.
3. The architecture is disciplined enough to trust.

## Demo story

### Synthetic company

Working business:
**Music Center** — ecommerce retailer for musical instruments.

Marketing stack:
- Google Ads
- Meta Ads
- GA4
- Shopify
- optional macro/control source

## Demo dataset A

Deliberately contains known defects:
- campaign-level exports;
- date-format mismatch;
- daily/weekly mismatch;
- duplicate records;
- missing inactive-media week;
- numeric strings/currency formatting;
- inconsistent channel labels;
- non-summable metric candidate;
- missing KPI period;
- insufficient-history warning or configurable edge case.

## Suggested 4-minute sequence

### 0:00–0:20 — Friction
"MMM often fails before modeling. Teams spend days turning incompatible platform exports into trustworthy model inputs."

### 0:20–0:35 — Product
"Meet M3 — ModelReady's autonomous Media Mix Modeling data-operations agent. M3 maps, mends, and makes fragmented marketing data model-ready."

### 0:35–0:50 — Architecture
Very fast visual:
Cloud Storage event → M3 Agent (ADK/Gemini) → deterministic tools → Meridian validator → BigQuery publish → Experience Loop.

### 0:50–2:35 — Autonomous run
Drop dataset.

Then hands off keyboard.

Show live stages:
- provider detection;
- profiling;
- mapping;
- issue creation;
- safe fixes;
- approval pause only if strategically useful;
- validation;
- BigQuery publish;
- publish-parity verification;
- generated Meridian input contract;
- output package.

The autonomous run should visibly end at **MODEL_READY**.

Show before/after:
- issues;
- readiness;
- transformed artifact.

### 2:35–3:15 — Learning
Second related package arrives.

Show:
- prior validated lesson retrieved;
- ambiguity resolved automatically;
- fewer steps or fewer approvals;
- deterministic validation still passes;
- `EXPERIENCE APPLIED` receipt;
- final BigQuery publish still passes parity.

### 3:15–3:40 — Production proof
Show:
- Cloud Run service;
- Cloud Logging;
- BigQuery experience/run rows;
- the published Meridian-facing BigQuery model view;
- Memory Bank or relevant Google Cloud evidence.

### 3:40–4:00 — Close
"M3 turns fragmented marketing exports into validated, auditable, BigQuery-published data that is ready for Meridian—and gets better from every evaluated run."

## Rubric evidence map

### 40% Operational Utility
On screen:
- raw input;
- autonomous execution;
- actual transformed output;
- issue delta;
- approval avoided on learned run.

### 30% Architecture
On screen:
- state transitions;
- agent vs deterministic tools;
- persistent run ID;
- memory/experience;
- validator gate;
- failure/approval behavior.

### 30% Production Readiness
On screen:
- deployed Cloud Run;
- logs;
- reproducible repo;
- tests/evals;
- downloadable artifacts.

## Bonus plan

Minimum:
- publish technical article;
- publish LinkedIn/X social post;
- integrate one legitimate additional Google AI model if it serves the product.

Stretch:
- investigate up to three additional qualifying Google AI models, but never damage product coherence for points.

## Prize positioning

Primary:
- Taskmaster

Secondary resonance:
- Architectural Design
- potentially Startup Excellence if eligibility/entry structure is appropriate

## Demo rule

Never rely on the judges imagining what happened.

**Show the action. Show the artifact. Show the proof.**

## Golden demo terminal state

The required demo terminal state is:

```text
MODEL_READY
✓ deterministic readiness passed
✓ BigQuery model artifact published
✓ publish parity passed
✓ Meridian input contract generated
✓ provenance complete
```

Optional stretch:
`Approve & Run Meridian`

If included, actual model execution must remain clearly approval-gated and should not displace the core four-minute proof.

## M3 naming in judge-facing copy

Use consistently:
- **ModelReady** — product
- **M3 Agent** — autonomous worker
- **Map. Mend. Model-Ready.** — M3 operational meaning
- **Media Mix Modeling** — domain meaning
- **MEL** — experience/learning loop
- **M3 Learning Receipt** — proof that reusable experience was created
