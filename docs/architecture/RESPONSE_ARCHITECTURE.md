# PreM3 Response Architecture

**Version:** 1.0.0  
**Status:** Structured response contract implemented. Full Agent Output Evaluation Harness deferred.

This document describes the presentation layer between PreM3 intelligence and human output. It does not duplicate `docs/context/RESPONSE_STYLE_GUIDE.md`.

Canonical human-readable presentation standard: `docs/context/RESPONSE_STYLE_GUIDE.md`.  
Machine contract: `app/response/`.  
Markdown is a fallback renderer, not the parser or source of enum values.

## Pipeline

```text
USER QUESTION / EVENT
        ↓
PREM3 REASONING
        ↓
TOOLS + RUN EVIDENCE
DOMAIN_VIEW
MERIDIAN
AUTHORITY REGISTRY
        ↓
STRUCTURED INTELLIGENCE
        ↓
RESPONSE TYPE SELECTION
        ↓
STRUCTURED RESPONSE CONTRACT
        ↓
OUTPUT QA  (hooks now; full harness later)
        ↓
UI RENDERER / MARKDOWN FALLBACK
        ↓
USER
```

```text
DATA / TOOLS
        ↓
STRUCTURED RUN INTELLIGENCE
        ↓
RESPONSE CONTRACT
        ↓
OUTPUT QA
        ↓
UI
```

DOMAIN_VIEW influences authorized knowledge. Tools establish run truth. Official Meridian supplies official EDA evidence. The response contract presents intelligence. QA evaluates output quality. MEL may later learn from evaluated outcomes.

## Layer boundaries

| Layer | Owns | Must not |
|---|---|---|
| Truth | Facts, calculations, official Meridian, evidence, authority, allowed actions | Presentation layout |
| Semantic / interpretation | What matters, response type, explanation, recommendation from evidence | Inventing numbers, owners, or MODEL_READY |
| Presentation | Title, summary, sections, metrics, findings, actions, owners, authority labels, proof disclosure | Recalculating diagnostics |
| UI | Components, spacing, cards, drawers, tables, progressive disclosure | Determining truth, severity, owner, or MODEL_READY |
| QA | Accuracy, semantics, format, consistency hooks | Promoting lessons |

## Design highlight

**Response Quality = Product Quality.**

Most LLM systems treat generated prose as the final product. PreM3 separates intelligence generation, response semantics, the presentation contract, quality evaluation, and UI rendering. A correct calculation can still fail the user if it is misframed, overlong, missing authority, missing an owner, or inconsistent across equivalent questions.

## Progressive disclosure

1. **Summary** — status, conclusion, top evidence, next action.
2. **Details** — findings, insights, questions, methodology, authority.
3. **Proof** — receipts, fingerprints, BigQuery identity, rule IDs, artifact URIs, raw official Meridian evidence.

Primary chat/UI does not automatically expose Level 3.

## UI component map

The frontend may control layout, color, and collapse. It must not calculate diagnostic state.

| Contract field | Component |
|---|---|
| status | StatusHeader |
| metrics | MetricRow |
| findings | FindingCard |
| insights | InsightCard |
| actions | ActionCard |
| questions | QuestionCard |
| scenarios | ScenarioCard |
| official_meridian | MeridianFindingCard |
| authority | SourceBadge |
| proof / technical_details | ProofDrawer |
| run_status | Timeline |
| learning | LearningDiff |

Status semantics are independent from exact visual colors. Use existing PreM3 brand tokens.

## Output QA

Visual: `docs/architecture/prem3_agent_output_qa_framework.png`

```text
ACCURACY + SEMANTICS + FORMAT + CONSISTENCY
        ↓
   RELIABILITY
        ↓
RESPONSE QUALITY
```

- **Accuracy** — Is it correct and grounded?
- **Semantics** — Is it the right kind of answer?
- **Format** — Is it expressed correctly?
- **Consistency** — Does PreM3 reach materially equivalent conclusions on equivalent questions?

Structured responses expose `qa_hooks` so those checks are inspectable. The full automated Agent Output Evaluation Harness is **not** implemented.

Future evaluation cases should use `OutputEvaluationCase` in `app/response/contracts.py`:

`case_id`, `user_prompt`, `run_context`, `expected_response_type`, `required_facts`, `forbidden_claims`, `expected_authority`, `expected_actions`, `expected_owners`, `expected_status`, `format_expectations`, `semantic_expectations`, `consistency_group`, `evidence_refs`.

Deferred: large prompt corpus, LLM-as-judge, 20-way paraphrase testing, statistical consistency scoring, hallucination benchmark, format score aggregation, production quality dashboard, and MEL learning from response quality.

## Relationship to MEL

```text
RUN → RESPONSE → OUTPUT QA EVIDENCE → ExperienceEpisode evidence
  → MEL evaluation → CandidateLesson → DOMAIN_VIEW
```

`OUTPUT QA → MEL` is **TARGET / FUTURE**.

QA failure does not automatically create a lesson. QA success does not automatically create a lesson. Formatting corrections are not learned lessons. MEL still owns candidate extraction, evaluation, promotion, and DOMAIN_VIEW update.

## Runtime

`present_run_response` and `present_product_response` consume existing artifacts. They do not recalculate diagnostics, mutate DOMAIN_VIEW, or set `MODEL_READY`.
