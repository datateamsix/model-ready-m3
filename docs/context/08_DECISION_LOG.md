# Decision Log

## 2026-08-13 — Track
**Decision:** Target Taskmaster.

**Why:** ModelReady is naturally event-driven, autonomous, multi-system and artifact-producing.

---

## 2026-08-13 — Product
**Decision:** Primary entry is ModelReady.

**Positioning:** Autonomous pre-modeling data operations for marketing measurement.

---

## 2026-08-13 — First modeling target
**Decision:** Google Meridian.

**Why:** Strong challenge/domain fit, open source, Google-native, objective input requirements.

---

## 2026-08-13 — Canonical interoperability
**Decision:** Align output to Google's MMM Unified Schema where practical rather than inventing a competing universal schema.

**Why:** Interoperability and stronger Google-native architecture.

---

## 2026-08-13 — Learning
**Decision:** Experiential learning is P1 hackathon functionality, not post-hackathon roadmap.

**Definition:** prior evaluated episodes must measurably change future execution.

**Safety:** no uncontrolled live self-modification.

---

## 2026-08-13 — Learning architecture
**Decision:** BigQuery is the auditable experience ledger; Vertex AI Memory Bank is retrieval memory; ADK evaluation measures trajectories; ADK optimization is controlled/offline.

---

## 2026-08-13 — Engineering philosophy
**Decision:** LLM decides; deterministic code proves.

---

## 2026-08-13 — Demo
**Decision:** use synthetic ecommerce musical-instrument business data with seeded defects.

**Why:** reproducible, controllable, objective defect ground truth.

---

## 2026-08-13 — Agent naming
**Decision:** The autonomous worker inside ModelReady is the **M3 Agent**.

**Meaning:** **Map. Mend. Model-Ready.**

**Secondary/domain meaning:** Media Mix Modeling.

**Hierarchy:**
- ModelReady = product
- M3 Agent = autonomous worker
- MEL = ModelReady Experience Loop
- M3 Learning Receipt = visible proof of learned/applied experience

---

## 2026-08-13 — Model-ready BigQuery publish
**Decision:** BigQuery publishing is a first-class M3 task, not merely an export option.

**Why:** The strongest Taskmaster endpoint is an operational artifact that is immediately available for model use.

**Required behavior:** After deterministic readiness validation, M3 may autonomously create a versioned BigQuery model-input table/view, write provenance/manifests, generate the Meridian input contract, and verify publish parity.

**Success milestone:** `MODEL_READY`. True terminal stages remain `FAILED` and `COMPLETE`.

---

## 2026-08-15 — MODEL_READY is a success milestone
**Decision:** `MODEL_READY` is a success milestone, not a hard terminal state.

**Why:** Phase 3 learning (`MODEL_READY → LEARNING`) and later Meridian approval (`MODEL_READY → WAITING_FOR_MODEL_APPROVAL`) must remain legal. Failed and completed runs stay terminal.

**Display:** Phase 1 Dataset A scripts still stop showing progress at `MODEL_READY`.

---

## 2026-08-15 — Model consumption tables are partitioned, clustered, and described in DDL
**Decision:** Versioned Meridian model-input tables are created with compiled DDL, not inferred load-job schemas.

**Required physical layout:**
- `PARTITION BY time`
- `CLUSTER BY geo`
- every column has a description in `CREATE TABLE` DDL
- the subsequent load job restates partition, clustering, and descriptions so `WRITE_TRUNCATE` cannot drop them

**Why:** Meridian queries a durable consumption object. Partitioning and clustering keep that object cheap to scan. Column descriptions make the published contract inspectable in BigQuery without reading ModelReady source.

**Fail closed:** a destination that exists with the right rows but the wrong physical type, missing descriptions, or missing partition/cluster cannot become `MODEL_READY`.

---

## 2026-08-13 — Meridian execution authority
**Decision:** M3 may prepare the full Meridian execution handoff, but launching a Meridian posterior / fitted model remains approval-gated. Autonomous official pre-modeling EDA is required and is not that launch.

