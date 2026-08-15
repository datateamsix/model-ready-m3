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

- `app/` — M3 agent, API, deterministic tools, integrations, rules, provider registry
- `tests/` — unit, integration, regression and golden demo fixtures
- `evals/` — ADK evaluation datasets/configuration
- `docs/context/` — canonical hackathon/product/architecture source of truth
- `scripts/` — local/bootstrap/demo utilities
- `deployment/` — Cloud Run/GCP deployment notes

## GCP project

Development/hackathon project: `model-ready-m3`

All project IDs, bucket names, datasets, regions, and model names must be configuration-driven. Do not hard-code cloud resource identifiers.

## First milestone

A single Music Center dataset must run end-to-end through M3 and reach `MODEL_READY` with a verified BigQuery artifact before broader feature work begins.
