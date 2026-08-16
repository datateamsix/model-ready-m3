# PreM3 asset inventory

Catalog of every file delivered in `brand/brand-assets/` after visual and technical review on 2026-08-16.

Source-file policy: **APPROVED_SOURCE_ASSET**. Do not modify these files in place.

Machine-readable companion: [`asset-manifest.json`](asset-manifest.json).

## Review summary

| Finding | Detail |
|---|---|
| Files reviewed | 20 |
| Production SVG masters | **none** — `assets/` is a placeholder |
| Production PNG exports (favicon/app/social) | **none** |
| Rasters | 6 approved reference PNGs, all RGB, opaque white backgrounds, no alpha |
| SVGs | none |
| Scripts / external refs in artwork | none (no SVG to inspect) |
| Frontend in this repo | none |

`MASTER_VECTOR_PENDING`. Do not reconstruct, auto-trace, or approximate the mark.

## Visual assets

| File | Role | Size | Dimensions | Alpha | Usage |
|---|---|---|---|---|---|
| `reference/prem3-approved-primary-logo-reference.png` | horizontal lockup | 226.4 KB | 1130×280 | no | README hero; light-background lockup reference |
| `reference/prem3-approved-icon-reference.png` | icon / mark | 75.4 KB | 385×265 | no | icon reference on light |
| `reference/prem3-approved-wordmark-reference.png` | wordmark | 134.7 KB | 715×260 | no | wordmark + tagline reference |
| `reference/prem3-approved-palette-reference.png` | reference | 71.6 KB | 435×265 | no | palette crop |
| `reference/prem3-approved-brand-board.png` | brand board | 997.0 KB | 1448×1086 | no | approved brand system |
| `reference/prem3-logo-system-concept.png` | logo system board | 1.05 MB | 1448×1086 | no | lockup variants; GitHub social-preview candidate |

## Non-visual package files

| File | Role |
|---|---|
| `README.md` | delivered package readme |
| `assets/README_PENDING_MASTER_VECTOR.md` | **UNKNOWN_REVIEW_REQUIRED** — states masters are not delivered |
| `manifest/asset-manifest.json` | required future export filenames |
| `manifest/export-matrix.csv` | required future export sizes |
| `spec/BRAND_SOURCE_OF_TRUTH.md` | approval hierarchy |
| `spec/LOGO_PRODUCTION_SPEC.md` | geometry / wordmark rules |
| `spec/SMALL_SIZE_SPEC.md` | small-size / favicon rules |
| `spec/DEV_IMPLEMENTATION.md` | future frontend notes |
| `spec/DEV_HANDOFF_CHECKLIST.md` | handoff checklist |
| `spec/QA_CHECKLIST.md` | vector-master QA gate |
| `tokens/prem3.css` | color/type tokens |
| `tokens/prem3.tokens.json` | color/type tokens |
| `tokens/prem3.ts` | color/type tokens |
| `tools/compare_logo_reference.py` | optional QA helper (requires Pillow) |

## Light / dark

All delivered rasters are authored on **opaque white**. There is no standalone inverse or transparent lockup file.

Dark-background and monochrome lockups appear only as tiles on the logo-system board. Do not crop or invert them.

GitHub dark mode will show the README hero as a white rectangle. That is expected until a transparent or inverse master is delivered.

## Discrepancies reported (not normalized)

1. **Palette naming:** the mission brief calls `#E6EAF1` Light Gray and `#F5F7FA` Off White. The delivered tokens call `#E6EAF1` Cool Gray and `#F5F7FA` Light Gray. Hex values match. Names were not changed.
2. **Wordmark color split:** production spec says `PreM` navy + `3` cyan. The primary lockup reference reads as `Pre` navy + `M3` cyan. Left as authored.
3. **Stale explanatory copy inside the delivered package:** several spec/token files still say `Map. Mend. Model-Ready.` Current product copy is `Map. Mend. Model.` Source files were not edited.
4. **Token semantic:** `tokens/prem3.css` maps `--prem3-status-model-ready` to cyan. Product status colors must stay separate from brand colors when a UI exists.

## Missing required exports

The inner `manifest/asset-manifest.json` still lists required masters that are **not present**:

- `prem3-logo-primary.svg` and inverse
- `prem3-logo-stacked.svg`
- `prem3-mark.svg` / `prem3-mark-small.svg`
- `prem3-wordmark.svg`
- mono dark/light SVGs
- app icon 1024, social 512, favicons 16/32/48

Do not generate these in this repository.
