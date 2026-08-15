# Cursor handoff — immediate task

Read `AGENTS.md`, `PHASE1.md`, `tests/fixtures/music_center/README.md`, and the canonical context before coding.

Your immediate goal is **not** to productize ModelReady. Your goal is to make the Phase 1 golden vertical slice executable and testable.

## Synthetic fixture is already built

Do **not** redesign or reimplement the Music Center generator before starting the vertical slice.

Materialize Dataset A with:

```bash
python scripts/generate_demo_data.py --dataset dataset_a
```

Then run:

```bash
pytest tests/unit/test_demo_data_generator.py
```

Dataset A contains exactly five declared Phase 1 defects. Their IDs, expected evidence, remediation classes, and rule families are in `tests/fixtures/music_center/expected_manifest.json`.

`dataset_a/expected_model_ready_weekly.csv` is regression ground truth only. **M3 must never read this file as an input or use it to decide how to transform the raw package.** Tests may compare M3's independently generated final artifact against it after execution.

Dataset B is reserved for the later MEL / `EXPERIENCE_APPLIED` demonstration. Do not bring it into Phase 1 implementation.

## First implementation package

1. Run the fixture generator and confirm its contract test passes.
2. Implement deterministic detectors for the five Dataset A defects:
   - exact duplicate campaign row;
   - Google/Meta date-format mismatch;
   - daily Google Ads vs weekly target grain;
   - Meta currency-formatted `amount_spent`;
   - inconsistent Meta channel labels.
3. Implement only the AUTO_SAFE repairs needed for the vertical slice, with provenance.
4. Create a synchronous run coordinator that records canonical state transitions and invokes tools; do not add more specialist agents yet unless required by ADK execution.
5. Aggregate campaign-level data only through explicit deterministic mappings and preserve source-to-target provenance.
6. Produce the local normalized/model-ready artifact and transformation manifest.
7. Compare the independently produced result against regression truth in tests; never expose the truth file to runtime orchestration.
8. Publish the validated artifact to a run-scoped BigQuery table/view and implement row/schema/fingerprint parity checks.
9. Generate the minimum Meridian input contract.
10. Only the deterministic completion gate may set `MODEL_READY`.

## Stop condition

Stop and report back when Dataset A reaches the full terminal-state contract:

```text
MODEL_READY
✓ deterministic readiness passed
✓ BigQuery model artifact published
✓ publish parity passed
✓ Meridian input contract generated
✓ provenance complete
```

Do not continue into MEL/Memory Bank, Dataset B, additional providers, SaaS auth/billing, or UI polish without review.
