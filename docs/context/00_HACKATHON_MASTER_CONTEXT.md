# Hackathon Master Context

## 1. Objective

Win Google's All Things Agentic Hackathon by producing a technically disciplined, demonstrably autonomous Taskmaster entry in a domain where the team has real expertise: marketing measurement and MMM data preparation.

The project is **ModelReady**.

### Product / system naming

- **ModelReady** = the product and user-facing system.
- **M3 Agent** = ModelReady's autonomous Media Mix Modeling data-operations worker.
- **M3** = **Map. Mend. Model-Ready.**
- **MEL** = the ModelReady Experience Loop that lets M3 learn from evaluated outcomes.
- **M3 Learning Receipt** = user/judge-facing proof that experience was learned or applied.

## 2. Challenge fit

Taskmaster rewards autonomous systems that remove real operational friction and complete workflows with little hand-holding.

ModelReady's complete loop:

1. A new dataset or data package arrives.
2. The system detects the event.
3. It inventories sources and identifies likely providers.
4. It resolves source schemas against a provider registry.
5. It profiles the data.
6. It maps inputs into a model-agnostic normalization layer.
7. It evaluates Meridian readiness.
8. It creates a remediation plan.
9. It performs only safe transformations automatically.
10. It re-validates the output.
11. M3 publishes the validated MMM artifact to BigQuery in a model-consumable table/view.
12. It generates a Meridian input contract/configuration and complete provenance.
13. It verifies publish parity between the validated artifact and BigQuery output.
14. The dataset enters **MODEL_READY** state.
15. Optional Meridian execution is offered behind an explicit approval gate.
16. It evaluates the run.
17. It records lessons from the episode and issues an M3 Learning Receipt.
18. Future similar runs retrieve validated lessons and improve routing/mapping.

## 3. Judging alignment

### Innovation & Operational Utility — 40%

We win by showing that an analyst can provide messy inputs and receive substantially improved, model-ready outputs without directing each intermediate step.

Evidence:
- number of issues detected;
- number safely auto-remediated;
- readiness score before/after;
- human interventions avoided;
- time/steps reduced on a repeated similar task;
- output accepted by deterministic Meridian compatibility checks.

### Architectural Discipline — 30%

We win by making state, memory, evaluation, tool boundaries, safety and failure recovery visible.

Required:
- Google ADK orchestration;
- explicit state machine;
- deterministic tools;
- typed artifacts;
- idempotent transforms;
- immutable run manifests;
- persistent experience store;
- retrieval of validated lessons;
- approval gate for risky transforms;
- evaluation and regression before lesson/policy promotion;
- secure secrets;
- structured logs;
- failure/retry behavior.

### Demo & Production Readiness — 30%

Required:
- deployed backend on Google Cloud;
- reproducible repo;
- architecture diagram;
- live/recorded proof of Cloud Run execution;
- visible event progression;
- downloadable artifacts;
- clean README;
- seeded demo dataset;
- one-click or simple deployment instructions;
- tests and evaluation report.

## 4. Core differentiator

Most agent demos optimize conversation quality. ModelReady optimizes a **verifiable operational artifact**.

The input can fail known checks.
The agent acts.
The output can be tested again.

This creates objective evidence of autonomous improvement.

## 5. Google-native thesis

The stack should be visibly Google-native:

- Gemini for reasoning
- Google ADK for orchestration
- Cloud Run for agent/API execution
- Cloud Storage for raw/output artifacts
- Pub/Sub or Eventarc for ingestion triggers
- BigQuery for profiles, run telemetry and experience analytics
- Firestore for workflow/job state if useful
- Vertex AI Memory Bank for validated experiential memories
- Secret Manager for credentials
- Cloud Logging for production evidence
- Google Meridian as first modeling target
- MMM Unified Schema as canonical interoperability target
- BigQuery as both experience ledger and first-class model-ready publishing destination
- Cloud Workflows + Colab Enterprise as an optional approval-gated Meridian execution path, following the Cortex for Meridian pattern

## 6. Schema strategy

Do **not** invent an isolated universal MMM schema.

Use three layers:

### Layer A — Provider Registry
Facts about provider exports:
- provider;
- report/export type;
- field names;
- field semantics;
- data types;
- aggregation behavior;
- grain;
- supported dimensions;
- lookback/export constraints;
- known quirks;
- source URL/evidence.

### Layer B — ModelReady Normalized Representation
The operational staging layer required for profiling, repair and transformations.

It should retain provenance at the field level:
- source provider;
- source file;
- source field;
- source row/grain;
- transformation history;
- confidence.

### Layer C — MMM Unified Schema / Meridian Adapter
Produce Google-aligned canonical artifacts and Meridian-specific input mappings.

### Layer D — BigQuery Model Contract
Publish validated model inputs into a stable BigQuery table/view contract, together with:
- Meridian column mappings;
- channel mappings;
- validation results;
- transformation manifest;
- provenance;
- run metadata.

M3 may publish this contract autonomously after deterministic validation and publish-parity checks pass. Actual Meridian model execution remains approval-gated.

## 7. Learning thesis

ModelReady must demonstrate **experiential learning**, not just memory.

Learning means a prior evaluated outcome changes a future decision.

A lesson is only promoted when:
- the outcome can be measured;
- evidence supports the lesson;
- scope is explicit;
- confidence is sufficient;
- regression tests do not worsen established cases.

The demo should include two related episodes so judges can see the improvement. Each meaningful lesson should be visible through an **M3 Learning Receipt** and later, when reused, an **Experience Applied** receipt.

## 8. Demo thesis

The user drops a deliberately messy data package for a synthetic music-instrument ecommerce company.

Data:
- Google Ads
- Meta Ads
- GA4
- Shopify/commerce
- optional macro/control data

The system autonomously:
- detects providers;
- maps columns;
- identifies defects;
- fixes safe issues;
- asks for one meaningful human decision if needed;
- produces a Meridian-ready package;
- validates it;
- publishes the final model artifact to BigQuery;
- generates the Meridian input contract;
- verifies BigQuery publish parity;
- records an episode and Learning Receipt.

Then a second related data package contains a previously unseen-but-similar schema issue.

The system retrieves the prior validated lesson and resolves it faster / with fewer ambiguous steps.

## 9. Product guardrails

1. Never fabricate missing observations.
2. Never impute KPI/control data without making the method explicit.
3. Never silently change semantic meaning.
4. Never promote a lesson solely because an LLM says it is good.
5. Never let experience memory override deterministic model requirements.
6. Every transformation must be reversible or reproducible.
7. Every output must have provenance.
8. Risky actions require confirmation.
9. Evaluation data must be separable from training/optimization data.
10. Demo reliability takes precedence over breadth.

## 10. Definition of done

A submission-quality build is done when:

- a fresh raw demo package triggers the agent;
- the agent completes the full workflow without step-by-step prompting;
- a before/after readiness score is produced;
- safe defects are automatically corrected;
- unsafe/ambiguous defects are surfaced for approval;
- output artifacts pass deterministic checks;
- validated MMM data is published to a BigQuery model table/view;
- the BigQuery artifact is verified against the validated source artifact;
- a Meridian input mapping/config is generated;
- optional model execution remains approval-gated;
- the system records a complete episode and M3 Learning Receipt;
- a second run demonstrably uses a validated prior lesson;
- agent trajectories and outcomes are stored;
- deployed execution is visible in Google Cloud;
- tests/evals pass;
- README and architecture are reproducible;
- four-minute demo is recorded;
- bonus article and social post are published;
- submission is complete before the deadline.
