# Experiential Learning Framework

## Purpose

Demonstrate that ModelReady gets better from evaluated experience.

Memory alone is not learning.

**Learning is present only when a prior evaluated episode causes a measurable improvement in a future decision or execution path.**

## Framework name

Working name: **ModelReady Experience Loop (MEL)**

MEL is the learning engine embedded in the **M3 Agent**. ModelReady is the product; M3 is the autonomous worker; MEL is how M3 learns from evaluated experience.

```text
EXPERIENCE
   ↓
EVALUATE
   ↓
EXTRACT CANDIDATE LESSON
   ↓
VALIDATE / REGRESSION TEST
   ↓
PROMOTE
   ↓
RETRIEVE ON SIMILAR CASE
   ↓
ADAPT DECISION / TOOL PATH
   ↓
MEASURE IMPROVEMENT
```

## 1. Episode capture

Every completed run becomes an `ExperienceEpisode`.

Suggested schema:

```json
{
  "episode_id": "...",
  "run_id": "...",
  "dataset_fingerprint": "...",
  "context": {
    "providers": [],
    "report_types": [],
    "grain": {},
    "schema_signatures": []
  },
  "trajectory": [
    {
      "step": 1,
      "agent": "resolver",
      "decision": "...",
      "tool": "...",
      "inputs_hash": "...",
      "result_summary": "..."
    }
  ],
  "issues_detected": [],
  "actions_taken": [],
  "human_feedback": [],
  "validator_results_before": {},
  "validator_results_after": {},
  "final_outcome": "MODEL_READY",
  "cost": {},
  "latency": {},
  "agent_version": "...",
  "policy_version": "..."
}
```

## 2. Evaluation

Use multiple evidence classes.

### A. Deterministic outcome evaluation
Highest authority.

Examples:
- output contains no prohibited missing values;
- dates are valid;
- media/spend channel mapping is complete;
- row grain is consistent;
- known synthetic defects were detected;
- Meridian loader compatibility succeeds.

### B. ADK trajectory evaluation
Evaluate:
- expected tool ordering;
- unnecessary calls;
- missing calls;
- tool parameter quality;
- multi-turn task success.

### C. Human feedback
Capture explicit:
- accepted/rejected mapping;
- accepted/rejected remediation;
- corrected provider identity;
- corrected channel taxonomy.

### D. LLM rubric evaluation
Useful for:
- explanation quality;
- reasoning completeness;
- confidence calibration.

Never allow LLM rubric evaluation to override deterministic failure.

## 3. Candidate lesson extraction

The evaluator generates structured `CandidateLesson` records.

```json
{
  "lesson_id": "...",
  "type": "schema_mapping|remediation_policy|routing|provider_quirk",
  "scope": {
    "provider": "meta_ads",
    "report_family": "campaign_performance",
    "schema_signature": "..."
  },
  "condition": "...",
  "recommended_action": "...",
  "evidence_episode_ids": ["..."],
  "success_count": 3,
  "failure_count": 0,
  "confidence": 0.94,
  "risk": "LOW",
  "status": "CANDIDATE"
}
```

## 4. Lesson promotion policy

A candidate may become `VALIDATED` only if:

1. deterministic output improved or remained correct;
2. the lesson is scoped;
3. supporting evidence exists;
4. known regression cases pass;
5. no safety guardrail is weakened.

Suggested promotion tiers:

### Tier 0 — Observation
Stored for analytics only.

### Tier 1 — Candidate
Can be surfaced to developers/evaluator but not used automatically.

### Tier 2 — Validated hint
May be retrieved to influence reasoning but cannot bypass deterministic validation.

### Tier 3 — Validated policy
May alter routing or select a safe transformation automatically.

No lesson can disable final validators.

## 5. Memory design

Use Vertex AI Memory Bank for concise validated knowledge that should influence future reasoning.

Use BigQuery as the auditable source of truth for:
- episodes;
- evidence;
- scores;
- promotion history;
- regressions.

Memory Bank is a retrieval surface, not the authoritative ledger.

## 6. Retrieval

Before mapping/remediation, query validated lessons using context:
- provider;
- report family;
- schema signature;
- field names;
- grain;
- defect type.

Retrieved lessons enter the run as **advisory context** with:
- lesson ID;
- confidence;
- scope;
- evidence count.

## 7. Improvement measurement

For comparable episodes track:

- mapping accuracy;
- issue detection precision/recall;
- number of tool calls;
- number of approval requests;
- runtime;
- token usage;
- final readiness;
- trajectory score.

A lesson is useful only if these remain safe and at least one improves.

Where a run publishes to BigQuery, also evaluate:
- publish success;
- row/schema parity;
- model-contract completeness;
- provenance completeness.

## 8. ADK optimization

Use ADK optimization **offline / controlled**, not as uncontrolled runtime self-editing.

Candidate process:

1. accumulate evaluated episodes;
2. create train/eval sets;
3. run ADK optimization against selected agent instructions/policies;
4. test candidate optimized agent on held-out regression suite;
5. compare against baseline;
6. version/publish only if it passes.

This produces a strong technical story:

> **Experience updates memory continuously; policy optimization happens only after evaluation and regression.**

## 9. Demo of learning

The demo should show learning in two episodes.

### Episode A — First encounter

Meta export includes an unfamiliar field alias and campaign taxonomy.

Agent:
- proposes mapping;
- receives a correction or deterministic confirmation;
- completes run;
- evaluator extracts lesson;
- lesson passes micro-regression;
- lesson becomes validated.

UI:
`M3 LEARNING RECEIPT`
`EXPERIENCE LEARNED`
`meta_ads.amount_spent → media_spend`
`confidence: 0.96`
`evidence: 1 validated episode`

### Episode B — Similar future dataset

Second package arrives with the same report family but different campaigns.

Agent:
- retrieves validated lesson;
- maps immediately;
- avoids the prior ambiguity/approval;
- uses fewer steps;
- output still passes deterministic validators.

UI:
`EXPERIENCE APPLIED`

UI comparison:

| Metric | First run | Learned run |
|---|---:|---:|
| Mapping confidence | 0.71 | 0.96 |
| Approval requests | 1 | 0 |
| Resolver tool calls | 6 | 3 |
| Validation | PASS | PASS |

The exact values must come from the actual demo runs, not hard-coded marketing claims.

## 10. Anti-patterns

Do not:
- claim chat history is learning;
- write every run directly into prompt rules;
- let one bad episode poison policy;
- use private/raw data as generalized memory;
- auto-promote high-risk transformations;
- optimize on the same cases used for final evaluation;
- hide lesson provenance.

## 11. M3 Learning Receipts

Learning Receipts are first-class proof artifacts.

### Experience Learned receipt
Generated when a candidate lesson is promoted.

Minimum fields:
- episode/run;
- observed condition;
- decision/action;
- deterministic evidence;
- risk;
- confidence;
- scope;
- promotion state;
- regression fixture;
- expected future behavior.

### Experience Applied receipt
Generated when a validated lesson changes a later run.

Minimum fields:
- lesson ID;
- evidence count;
- previous behavior;
- current behavior;
- measured change;
- final deterministic validation.

A receipt may reference BigQuery publication evidence when the learned behavior affects the final model artifact.
