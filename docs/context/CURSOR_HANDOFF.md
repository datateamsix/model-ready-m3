# Cursor handoff — immediate task

Read `AGENTS.md`, `PHASE1.md`, and the canonical context before coding.

Your immediate goal is **not** to productize ModelReady. Your goal is to make the Phase 1 golden vertical slice executable and testable.

## First implementation package

1. Implement `scripts/generate_demo_data.py` to create deterministic Music Center `dataset_a` fixtures.
2. Seed exactly 3–5 defects first: exact duplicates, date-format mismatch, currency-formatted spend, inconsistent channel label, and one temporal-grain issue.
3. Update `expected_manifest.json` with machine-readable expected locations/counts where practical.
4. Add deterministic tests for each defect detector and AUTO_SAFE repair.
5. Create a run coordinator that records canonical state transitions and invokes tools; do not add more specialist agents yet unless required by ADK execution.
6. Produce local artifacts and provenance before wiring BigQuery.
7. Then publish to a run-scoped BigQuery table/view and implement parity checks.
8. Generate the minimum Meridian input contract.
9. Only the deterministic completion gate may set `MODEL_READY`.

## Stop condition

Stop and report back when one local dataset reaches the full terminal-state contract. Do not continue into MEL, additional providers, SaaS auth/billing, or UI polish without review.
