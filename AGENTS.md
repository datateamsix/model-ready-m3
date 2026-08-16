# AGENTS.md

You are contributing to **ModelReady**, an entry for Google's All Things Agentic Hackathon.

Canonical naming:
- **ModelReady** = product
- **M3 Agent** = autonomous worker
- **M3** = Map. Mend. Model-Ready. / Media Mix Modeling
- **MEL** = ModelReady Experience Loop
- **M3 Learning Receipt** = proof of learned/applied experience

Before coding, read:
1. `README.md`
2. `docs/context/00_HACKATHON_MASTER_CONTEXT.md`
3. `docs/context/02_SYSTEM_ARCHITECTURE.md`
4. the relevant workstream spec.

## Absolute rules

- Deadline is Aug 31, 2026 at 5:00 PM PT.
- Primary track is Taskmaster.
- Google Meridian is the first modeling target.
- Align with Google's MMM Unified Schema where practical.
- Agent behavior must be autonomous but auditable.
- Deterministic validators own readiness; agent prose never does.
- `MODEL_READY` additionally requires verified BigQuery publish parity, a complete Meridian handoff contract, and official pre-modeling EDA with zero ERROR findings.
- Raw input is immutable.
- Every transform has provenance.
- Validated model artifacts should be publishable to a versioned BigQuery table/view.
- M3 may publish validated run-scoped/versioned model artifacts autonomously.
- Launching Meridian (posterior / model fitting) is approval-gated. Autonomous official pre-modeling EDA, including EDA-only `sample_prior`, is required and is not model execution.
- Learning is evidence-driven; do not implement uncontrolled self-modification.
- Demo reliability is more important than feature breadth.
- Do not add infrastructure or agents without a clear rubric/demo benefit.
- Do not hard-code GCP project IDs, resource names, demo metrics, readiness outcomes, or learning receipts.

## Engineering principle

**LLM decides; deterministic code proves.**

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
- M3 Learning Receipt evidence.

## MVP order of operations

Do not broaden scope until this works end to end:

`fixture/upload → M3 → profile → issue detection → safe repair → deterministic validation → BigQuery publish → parity check → Meridian contract → official pre-modeling EDA → MODEL_READY`
