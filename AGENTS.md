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

`fixture/upload → PreM3 → profile → issue detection → safe repair → deterministic validation → BigQuery publish → parity check → Meridian contract → PreM3 pre-EDA diagnostics → official pre-modeling EDA → MODEL_READY`

## Context routing

Do not load every long context file into every agent prompt.

| Path | Load |
|---|---|
| Every agent | `docs/context/prem3_mmm_boot_context.md` |
| Product / general user-facing | `docs/context/prem3_product_context.md` |
| User-facing presentation | `docs/context/RESPONSE_STYLE_GUIDE.md` plus the typed contract in `app/response/` |
| Execution / readiness | `docs/context/meridian/meridian_data_prep_context.md` |
| Advisory / conversational | `docs/context/meridian/meridian_advisor_playbook.md` |
| Deterministic runtime | `app/rules/meridian.yaml` plus `app/rules/intelligence_registry.yaml` (pre-EDA diagnostics implemented) |
| Domain reasoning | current DOMAIN_VIEW (`docs/context/domain-view/DOMAIN_VIEW.md`, `app/domain/intelligence/data/current/domain_view.json`) |

Intelligence version: `docs/context/intelligence/intelligence_version.json`.

Four user-value behaviors: **ASSESS · ADVISE · INSIGHT · GUIDE**.

Knowledge classes: `MERIDIAN_NORMATIVE` · `PREM3_DETERMINISTIC_DIAGNOSTIC` · `MMM_EVIDENCE_HEURISTIC` · `MMM_JUDGMENT`.

A deterministic calculation does not grant action authority. Official Meridian owns official EDA findings. Heuristics cannot independently block `MODEL_READY`.

The isolated Meridian EDA worker must not load product, DOMAIN_VIEW, or RESPONSE_STYLE_GUIDE prose.

Do not turn execution agents into sales bots. Product context exists so PreM3 can answer product questions accurately, not inject marketing into every interaction.

User-facing agents should use the structured response contract when a response type exists. Do not return a large unstructured text block when typed intelligence can be presented. Structured evidence remains authoritative. Gemini may summarize evidence; it may not invent numbers, owners, authority, or `MODEL_READY`.

The computational/semantic intelligence layer must not change BigQuery publication, BQ parity, the Meridian worker, official EDA behavior, the `MODEL_READY` gate, Cloud Run resource names, Eventarc, or MEL runtime. DOMAIN_VIEW is consumed, not mutated. The presentation layer consumes that intelligence; it does not recalculate it.

## Legacy technical identifiers

Some infrastructure and internal machine identifiers retain the earlier `modelready-m3` / `m3` namespace for compatibility with proven cloud deployments. They are implementation identifiers, not a separate product.
