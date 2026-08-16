# Agent Delegation and Guardrails

## Purpose

Allow Cursor, Codex, Claude Code and human development to operate in parallel without architecture drift while preserving the canonical PreM3 system boundaries.

## Shared source of truth

Every coding agent must read:
1. `README.md`
2. `00_HACKATHON_MASTER_CONTEXT.md`
3. `02_SYSTEM_ARCHITECTURE.md`
4. the workstream-specific spec.

## Suggested delegation

### Claude Code — Frontend / demo console
Own:
- upload UI;
- PreM3 run timeline;
- readiness report;
- issue cards;
- BigQuery publish status;
- `MODEL_READY` state;
- artifact download;
- PreM3 Learning Receipt / Experience Applied UI;
- learning comparison visualization;
- Cloud Run API integration.

Guardrail:
Do not invent backend contracts. Use checked-in API schemas.

### Cursor — Provider registry / data tools
Own:
- registry schema;
- seed provider definitions;
- profiling;
- deterministic transforms;
- canonical mapping structures.

Guardrail:
All transforms require tests and provenance.

### Codex / OpenAI coding agent — ADK backend / evaluation
Own:
- M3 orchestrator;
- state machine;
- ADK agents/tools;
- BigQuery agent telemetry;
- BigQuery model-artifact publisher;
- publish-parity validator;
- Meridian input-contract generator;
- Memory Bank;
- episode/evaluation pipeline;
- PreM3 Learning Receipt generation;
- regression harness.

Guardrail:
Never allow agent prose to mark a run `MODEL_READY`. `MODEL_READY` requires deterministic readiness validation, verified BigQuery publish parity, a complete Meridian handoff contract, and official pre-modeling EDA with zero ERROR findings.

### Human lead
Own:
- product decisions;
- Meridian interpretation policy;
- scope;
- judge-facing claims;
- final review;
- demo narrative;
- judge-facing claims.

## Interface contracts

### Run status event

```json
{
  "run_id": "...",
  "stage": "PROFILING",
  "status": "RUNNING",
  "message": "...",
  "timestamp": "...",
  "progress": 0.35
}
```

### Issue

```json
{
  "issue_id": "...",
  "rule_id": "MR-006",
  "severity": "ERROR",
  "title": "...",
  "evidence": {},
  "remediation_class": "AUTO_SAFE",
  "proposed_action": {},
  "status": "OPEN"
}
```

### Transformation

```json
{
  "action_id": "...",
  "tool": "aggregate_to_week",
  "source_fields": [],
  "target_fields": [],
  "parameters": {},
  "reason": "...",
  "lesson_ids": [],
  "status": "APPLIED"
}
```

## Engineering rules

1. Type all contracts.
2. Keep raw inputs immutable.
3. Transform into versioned output.
4. Every transformation writes provenance.
5. No nondeterministic calculation where deterministic code works.
6. Prompts are versioned.
7. Rules are versioned.
8. Registry entries include evidence/source.
9. Do not silently swallow errors.
10. Tests accompany transformations.
11. Do not merge features that break the golden demo.
12. Optimize for judge-visible evidence.

## PR checklist

- Does this support a rubric item?
- Does it preserve provenance?
- Is it testable?
- Does it make the demo stronger?
- Is it in scope before Aug 31?
- Does it introduce hidden manual steps?
- Does it weaken deterministic validation?

### BigQuery Publish Contract

```json
{
  "run_id": "...",
  "status": "PUBLISHED",
  "project_id": "...",
  "dataset_id": "...",
  "table_id": "...",
  "view_id": "...",
  "row_count": 0,
  "schema_fingerprint": "...",
  "artifact_fingerprint": "...",
  "parity_status": "PASS",
  "meridian_contract_uri": "...",
  "provenance_uri": "..."
}
```

### Learning Receipt Contract

```json
{
  "receipt_id": "...",
  "receipt_type": "EXPERIENCE_LEARNED|EXPERIENCE_APPLIED",
  "run_id": "...",
  "lesson_id": "...",
  "evidence": [],
  "confidence": 0.0,
  "risk": "LOW|MEDIUM|HIGH",
  "measured_change": {},
  "validation_status": "PASS"
}
```

## Additional engineering rules

13. PreM3 is the product and the autonomous pre-modeling agent. M3 is the Map. Mend. Model. operating method.
14. In Map. Mend. Model., Model means constructing and proving the model-consumption package, not fitting Meridian.
15. Publishing a validated run-scoped/versioned model artifact to BigQuery is allowed autonomously.
16. A run is not `MODEL_READY` until BigQuery publish parity passes, the Meridian handoff contract is complete, official pre-modeling EDA reports zero ERROR findings, and the modeler handoff is persisted.
17. Official pre-modeling EDA is autonomous. Posterior / model fitting remains outside autonomous authority. Official rejection or ERROR findings produce `USER_REQUIRED` guidance (`agent_can_fix=false`).
18. Model parameters/priors must never be silently selected merely to complete an autonomous workflow.
19. PreM3 Learning Receipts must be generated from real evidence, never hard-coded demo metrics.
20. Do not use nondeterministic calculation where deterministic code works.
