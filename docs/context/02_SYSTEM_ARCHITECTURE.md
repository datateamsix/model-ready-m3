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
   │ Gemini     │ │ Determin.  │   │ Isolated      │
   │ reasoning  │ │ tools      │   │ Meridian EDA  │
   │            │ │            │   │ Cloud Run Job │
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
EXPLORING
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
- model-input table created by compiled DDL (`PARTITION BY time`, `CLUSTER BY geo`, column descriptions);
- stable Meridian-facing view;
- `model_ready_runs` registry;
- channel mapping;
- validation results;
- ModelReady Manifest;
- transformation manifest;
- provenance;
- run metadata.

Gemini never chooses BigQuery types, partition fields, clustering, or descriptions. Deterministic schema compilation owns the physical contract. Publishing is complete only after the destination is independently read back and confirmed against the ModelReady Manifest, including physical types, partition, clustering, and column descriptions.

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

CLOUD_TASKMASTER uses one deployed M3 agent plus six run-level tools, including `run_meridian_eda`. Official Meridian pre-modeling EDA is deterministic compute in an isolated Cloud Run Job (`google-meridian==1.8.0` on Python 3.12). It is not a second agent and is not installed in the ADK Cloud Run image. Gemini interprets structured findings; it does not calculate EDA metrics. Eventarc remains future (`AMBIENT_TASKMASTER`). Durable run state is stored in the artifact GCS bucket; Cloud Run `/tmp` is scratch only. See `docs/context/13_CLOUD_TASKMASTER_EXECUTION_MODEL.md`.

## M3 publish and model handoff

The M3 Agent's default **success milestone** is **MODEL_READY**, not merely `READY`. True terminal stages are `FAILED` and `COMPLETE`. `MODEL_READY → LEARNING` and `MODEL_READY → WAITING_FOR_MODEL_APPROVAL` are legal; Phase 1 demos still stop displaying at `MODEL_READY`.

```text
validated artifact
      ↓
ModelReady Manifest (`VALIDATED_FOR_PUBLICATION`)
      ↓
compiled BigQuery DDL (types, descriptions, PARTITION BY time, CLUSTER BY geo)
      ↓
versioned BigQuery model table
      ↓
independent destination read-back
      ↓
stable Meridian-facing view + registry
      ↓
EXPLORING — official Meridian PRE-MODELING EDA
  (EDASpec(); EDA-only sample_prior; never sample_posterior)
      ↓
Gemini interpretation of structured EDAFinding objects
      ↓
confirmation receipt
      ↓
MODEL_READY
      ↓
optional approval (WAITING_FOR_MODEL_APPROVAL)
      ↓
posterior / Meridian model execution
```

### Autonomous authority

M3 may autonomously:
- create run-scoped/versioned BigQuery model tables;
- create a Meridian-facing view;
- write provenance and manifests;
- generate field/channel mappings;
- verify publish parity;
- run official Meridian pre-modeling EDA, including EDA-only `sample_prior`.

### Approval boundary

Launching Meridian posterior sampling or model fitting is approval-gated because modeling configuration choices can materially affect model behavior and interpretation. Autonomous pre-modeling EDA is required for `MODEL_READY` and is not model execution. The EDA gate records official `ModelSpec.knots` and data-adequacy parameters; those values are evidence for `MODEL_READY`, not agent prose. Official input rejection or ERROR findings produce a `USER_REQUIRED` resolution pack. M3 does not silently drop controls, change grain, or choose final knots.

For the hackathon, actual Meridian fitting remains out of scope. The required proof is `PRE_MODELING_COMPLETE` plus evidence-backed `MODEL_READY`.

## Learning proof

MEL (ModelReady Experience Loop) is embedded inside M3.

A meaningful learned episode should generate:
- **M3 Learning Receipt** when experience is promoted;
- **Experience Applied Receipt** when validated experience materially changes a future execution path.
