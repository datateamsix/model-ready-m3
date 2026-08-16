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
