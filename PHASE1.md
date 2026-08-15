# Phase 1 — Vertical Slice

**Target window:** Aug 14–17, 2026  
**Exit condition:** one Music Center dataset runs end to end and reaches `MODEL_READY` with a verified BigQuery model artifact.

## P0 implementation order

1. Generate deterministic Music Center `dataset_a` fixture with 3–5 seeded defects and expected-answer manifest.
2. Build a synchronous M3 run coordinator around the canonical state machine.
3. Wire inventory/profile → issue detection → 1–2 AUTO_SAFE remediations → re-validation.
4. Persist transformed artifact and provenance locally first.
5. Publish the validated artifact to a run-scoped BigQuery table/view.
6. Implement row/schema/fingerprint parity checks and publish receipt.
7. Generate the minimum Meridian input contract.
8. Set `MODEL_READY` only after all deterministic gates pass.
9. Deploy the working path to Cloud Run.
10. Add GCS/Eventarc ingestion only after the synchronous path is reliable.

## Explicit non-goals for Phase 1

- Stripe/Clerk/auth productization
- full provider registry
- Memory Bank / MEL learning implementation
- full Meridian model execution
- large dashboard/UI
- Terraform or elaborate CI/CD
- multiple unrelated demo scenarios

## Acceptance proof

```text
Music Center dataset_a
→ M3 run_id created
→ PROFILING
→ 3–5 known issues found
→ 1–2 safe fixes applied with provenance
→ VALIDATING PASS
→ PUBLISHING
→ BigQuery table/view written
→ publish parity PASS
→ Meridian contract generated
→ MODEL_READY
```

All displayed metrics must be generated from real run evidence.
