# System Architecture

## Architectural goal

Build a small but production-minded event-driven agent with explicit state, deterministic validation, durable run history and experiential learning.

## Proposed Google Cloud architecture

```text
                 ┌──────────────────────┐
                 │   Web UI / Upload    │
                 └──────────┬───────────┘
                            │
                            v
                 ┌──────────────────────┐
                 │ Google Cloud Storage │
                 │ raw/{run_id}/...     │
                 └──────────┬───────────┘
                            │ Object event
                            v
                 ┌──────────────────────┐
                 │ Eventarc / Pub/Sub   │
                 └──────────┬───────────┘
                            v
                 ┌──────────────────────┐
                 │ Cloud Run            │
                 │ M3 Agent / ADK       │
                 │ Orchestrator         │
                 └───────┬──────────────┘
                         │
          ┌──────────────┼─────────────────┐
          │              │                 │
          v              v                 v
   ┌────────────┐ ┌────────────┐   ┌───────────────┐
   │ Gemini     │ │ Determin.  │   │ Memory/Evals  │
   │ reasoning  │ │ tools      │   │               │
   └────────────┘ └──────┬─────┘   └───────┬───────┘
                         │                 │
               ┌─────────┼─────────┐       │
               v         v         v       v
          BigQuery     GCS      Firestore  Vertex AI
          analytics  outputs     state     Memory Bank
```

## Agent topology

The user-facing autonomous worker is the **M3 Agent**: **Map. Mend. Model-Ready.**

M3 is one coherent Taskmaster worker implemented as an ADK orchestrator plus focused specialist agents/tools. Avoid presenting the product as a decorative swarm of agents.

Prefer one orchestrator plus focused specialist agents/tools.

### 1. M3 Orchestrator
Responsibilities:
- state transitions;
- task routing;
- retries;
- human approval pauses;
- final completion gate.

### 2. Intake/Resolver Agent
Reasoning tasks:
- provider identification;
- report-type identification;
- candidate field semantics;
- confidence scores.

### 3. Readiness Agent
Reasoning tasks:
- interpret deterministic findings;
- determine severity;
- build remediation plan;
- route ambiguous choices.

### 4. Learning/Evaluator Agent
Responsibilities:
- summarize run episode;
- compare outcome to expectations;
- create candidate lessons;
- assign scope/confidence;
- propose eval cases.

## Deterministic tools

Minimum:
- `inventory_files`
- `sample_dataset`
- `profile_dataset`
- `detect_grain`
- `detect_date_gaps`
- `detect_duplicates`
- `detect_missingness`
- `detect_non_summable_metrics`
- `aggregate_to_week`
- `aggregate_campaign_to_channel`
- `normalize_dates`
- `normalize_numeric_values`
- `zero_fill_media_if_inactive`
- `apply_mapping`
- `validate_meridian_fields`
- `validate_meridian_no_na`
- `validate_time_format`
- `validate_channel_mappings`
- `validate_history_length`
- `write_artifact`
- `write_bigquery_model_table`
- `create_meridian_bigquery_view`
- `generate_meridian_input_contract`
- `validate_bigquery_publish_parity`
- `write_publish_receipt`
- `compare_before_after`

## State model

```text
NEW
DISCOVERING
PROFILING
MAPPING
ASSESSING
WAITING_FOR_APPROVAL
REMEDIATING
VALIDATING
PUBLISHING
MODEL_READY
WAITING_FOR_MODEL_APPROVAL
MODELING
FAILED
LEARNING
COMPLETE
```

State transitions must be persisted and idempotent.

## Run identity

Every run receives:
- `run_id`
- `dataset_fingerprint`
- `created_at`
- `source_manifest`
- `agent_version`
- `registry_version`
- `rule_version`
- `prompt/policy_version`
- `model_version`
- `lesson_set_version`

This enables true before/after and regression analysis.

## Persistence

### Cloud Storage
- raw files;
- transformed files;
- reports;
- manifests.

### BigQuery

BigQuery has two distinct responsibilities.

#### A. Agent / experience analytics
Tables:
- `runs`
- `run_files`
- `profiles`
- `issues`
- `actions`
- `tool_calls`
- `evaluations`
- `lessons`
- `lesson_evidence`
- `regression_results`

#### B. Model-ready publishing contract
For each versioned run or organization namespace:
- model-input table;
- stable Meridian-facing view;
- channel mapping;
- validation results;
- transformation manifest;
- provenance;
- run metadata.

Publishing is complete only after parity checks confirm the BigQuery representation matches the artifact that passed deterministic validation.

### Firestore
Use if needed for fast workflow/UI state:
- active job;
- current stage;
- approvals;
- status events.

### Vertex AI Memory Bank
Store only **validated, generalized memories**, not raw datasets or secrets.

Examples:
- "Meta export field `amount_spent` is semantically media spend for report family X."
- "When a media-only week is absent and inactivity is supported by provider evidence, scaffold the period and zero-fill spend/exposure."
- "Do not aggregate CPC directly; reconstruct summable values from raw spend/clicks when available."

## Security

- Secret Manager for secrets.
- Service accounts with least privilege.
- Signed upload paths or authenticated API.
- No raw sensitive customer data in agent memory.
- Dataset retention config.
- Provenance log for all transformations.

## Failure strategy

- tool calls idempotent;
- retry transient failures;
- fail closed on ambiguous semantic transforms;
- preserve raw files;
- preserve previous output versions;
- validation required before READY;
- no irreversible transform without source artifact.

## Architecture constraint

Do not let "multi-agent" become decorative complexity.

Use agents when reasoning/context differs.
Use normal functions/tools for deterministic work.

## M3 publish and model handoff

The M3 Agent's default **success milestone** is **MODEL_READY**, not merely `READY`. True terminal stages are `FAILED` and `COMPLETE`. `MODEL_READY → LEARNING` and `MODEL_READY → WAITING_FOR_MODEL_APPROVAL` are legal; Phase 1 demos still stop displaying at `MODEL_READY`.

```text
validated artifact
      ↓
M3 Publish
      ↓
BigQuery model table/view
      ↓
publish parity validation
      ↓
Meridian input contract
      ↓
MODEL_READY
      ↓
optional approval
      ↓
Cloud Workflows / Colab Enterprise / Meridian
```

### Autonomous authority

M3 may autonomously:
- create run-scoped/versioned BigQuery model tables;
- create a Meridian-facing view;
- write provenance and manifests;
- generate field/channel mappings;
- verify publish parity.

### Approval boundary

Launching Meridian is approval-gated because modeling configuration choices can materially affect model behavior and interpretation.

For the hackathon, actual Meridian execution is a stretch goal. The required proof is that M3 produces a validated BigQuery artifact and a complete model handoff contract.

## Learning proof

MEL (ModelReady Experience Loop) is embedded inside M3.

A meaningful learned episode should generate:
- **M3 Learning Receipt** when experience is promoted;
- **Experience Applied Receipt** when validated experience materially changes a future execution path.
