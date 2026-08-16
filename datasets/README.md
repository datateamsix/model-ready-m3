# PreM3 synthetic datasets

Canonical home for complete, reproducible synthetic assignments used for product
proof, integration testing, demos, MEL episodes, and controlled evaluation.

`tests/fixtures/` is reserved for small isolated unit-test fixtures. Do not keep
a second copy of Dataset A, B, or C there.

| Dataset | Business | Role | ID | Seed | Generator | Learning |
|---|---|---|---|---|---|---|
| A | Music Center | `TRAINING_EXPERIENCE` | `dataset_a` / Music Center golden | `20260815` | `scripts/generate_demo_data.py` | First MEL experience. Not a promoted lesson by itself. |
| B | Stride & Field | `LEARNING_EVIDENCE` | `dataset_b_stride_and_field` | `20260817` | `scripts/generate_dataset_b.py` | Independent evidence episode. Generation is not `EXPERIENCE_LEARNED`. |
| C | Summit & Pine | `SEALED_HOLDOUT` | `dataset_c_summit_and_pine` | `20260816` | `scripts/generate_dataset_c.py` | Evaluation holdout. Training, candidate extraction, and promotion access are `DENIED`. |

All three packages are fully synthetic. MEL security boundaries use the typed
`DatasetRole` on the episode, not the folder name.

## Layout

```text
datasets/
├── README.md
├── music_center/dataset_a/          TRAINING_EXPERIENCE
├── music_center/dataset_b/          Music Center related-schema episode (not Stride & Field)
├── stride_and_field/dataset_b/      LEARNING_EVIDENCE
└── summit_and_pine/dataset_c/       SEALED_HOLDOUT
```

Music Center `dataset_b/` is a related Music Center schema-family episode. It is
**not** Stride & Field Dataset B.

## Holdout

Summit & Pine Dataset C was sealed before experiential lesson promotion.
`lesson_ids_visible_at_seal` is empty. Do not feed Dataset C into
CandidateLesson generation, evidence sufficiency, or DOMAIN_VIEW construction.

Manifests: `datasets/summit_and_pine/dataset_c/package_manifest.json` and
`learning/holdout_manifest.json`.
