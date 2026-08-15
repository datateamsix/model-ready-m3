# Phase 1 — Vertical Slice

**Target window:** Aug 14–17, 2026  
**Exit condition:** one Music Center dataset runs end to end and reaches `MODEL_READY` with a verified BigQuery model artifact.

## Current status

- [x] Deterministic Music Center Dataset A/B generator implemented.
- [x] Dataset A ground-truth manifest defines exactly five Phase 1 defects.
- [x] Regression-truth artifact design and generator contract test added.
- [x] Synchronous M3 vertical slice reaches `MODEL_READY`.

**Phase 1 Golden Slice:** COMPLETE  
**Pre-Cloud Hardening:** COMPLETE  
**Cloud Run private runtime (`CLOUD_ALIVE`):** COMPLETE  
**CLOUD_TASKMASTER:** COMPLETE when proven  
**Eventarc / Ambient:** NEXT

## P0 implementation order

1. **DONE — Synthetic fixture.** Generate deterministic Music Center `dataset_a` with exactly five seeded Phase 1 defects and machine-readable ground truth.
2. **DONE — Run coordinator.** Synchronous M3 coordinator around the canonical state machine.
3. **DONE — Inventory/profile → issue detection → AUTO_SAFE remediations → re-validation.**
4. **DONE — Transformed artifact and provenance persist locally.**
5. **DONE — Independently generated final artifact compared against synthetic regression truth in tests.** Runtime M3 never reads the truth artifact as an input.
6. **DONE — Publish the validated artifact to a run-scoped BigQuery table.**
7. **DONE — Row/schema/key/content parity checks and publish receipt.**
8. **DONE — Minimum Meridian input contract.**
9. **DONE — `MODEL_READY` only after all deterministic gates pass.**
10. **DONE — Private Cloud Run ADK API (`CLOUD_ALIVE`).** Runtime identity is `m3-runtime`. Vertex remains `global`.
11. **IN PROGRESS —** Agent-driven Dataset A execution on Cloud Run (`CLOUD_TASKMASTER`) using five run-level tools. Do not add Eventarc until that path is proven.

## Dataset A Phase 1 defects

The five expected issues are declared in `tests/fixtures/music_center/expected_manifest.json`:

- exact duplicate Google Ads campaign row;
- Google/Meta date-format mismatch;
- daily Google Ads vs weekly target grain;
- currency-formatted Meta `amount_spent`;
- inconsistent Meta channel labels.

A successful Dataset A run must prove `detected=5`, `resolved=5`, `open=0`, with each resolved issue linked to the transform that repaired it.

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
→ 5 issues resolved with provenance
→ VALIDATING PASS
→ PUBLISHING
→ BigQuery table/view written
→ publish parity PASS
→ Meridian contract generated
→ MODEL_READY (success milestone, not a hard terminal state)
```

All displayed metrics must be generated from real run evidence. See `docs/context/12_PHASE1_EVIDENCE_MODEL.md`.
