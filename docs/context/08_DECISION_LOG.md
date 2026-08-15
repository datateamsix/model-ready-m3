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

## 2026-08-13 — Meridian execution authority
**Decision:** M3 may prepare the full Meridian execution handoff, but launching a Meridian model remains approval-gated.

**Why:** Model configuration choices can materially affect model behavior and interpretation. Operational autonomy should not silently expand into model-governance authority.

**Stretch architecture:** Cloud Workflows + Colab Enterprise, aligned with the official Cortex for Meridian pattern.

---

## 2026-08-13 — Learning Receipts
**Decision:** Learning Receipts are first-class product and demo artifacts.

**Types:**
- `EXPERIENCE_LEARNED`
- `EXPERIENCE_APPLIED`

**Why:** They make experiential learning observable and auditable instead of requiring judges/users to trust a claim that the agent "learns."
