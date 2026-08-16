# PreM3 Brand Production Handoff — v1.0

**Status:** Approved visual direction + production specification  
**Date:** 2026-08-15  
**Brand:** PreM3  
**Lockup tagline:** `MAP. MEND. MODEL.`  
**Product meaning / explanatory copy:** `Map. Mend. Model-Ready.`

This package turns the approved PreM3 brand board into an implementation contract for design and frontend teams.

## The one rule that matters most

**Do not reconstruct the PreM3 mark from generic CSS squares, an icon library, a cube component, or an auto-traced approximation.** The resolving-cube artwork is the brand. Its spacing, perspective, tile proportions, trailing fragments, and color progression must be preserved from the approved reference.

The PNGs in `reference/` are the **visual source of truth** for fidelity review. They are not substitutes for the final master vector.

## Required production masters

The design owner should create and approve the following vector masters in Figma (or equivalent), then export the filenames exactly as listed in `manifest/asset-manifest.json`:

- primary horizontal logo
- icon / brand mark
- wordmark
- stacked lockup
- inverse lockup
- monochrome dark
- monochrome light
- small-size simplified mark

The vector masters should use explicit vector paths / outlined wordmark artwork. The official logo should **not** depend on a runtime webfont.

## Package structure

- `reference/` — approved brand board and visual comparison crops
- `spec/` — logo geometry, small-size, implementation, and QA guidance
- `tokens/` — canonical color and typography tokens
- `manifest/` — required filenames and export matrix
- `tools/` — optional visual-diff helper for QA
- `assets/` — reserved for final approved SVG/PNG masters

## Canonical palette

| Token | Hex | Purpose |
|---|---|---|
| Deep Navy | `#1A1F4B` | primary identity, text, trust |
| Indigo | `#3B4BDB` | transformation / transition |
| Cyan | `#00C2F5` | resolved state, accent, numeral `3` |
| Cool Gray | `#E6EAF1` | unresolved fragments, borders |
| Light Gray | `#F5F7FA` | backgrounds / surfaces |

## Typography

- **Brand / display:** Satoshi
- **UI / product:** Inter
- The official `PreM3` wordmark should be exported as artwork/outlines; do not recreate it with live HTML text.
- Do not distribute font files in this package. Use the organization's licensed webfont source where applicable.

## Brand color logic

The icon is not a random multicolor cube. The approved progression is semantic:

`unresolved / trailing gray → structured navy → restrained indigo transition → resolved cyan face`

Keep cyan concentrated on the resolved face and the `3`. Avoid using cyan as a decorative fill everywhere in the product.

## First implementation check

Before merging frontend use of the logo, render the candidate SVG on white at the same dimensions as `reference/prem3-approved-primary-logo-reference.png` and compare visually at 100%, 50%, and 25% scale. Review the cube silhouette, tile spacing, fragment positions, wordmark weight, divider, and cyan placement.

See `spec/QA_CHECKLIST.md` for the complete acceptance gate.
