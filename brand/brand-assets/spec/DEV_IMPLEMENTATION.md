# Frontend Implementation

## Never build the logo from HTML/CSS primitives

Use the approved exported SVG file as an `<img>`, framework image asset, or inline SVG only when inline control is necessary. The brand mark is artwork, not a reusable grid component.

## Recommended asset use

- Site header / marketing navigation: `prem3-logo-primary.svg`
- Product sidebar / compact header: `prem3-mark.svg` or `prem3-mark-small.svg`
- Dark hero/footer: `prem3-logo-primary-inverse.svg`
- Social metadata image composition: PNG export derived from master artwork
- Favicon: dedicated small-size export; never browser-scale the full lockup

## Example CSS tokens

Import `tokens/prem3.css` and use semantic tokens rather than copying hex values into components.

## Accessibility

- Give the primary logo image alt text `PreM3` unless adjacent text already provides the brand name, in which case use an empty alt attribute.
- Decorative brand marks should use empty alt text.
- Maintain adequate surrounding contrast; do not rely on the Cyan `3` as body text on white at small sizes.

## Theme mapping

The identity palette is not a mandate to make the entire application blue. Deep Navy should carry trust/structure, Indigo should be selective, and Cyan should signal resolved/active/completion states.

Suggested semantics:
- `--prem3-status-model-ready`: Cyan
- `--prem3-brand-primary`: Deep Navy
- `--prem3-brand-transition`: Indigo
- `--prem3-border-subtle`: Cool Gray
- `--prem3-surface-subtle`: Light Gray