**Why:** Model configuration choices can materially affect model behavior and interpretation. Operational autonomy should not silently expand into model-governance authority. Pre-modeling EDA uses official `EDASpec()` and may call `sample_prior` only for diagnostics.

**Stretch architecture:** Cloud Workflows + Colab Enterprise, aligned with the official Cortex for Meridian pattern.

---

## 2026-08-15 — CLOUD_TASKMASTER five-tool operational API
**Decision:** The deployed M3 agent executes Dataset A through five run-level tools. Gemini selects issue IDs; deterministic plans supply transform parameters. Durable run state lives in the artifact GCS bucket, not in RAM or `/tmp`.

**Why:** Judges must see that M3 did not invoke a monolithic preprocessing script. Eventarc, MEL, Dataset B/C, and Meridian execution remain out of scope until this path is proven.

---

## 2026-08-15 — Official Meridian EDA is deterministic compute, not a second agent
**Decision:** M3 remains one Taskmaster worker. Pre-modeling EDA uses the published `google-meridian==1.8.0` package. Gemini interprets structured `EDAFinding` objects; it does not calculate EDA metrics or override ERROR/ATTENTION/INFO.

**Runtime:** Measured Option B. Official install docs require Python 3.11 or 3.12. The M3 ADK service is Python 3.13 with pandas 3.0.x. Installing Meridian 1.8.0 would downgrade pandas to 2.x and pull TensorFlow 2.21. EDA therefore runs in a dedicated worker interpreter, not inside the ADK Cloud Run image.

**Priors:** MeridianEDA may call `sample_prior` for prior-probability diagnostics. That context is recorded as `MERIDIAN_DEFAULT` / `EDA_PRIOR_DIAGNOSTICS_ONLY` / `approved_for_final_modeling=false`. `sample_posterior` is forbidden.

**Gate:** Any official ERROR finding is `EDA_BLOCKED` and cannot become `MODEL_READY`. ATTENTION sets `review_recommended=true` without blocking. Passing EDA is `PRE_MODELING_COMPLETE`. `MODEL_READY` requires that EDA gate.

**Official parameters:** Deterministic tools persist and evaluate official Meridian `ModelSpec.knots` (not a homemade `n_knots` constructor) plus `check_data_param_ratio` scalars: `n_geos`, `n_times`, `n_knots`, `n_controls`, `n_treatments`, `n_parameters`, `n_data_points`, and `ratio`. Gemini interprets those values; it does not calculate them. EDA-only `knots < n_time` for geo-invariant time-only controls is disclosed and `approved_for_final_modeling=false`.

**Stage:** The only added run stage is `EXPLORING` (`PUBLISHING → EXPLORING → MODEL_READY`). ERROR / ATTENTION / INFO remain the official Meridian severities.

**Runtime isolation:** Do not install `google-meridian` into the M3 ADK Cloud Run image. Production EDA runs in Cloud Run Job `MODELREADY_EDA_JOB` on Python 3.12 with `google-meridian==1.8.0`.

**Idempotency:** `run_id + model_input_fingerprint + meridian_version + eda_config_fingerprint`. The EDA config fingerprint includes the trusted EDA-only ModelSpec policy. A data-dependent `knots=n_time-1` compatibility event is persisted as `EDA_MODEL_SPEC_COMPATIBILITY_ADJUSTMENT` and is not approved for final modeling.

**User resolution:** Official Meridian input rejection or ERROR findings produce a `USER_REQUIRED` resolution pack (`agent_can_fix=false`). Official Meridian text is stored separately from M3 interpretation. ATTENTION remains non-blocking with `review_recommended=true`.

---

## 2026-08-16 — Pre-modeling golden hardening

