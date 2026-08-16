# AGENTS.md

You are contributing to **PreM3**, an entry for Google's All Things Agentic Hackathon.

Canonical naming:
- **PreM3** = product and autonomous pre-modeling agent
- **M3** = Map. Mend. Model. operating method / Media Mix Modeling reference
- **MEL** = PreM3 Experience Loop
- **PreM3 Learning Receipt** = proof of promoted experience
- **EXPERIENCE_APPLIED** = proof validated experience changed a future run
- **MODEL_READY** = verified pre-modeling terminal state

Before coding, read:
1. `README.md`
2. `docs/PREM3_BRAND_AND_NAMING.md`
3. `docs/context/00_HACKATHON_MASTER_CONTEXT.md`
4. `docs/context/02_SYSTEM_ARCHITECTURE.md`
5. the relevant workstream spec.

## Absolute rules

- Deadline is Aug 31, 2026 at 5:00 PM PT.
- Primary track is Taskmaster.
- Google Meridian is the first modeling target.
- Align with Google's MMM Unified Schema where practical.
- Agent behavior must be autonomous but auditable.
- Deterministic validators own readiness; agent prose never does.
- BigQuery model input must be independently verified.
- Official Meridian EDA is autonomous pre-modeling.
- Official Meridian ERROR blocks `MODEL_READY`.
- EDA ATTENTION may allow `MODEL_READY` with review recommended.
- Agent prose never determines `MODEL_READY`.
- Raw input is immutable.
- Every transform has provenance.
- No fabricated observations.
- No silent business-semantic changes.
- Validated model artifacts should be publishable to a versioned BigQuery table/view.
- PreM3 may publish validated run-scoped/versioned model artifacts autonomously.
- Posterior sampling and Meridian model fitting remain outside autonomous authority. Official pre-modeling EDA, including EDA-only `sample_prior`, is required and is not model execution.
- Learning is evidence-driven; do not implement uncontrolled self-modification.
- Demo reliability is more important than feature breadth.
- Do not add infrastructure or agents without a clear rubric/demo benefit.
- Do not hard-code GCP project IDs, resource names, demo metrics, readiness outcomes, or learning receipts.

## Engineering principle

**Gemini decides. Deterministic code proves. Meridian calculates. Gemini interprets. Experience teaches. Evaluation decides what survives.**

Use agents for reasoning/context boundaries. Use ordinary typed functions/tools for deterministic calculations and transformations.

## Definition of useful work

A change is useful if it improves at least one:
- operational autonomy;
- deterministic correctness;
- Meridian readiness;
- experiential learning;
- cloud production proof;
- demo clarity;
- reproducibility;
- BigQuery model-contract integrity;
- PreM3 Learning Receipt evidence.

## MVP order of operations

Do not broaden scope until this works end to end:

`fixture/upload → PreM3 → profile → issue detection → safe repair → deterministic validation → BigQuery publish → parity check → Meridian contract → official pre-modeling EDA → MODEL_READY`

## Legacy technical identifiers

Some infrastructure and internal machine identifiers retain the earlier `modelready-m3` / `m3` namespace for compatibility with proven cloud deployments. They are implementation identifiers, not a separate product.
