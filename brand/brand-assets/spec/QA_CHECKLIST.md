# QA Checklist — Logo Acceptance Gate

Do not merge production logo assets until all applicable items pass.

## Geometry

- [ ] Candidate was manually recreated/cleaned as vector artwork; not shipped from a blind auto-trace.
- [ ] Overall silhouette matches the approved reference.
- [ ] Trailing fragment count, placement, size relationships, and perspective visually match the reference.
- [ ] Structural navy tiles match the approved spacing and apparent depth.
- [ ] Cyan resolved face matches the reference.
- [ ] Indigo transition/top-plane usage matches the reference.
- [ ] White channels/gaps have consistent visual rhythm.

## Wordmark

- [ ] `PreM` weight matches the approved bold wordmark.
- [ ] `3` is Cyan `#00C2F5`.
- [ ] Wordmark is exported as vector artwork, not runtime browser typography.
- [ ] Divider position and weight match the reference.
- [ ] Tagline tracking and hierarchy match the reference when present.

## Color

- [ ] Deep Navy `#1A1F4B`.
- [ ] Indigo `#3B4BDB`.
- [ ] Cyan `#00C2F5`.
- [ ] Cool Gray `#E6EAF1`.
- [ ] Light Gray `#F5F7FA`.
- [ ] No random tile recoloring.

## Responsive / export

- [ ] Full logo tested at 100%, 50%, and 25% of reference size.
- [ ] Mark tested at 16, 32, 48, 64, 128, and 512 px.
- [ ] Light-background and dark-background variants tested.
- [ ] SVG has a tight, correct `viewBox` with no excessive whitespace.
- [ ] SVG has no embedded raster image.
- [ ] SVG has no external font dependency.
- [ ] PNG exports are generated from the approved master, not independently redrawn.

## Final visual approval

- [ ] Candidate rendered next to `reference/prem3-approved-primary-logo-reference.png`.
- [ ] Design owner approved side-by-side fidelity.