**Decision:** Official Meridian EDA is part of autonomous pre-modeling. The package executes only in an isolated Cloud Run Job. EDA-only prior sampling does not authorize model priors. `MODEL_READY` requires zero official ERROR findings. Non-agent-fixable EDA/input issues produce `USER_REQUIRED` resolution artifacts. Model fitting and `sample_posterior` remain outside autonomous M3 authority.

**Why:** Judges and users must be able to answer what code, container, Meridian distribution, BigQuery data, and configuration produced `MODEL_READY`, and what happens when Meridian says the data is not suitable.

---
**Decision:** Learning Receipts are first-class product and demo artifacts.

**Types:**
- `EXPERIENCE_LEARNED`
- `EXPERIENCE_APPLIED`

**Why:** They make experiential learning observable and auditable instead of requiring judges/users to trust a claim that the agent "learns."

---

## 2026-08-15 — Product rebrand to PreM3

**Decision:** ModelReady is rebranded as PreM3.

**Canonical positioning:** "A self-learning, autonomous pre-modeling agent for Google Meridian."

**Operating method:** "Map. Mend. Model."

**Reason:** The system now owns the complete pre-modeling assignment rather than only data-readiness evaluation. It maps fragmented inputs, safely mends issues, constructs and independently verifies the model-consumption artifact, executes official Meridian pre-modeling EDA, interprets the findings and creates the modeler handoff.

**M3:** retained as the internal operating concept and natural reference to Media Mix Modeling.

**MEL:** becomes the PreM3 Experience Loop.

**MODEL_READY:** remains the verified operational state.

**Technical identifiers:** existing `modelready-m3` and `m3` cloud/runtime identifiers may remain to protect proven infrastructure and historical evidence.

**Modeling authority:** official pre-modeling EDA is autonomous; posterior/model fitting remains outside autonomous authority.

**Repository:** GitHub remote renamed to `datateamsix/prem3`. The Python distribution name remains `model-ready-m3`.

---

## 2026-08-16 — PREM3 INTELLIGENCE MODEL

**Decision:** PreM3 intelligence now consists of three layers:

1. **Product Intelligence** — why PreM3 exists, who it serves, value, proof vs roadmap (`prem3_product_context.md`).
2. **MMM Domain Intelligence** — Meridian requirements, MMM best practice, causal reasoning (`prem3_mmm_boot_context.md` + specialized Meridian context).
3. **Run Intelligence** — what this user's actual data, diagnostics, official EDA, and open questions prove.

**User-value behavior** is organized around:

**Assess** — identify state, issues, contract readiness, and risk.  
**Advise** — explain official requirements and labeled best practice.  
**Insight** — interpret actual run evidence without converting pattern into causal claim.  
**Guide** — provide a concrete resolution path with an identified actor.

PreM3 computes what the data can establish, advises from source-backed best practice, interprets evidence into insights, and guides users through resolution where additional action is required.

**Authority:** official Meridian rules remain separate from PreM3 heuristics. Parameter-pressure interpretation is advisory and cannot independently block `MODEL_READY`. Missing media is not automatically zero. KPI/control imputation remains approval-gated. Causal roles are not inferred from correlation. Modeling feasibility remains separate from `MODEL_READY`.

**Scope of this decision:** context, contracts, and registry design only. No diagnostic-tool suite, MEL runtime, Eventarc, or `MODEL_READY` gate change.

---

## 2026-08-16 — PreM3 DOMAIN_VIEW

**Decision:** PreM3 will maintain a versioned operational domain view representing the knowledge it is currently justified and authorized to use.

**Key distinction:** memory is stored information; learning requires evaluated experience that changes future behavior.

Promoted experiential lessons may update DOMAIN_VIEW only after evidence, scope, safety and regression gates.

Official Meridian requirements and PreM3 safety policies retain higher authority.

Organization-specific context does not become global domain knowledge. Run facts do not become domain knowledge.

DOMAIN_VIEW v1 is generated from current verified intelligence and contains **0 promoted experiential lessons**. MEL Episode Core and `EXPERIENCE_APPLIED` remain unimplemented.
