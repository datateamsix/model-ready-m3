# ModelReady

**Autonomous Data Preparation for Marketing Measurement**

ModelReady is a Taskmaster agent that autonomously transforms fragmented marketing and advertising datasets into validated, model-ready inputs for Google Meridian. Using Gemini, Google ADK, Cloud Run, BigQuery, and Google Cloud storage/event infrastructure, its M3 Agent profiles, maps, safely remediates, validates, publishes, and learns from completed data-preparation workflows.

## M3 Agent

**M3 = Map. Mend. Model-Ready.**

ModelReady is the product. M3 is the autonomous worker. Google Meridian is the first modeling target.

## Hackathon target

Google All Things Agentic Hackathon — **Taskmaster** track.

The required terminal state for the golden path is:

```text
MODEL_READY
✓ deterministic readiness passed
✓ BigQuery model artifact published
✓ publish parity passed
✓ Meridian input contract generated
✓ provenance complete
```

Actual Meridian execution remains approval-gated.

## MVP vertical slice

```text
Upload / fixture
  → M3 / ADK orchestration
  → provider resolution
  → deterministic profiling
  → Meridian-oriented readiness rules
  → safe remediation
  → deterministic validation
  → BigQuery model table/view publish
  → publish parity verification
  → Meridian input contract
  → MODEL_READY
```

## Engineering principle

> LLM decides; deterministic code proves.

Raw inputs are immutable. Every transformation has provenance. Agent prose never marks a run `MODEL_READY`.

## Repository layout

```text
app/
├── agent.py            # ADK root agent / M3 orchestration entrypoint
├── config.py           # environment-driven runtime config
├── core/               # typed contracts, run state, domain errors
├── agents/             # focused reasoning boundaries
├── tools/              # deterministic profiling/remediation/validation/publish
├── integrations/       # GCS, BigQuery, Vertex adapters
├── registry/           # provider-registry schema and sourced provider entries
└── rules/              # versioned Meridian-oriented rule catalog

tests/
├── unit/
├── integration/
├── regression/
└── fixtures/music_center/

evals/                  # ADK evaluation configuration and future datasets
docs/context/           # canonical War Room source of truth
scripts/                # safe bootstrap/demo utilities
deployment/             # Cloud Run/GCP deployment guidance
```

## Local setup

Python 3.13 is the current repo target.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
cp .env.example .env
```

For local Google Cloud development, authenticate with Application Default Credentials and select the hackathon project:

```bash
gcloud auth application-default login
gcloud config set project model-ready-m3
```

Then run the unit checks:

```bash
ruff check app tests
pytest tests/unit
```

## Google Cloud project

Hackathon/development project: `model-ready-m3`.

All project IDs, bucket names, datasets, regions, and model names are configuration-driven. Do not hard-code cloud resource identifiers.

The safe bootstrap script only enables core APIs:

```bash
bash scripts/bootstrap_gcp.sh
```

It intentionally does not create IAM bindings, buckets, datasets, triggers, or deploy services without an explicit implementation step.

## Shared context for coding agents

Before changing architecture or implementation, read:

1. `AGENTS.md`
2. `docs/context/00_HACKATHON_MASTER_CONTEXT.md`
3. `docs/context/02_SYSTEM_ARCHITECTURE.md`
4. the relevant workstream specification

Do not add agents, infrastructure, or SaaS features merely because they may be useful later. The Aug 31 hackathon demo is the current product constraint.

## Current scaffold status

Present now:
- ADK root-agent entrypoint;
- canonical M3 state model;
- typed issue/transformation/publish/learning contracts;
- deterministic inventory, profiling, mapping, remediation, validation, artifact, and BigQuery publish primitives;
- GCS/BigQuery/Vertex integration boundaries;
- versioned readiness-rule catalog seed;
- provider-registry schema and evidence guardrail;
- unit/integration/regression test structure;
- Music Center golden-fixture manifest;
- evaluation config;
- Cloud Run deployment notes and API bootstrap script;
- synchronized War Room context.

## First milestone — do not broaden before this works

A single Music Center dataset must run end-to-end through M3 and reach `MODEL_READY` with a verified BigQuery artifact:

```text
fixture
→ profile
→ detect 3–5 seeded issues
→ make 1–2 AUTO_SAFE repairs
→ deterministic readiness PASS
→ publish BigQuery model table/view
→ publish parity PASS
→ generate Meridian input contract
→ MODEL_READY
```

Only after this vertical slice is reliable should the build expand into deeper provider coverage, MEL/Memory Bank, event-driven ingestion, or UI polish.
