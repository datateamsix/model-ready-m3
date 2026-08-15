# Phase 1 — Vertical Slice

**Target window:** Aug 14–17, 2026  
**Exit condition:** one Music Center dataset runs end to end and reaches `MODEL_READY` with a verified BigQuery model artifact.

## Current status

- [x] Deterministic Music Center Dataset A/B generator implemented.
- [x] Dataset A ground-truth manifest defines exactly five Phase 1 defects.
- [x] Regression-truth artifact design and generator contract test added.
- [ ] Synchronous M3 vertical slice reaches `MODEL_READY`.

## P0 implementation order

1. **DONE — Synthetic fixture.** Generate deterministic Music Center `dataset_a` with exactly five seeded Phase 1 defects and machine-readable ground truth.
2. Build a synchronous M3 run coordinator around the canonical state machine.
3. Wire inventory/profile → issue detection → AUTO_SAFE remediations → re-validation.
4. Persist transformed artifact and provenance locally first.
5. Compare the independently generated final artifact against synthetic regression truth in tests. Runtime M3 must never read the truth artifact as an input.
6. Publish the validated artifact to a run-scoped BigQuery table/view.
7. Implement row/schema/fingerprint parity checks and publish receipt.
8. Generate the minimum Meridian input contract.
9. Set `MODEL_READY` only after all deterministic gates pass.
10. Deploy the working path to Cloud Run.
11. Add GCS/Eventarc ingestion only after the synchronous path is reliable.

## Dataset A Phase 1 defects

The five expected issues are declared in `tests/fixtures/music_center/expected_manifest.json`:

- exact duplicate Google Ads campaign row;
- Google/Meta date-format mismatch;
- daily Google Ads vs weekly target grain;
- currency-formatted Meta `amount_spent`;
- inconsistent Meta channel labels.

Generate the fixture with:

```bash
python scripts/generate_demo_data.py --dataset dataset_a
```

## Explicit non-goals for Phase 1

- Stripe/Clerk/auth productization
- full provider registry
- Memory Bank / MEL learning implementation
- Dataset B / Experience Applied execution
- full Meridian model execution
- large dashboard/UI
- Terraform or elaborate CI/CD
- multiple unrelated demo scenarios

## Acceptance proof

```text
Music Center dataset_a
→ M3 run_id created
→ PROFILING
→ 5 known issues found
→ safe fixes applied with provenance
→ VALIDATING PASS
→ PUBLISHING
→ BigQuery table/view written
→ publish parity PASS
→ Meridian contract generated
→ MODEL_READY
```

All displayed metrics must be generated from real run evidence.
