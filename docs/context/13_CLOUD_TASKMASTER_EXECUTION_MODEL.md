# Cloud Taskmaster execution model

CLOUD_ALIVE proved that PreM3 runs on private Cloud Run as `m3-runtime`.

CLOUD_TASKMASTER proves that the same deployed agent can perform a real Dataset A preparation task:

```text
Immutable GCS package
        ↓
Gemini / ADK
        ↓
observes run
        ↓
chooses authorized action
        ↓
    six run-level tools
        ↓
RunCoordinator enforces authority
        ↓
deterministic tools execute
        ↓
evidence generated
        ↓
compiled BQ DDL (partition/cluster/descriptions)
        ↓
BigQuery publish + independent destination proof
        ↓
stable consumption view + registry
        ↓
Meridian contract
        ↓
EXPLORING
        ↓
isolated Meridian EDA Cloud Run Job
        ↓
structured EDAFinding receipt + official HTML
        ↓
Gemini interpretation
        ↓
MODEL_READY
```

The agent decides. The coordinator constrains. The tools execute. The evidence proves.

## Six run-level tools

The deployed root agent is not given low-level file-mutating primitives. Normal cloud execution uses:

| Tool | Purpose |
|---|---|
| `initialize_dataset_run` | Create/resume the bound Evaluation. No package URI, tenant, or run_id arguments. |
| `inspect_dataset_run` | Read-only durable state reconstruction. No run_id argument. |
| `apply_safe_remediations` | Request AUTO_SAFE repairs by issue ID only |
| `validate_and_publish_run` | Readiness, BigQuery publish, parity, Meridian contract. Destinations are server-owned. |
| `run_meridian_eda` | Official google-meridian pre-modeling EDA in an isolated Cloud Run Job. I/O from run state. |
| `complete_dataset_run` | Request evidence-backed `MODEL_READY` with optional EDA analysis |

Trusted CLI/cloud-proof callers bind `ExecutionContext` (or use
`prepare_legacy_dataset_execution`) before the agent runs. The model cannot
supply package URIs or run IDs.

Read-only context tools remain available: `get_meridian_pocket_card`, `lookup_provider_card`, `search_provider_directory`, `cloud_runtime_probe`.

Phase 1 ADK wrappers still exist as library functions. They are not exposed on the deployed agent.

## Agent vs coordinator vs engine

Gemini / M3 owns:

- which authorized run operation should happen next;
- whether observed AUTO_SAFE issues should be remediated;
- when to request validation/publication;
- when to request official Meridian EDA;
- how to interpret structured EDA findings;
- when to request final completion;
- recognizing when a run cannot proceed.

The coordinator owns:

- run state and legal transitions;
- issue lifecycle;
- deterministic remediation execution;
- artifact creation;
- validation and publication sequencing;
- fail-closed behavior.

Deterministic tools own calculations, fingerprints, provenance, readiness, BigQuery parity, the Meridian contract, official Meridian EDA, and the `MODEL_READY` gate.

Gemini may never:

- manipulate pandas;
- write SQL;
- choose arbitrary filesystem paths;
- modify raw data;
- supply a PASS string;
- mark an issue `RESOLVED`;
- mark a run `MODEL_READY`;
- calculate EDA metrics or override ERROR / ATTENTION / INFO;
- call `sample_posterior` or fit Meridian;
- bypass approval or the coordinator.

## Isolated Meridian EDA worker

`google-meridian==1.8.0` is not installed in the M3 ADK Cloud Run image (Python 3.13 / pandas 3). Official install docs require Python 3.11 or 3.12. Pre-modeling EDA therefore runs in an isolated Cloud Run Job on Python 3.12.

EDA idempotency key:

`run_id + model_input_fingerprint + meridian_version + eda_config_fingerprint`

A matching receipt plus HTML is replayed and does not start a new job.

## Issue IDs, not transform parameters

`apply_safe_remediations(run_id, issue_ids)` is the agentic decision boundary.

The agent selects issue IDs. The deterministic remediation plan registered to each stored issue supplies date formats, aggregations, channel maps, and output paths. Gemini cannot choose those implementation details.

## Durable run layout

Cloud Run local disk is scratch only (`/tmp/modelready/<run_id>/`). Durable evidence lives in the artifact bucket:

```text
gs://<artifact-bucket>/<org>/<workspace>/runs/<run_id>/
    run_state.json
    run_summary.json
    issues.json
    model_ready.csv
    readiness_report.json
    transformation_manifest.json
    provenance.json
    meridian_input_contract.json
    publish_receipt.json
    model_ready_manifest.json
    eda/meridian_eda_request.json
    eda/meridian_eda_report.html
    eda/meridian_eda_receipt.json
    eda/meridian_eda_config.json
    eda/m3_eda_analysis.json
    eda/pre_modeling_handoff.md
    trajectory/agent_trajectory_receipt.json
```

A run can be reconstructed after the in-memory coordinator and local scratch are destroyed. `run_id` is idempotent: the same id plus the same package fingerprint resumes; a different fingerprint fails closed; a completed run returns the existing `MODEL_READY` evidence and does not rerun transforms or republish.

## Manual package invocation

Dataset A is staged by the developer identity into the raw bucket. The runtime service account remains read-only against raw. The judge/developer then sends M3 one task prompt containing the `gs://` URI.

Eventarc, Pub/Sub, and `trigger_sources` are out of scope for this milestone.
