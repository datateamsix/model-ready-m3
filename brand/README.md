# PreM3 brand implementation

Developer guide for using the approved PreM3 visual identity.

Naming, positioning, and product language live in [`docs/PREM3_BRAND_AND_NAMING.md`](../docs/PREM3_BRAND_AND_NAMING.md). This file tells you **which file to use**.

## Brand identity

**PreM3** — a self-learning, autonomous pre-modeling agent for Google Meridian.

**MAP. MEND. MODEL.**

Before you model, PreM3.

The mark represents fragmented / distributed inputs resolving into a structured model-ready form. Do not rewrite that concept.

## Canonical source directory

`brand/brand-assets/`

Every file there is an **APPROVED_SOURCE_ASSET**. Do not modify, recolor, crop, optimize, or rename those files.

Inventory: [`ASSET_INVENTORY.md`](ASSET_INVENTORY.md)  
Hashes: [`asset-manifest.json`](asset-manifest.json)

## Approved assets

The delivered package is the approved **visual reference + production specification**. Final SVG/PNG masters are **not yet in `assets/`**.

`MASTER_VECTOR_PENDING`

Until masters arrive, use the approved reference rasters. Do not reconstruct the logo.

## Use these assets

| Usage | Path |
|---|---|
| README hero | `brand/brand-assets/reference/prem3-approved-primary-logo-reference.png` |
| Application header | no product UI yet — when one exists, wait for `prem3-logo-primary.svg` |
| Small product icon | `brand/brand-assets/reference/prem3-approved-icon-reference.png` (reference only; too large/white for favicon) |
| Dark background | no standalone inverse file — see tiles on the logo-system board only |
| Light background | primary logo or icon reference PNGs |
| Social / GitHub preview | `brand/brand-assets/reference/prem3-logo-system-concept.png` (candidate; not 1280×640) |
| Reference board | `brand/brand-assets/reference/prem3-approved-brand-board.png` |
| Wordmark only | `brand/brand-assets/reference/prem3-approved-wordmark-reference.png` |
| Palette crop | `brand/brand-assets/reference/prem3-approved-palette-reference.png` |

## Color palette

Hex values from the approved board and tokens:

| Hex | Package token name | Brief name |
|---|---|---|
| `#1A1F4B` | Deep Navy | Navy |
| `#3B4BDB` | Indigo | Indigo |
| `#00C2F5` | Cyan | Cyan |
| `#E6EAF1` | Cool Gray | Light Gray |
| `#F5F7FA` | Light Gray | Off White |

Do not recolor production marks. Do not use brand cyan/navy as ERROR / ATTENTION / INFO / PASS / USER_REQUIRED colors.

Token files (not wired into an app; no frontend exists):

- `brand/brand-assets/tokens/prem3.css`
- `brand/brand-assets/tokens/prem3.tokens.json`
- `brand/brand-assets/tokens/prem3.ts`

## Typography

- Primary / display: Satoshi
- Secondary / UI: Inter

`FONT_IMPLEMENTATION_PENDING`. No font binaries are committed. GitHub README uses GitHub’s native type. Do not add Satoshi to the application until licensed and needed.

The official wordmark is artwork. Do not recreate `PreM3` with live HTML text.

## Clear space / sizing

The delivered package does not define numeric clear-space geometry. Do not invent it.

Small-size rules are in `brand/brand-assets/spec/SMALL_SIZE_SPEC.md`. There is no approved 16/24/32 px export. Do not shrink the full mark for favicons.

## Light backgrounds

Prefer the full-color primary lockup or icon on white / `#F5F7FA`.

## Dark backgrounds

No standalone inverse or transparent lockup was delivered. Inverse and monochrome-light treatments exist only as tiles on `prem3-logo-system-concept.png`. Do not crop or invert.

## App icon

Required `prem3-app-icon-1024.png` is not delivered. Do not generate one.

## README usage

Use the primary lockup PNG at width 640 (native 1130×280). Alt text: `PreM3 — Map. Mend. Model.`

The file has an opaque white background, so GitHub dark mode shows a white plate. Do not generate a reverse logo.

Do not use the full brand board as the README hero.

## Product UI usage

This repository has no web UI, `public/`, favicon, or web manifest. Cloud Run serves the ADK API only.

When a UI exists: use exported masters, not CSS cubes. Keep branding restrained (header / empty state / about). Never brand `meridian_eda_report.html`.

## Social usage

| Future surface | Use |
|---|---|
| GitHub social preview | logo-system board, uploaded in repo Settings (manual) |
| Devpost / article / LinkedIn / slides | primary lockup or brand board |
| Avatar / app tile | wait for approved icon exports |
| Video title card | primary lockup on light, or inverse tile from the system board as a **reference only** until a master exists |

Do not manufacture new collateral here.

## Do not

- redraw the mark
- recreate it with CSS or Lucide
- change the `3` color independently
- recolor logo elements
- stretch, squash, or rotate
- change spacing between icon and wordmark
- add `.ai` to the product lockup
- replace the logo typeface
- put the logo on insufficient-contrast backgrounds
- mix obsolete ModelReady branding with PreM3
- use a generic cube / data icon
- brand official Meridian HTML
- imply Google built or certified PreM3

## Technical asset inventory

See [`ASSET_INVENTORY.md`](ASSET_INVENTORY.md) and [`asset-manifest.json`](asset-manifest.json).
