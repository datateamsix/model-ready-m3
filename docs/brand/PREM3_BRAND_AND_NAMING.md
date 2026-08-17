# PreM3 brand and naming

Canonical naming source of truth for current product copy.

## Product

**PreM3**

Pronunciation (internal): "pre-em-three". Do not force pronunciation into product copy.

Exact capitalization: `P` `r` `e` `M` `3`.

Do not use `PREM3`, `Prem3`, `preM3`, or `prem3` in user-facing copy except where a lowercase technical slug is required.

## Descriptor

A self-learning, autonomous pre-modeling agent for Google Meridian.

## Operating line

Map. Mend. Model.

## Secondary line

Before you model, PreM3.

## Domain

`prem3.ai`

Do not append `.ai` to the product name unless referring to the domain.

## Hierarchy

```text
PreM3
│
├── M3 operating method
│     ├── MAP
│     ├── MEND
│     └── MODEL
│
├── deterministic pre-modeling engine
├── BigQuery model-consumption contract
├── official Meridian EDA integration
├── Gemini interpretation
├── User Resolution / Modeler Handoff
└── MEL
      PreM3 Experience Loop
```

PreM3 is simultaneously the product, the autonomous agent, and the user-facing system. Do not present **M3 Agent** as a separate personality.

## M3

M3 is the operating method inside PreM3: **Map. Mend. Model.**

It also naturally references Media Mix Modeling.

Correct: "PreM3 uses the M3 operating method: Map. Mend. Model."

Avoid: "ModelReady contains an M3 Agent."

### MAP

Understand the data before changing it: inventory sources, identify providers, profile schemas, infer grain, resolve semantics, identify KPI/media/control/treatment candidates, map fields into canonical concepts, establish provenance, and determine what PreM3 knows and does not know.

MAP is not merely renaming columns.

### MEND

Safely resolve what can be resolved: deterministic AUTO_SAFE transforms, date/type normalization, valid aggregation, duplicate resolution, evidence-supported media inactivity zero-fill, approved mappings, repeated validation, and provenance.

MEND never means fabricate data, silently impute KPI, silently change causal semantics, silently merge channels, or silently change model configuration.

### MODEL

In **Map. Mend. Model.**, **Model** refers to completing and validating the model-consumption package and pre-modeling diagnostics—not fitting the Meridian MMM.

MODEL includes explicit schema compilation, the model-ready manifest, versioned BigQuery publication, independent verification, the Meridian input contract, official pre-modeling EDA, finding interpretation, resolution guidance, and the modeler handoff. Then `MODEL_READY`.

Customer-facing Mission 2 copy uses **Meridian Integration** for that completion surface. Do not introduce “Meridian handoff” in new customer-facing product UI. Internal artifact names may keep `handoff_*`.

Posterior sampling and production model fitting remain outside the default autonomous boundary.

## MEL

**MEL** remains the acronym.

Current full name: **PreM3 Experience Loop**.

Canonical learning principle: PreM3 has learned only when evaluated experience changes future behavior, and the changed behavior can be shown to remain correct.

Self-learning means PreM3 learns from evaluated experience. Completed pre-modeling episodes may produce scoped candidate lessons. Only lessons that pass evidence, safety, and regression gates can become reusable knowledge.

Self-learning does **not** mean uncontrolled self-modification, runtime source-code rewriting, automatic fine-tuning after every run, unreviewed rule rewriting, automatically changing official Meridian thresholds or final priors, or treating chat history as learning.

## MODEL_READY

`MODEL_READY` is a verified operational state, not a product name.

It means the pre-modeling contract and official EDA gate pass. It does not guarantee posterior convergence, identifiability, stable ROI, business usefulness, or a particular modeler's final specification.

## Approved current language

- PreM3
- A self-learning, autonomous pre-modeling agent for Google Meridian.
- Map. Mend. Model.
- Before you model, PreM3.
- PreM3 Experience Loop
- PreM3 Learning Receipt
- MODEL_READY
- Official Meridian EDA
- PreM3 User Resolution Pack
- PreM3 Pre-Modeling Handoff
- PreM3 Model-Ready Manifest

## Deprecated user-facing language

- ModelReady — when used as the product name
- M3 Agent — when used as a separate user-facing worker
- Map. Mend. Model-Ready.
- ModelReady Experience Loop
- M3 Learning Receipt

Do not mark internal machine identifiers deprecated.

## Technical-ID compatibility

Some infrastructure and internal machine identifiers retain the earlier `modelready-m3` / `m3` namespace for compatibility with proven cloud deployments. They are implementation identifiers, not a separate product.

Examples intentionally preserved:

- GCP project `modelready-m3`
- Cloud Run service `modelready-m3`
- runtime service account `m3-runtime@...`
- BigQuery datasets `modelready_ops`, `modelready_experience`, `modelready_models`
- ADK agent name `modelready_m3`
- environment namespaces `M3_*` and `MODELREADY_*`
- machine files such as `model_ready_manifest.json`
- machine state `MODEL_READY`

## Repository

GitHub repository: `datateamsix/prem3`.

The Python distribution name remains `model-ready-m3` so imports and ADK deployment stay stable.

## Visual system

Approved artwork and production specs live in [`brand/brand-assets/`](../brand/brand-assets/). Inventory: [`brand/ASSET_INVENTORY.md`](../brand/ASSET_INVENTORY.md). Implementation guide: [`brand/README.md`](../brand/README.md).

### Approved PreM3 Brand System

![Approved PreM3 Brand System](../brand/brand-assets/reference/prem3-approved-brand-board.png)

### Canonical logo

Use the approved primary lockup reference until vector masters are delivered:

![PreM3 — Map. Mend. Model.](../brand/brand-assets/reference/prem3-approved-primary-logo-reference.png)

Do not redraw, auto-trace, or approximate this mark.

### Palette

| Hex | Purpose |
|---|---|
| `#1A1F4B` | Navy / primary identity |
| `#3B4BDB` | Indigo / transition |
| `#00C2F5` | Cyan / resolved accent and numeral `3` |
| `#E6EAF1` | Cool gray / fragments and borders |
| `#F5F7FA` | Light surface |

Hex values match the approved board. Token naming in the delivered package differs slightly from some brief copy (`Cool Gray` vs `Light Gray` for `#E6EAF1`). Do not silently rename source tokens.

### Typography

- Primary / display: Satoshi
- Secondary / UI: Inter

`FONT_IMPLEMENTATION_PENDING`. Font binaries are not in this repository.

### Logo usage

- Wide / README: `brand/brand-assets/reference/prem3-approved-primary-logo-reference.png`
- Icon reference: `brand/brand-assets/reference/prem3-approved-icon-reference.png`
- Wordmark reference: `brand/brand-assets/reference/prem3-approved-wordmark-reference.png`
- Do not add `.ai` to the lockup
- Do not use the full brand board as a product hero

### Icon usage

Dedicated favicon / app-icon exports are not delivered (`FAVICON_EXPORT_PENDING`). Do not shrink the full mark to 16–32 px.

### Light / dark

All delivered rasters are on opaque white. No standalone inverse or transparent lockup exists (`INVERSE_STANDALONE_PENDING`, `TRANSPARENT_LOCKUP_PENDING`). GitHub dark mode will show a white plate behind the README logo.

### Brand descriptors on the approved board

Disciplined. Reliable. Adaptive. Precise. Model-Ready.

Do not invent additional personality terms.
