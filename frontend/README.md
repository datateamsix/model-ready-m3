# PreM3 Frontend

The judge-facing operations console for **PreM3** — a self-learning, autonomous pre-modeling
agent for Google Meridian. **Map. Mend. Model.**

This app renders PreM3's typed run intelligence (`StructuredResponse`, run state, MEL
experience/reflection, DOMAIN_VIEW). It does not reason, calculate, or decide anything itself.

## Product

**PreM3** — Map. Mend. Model. — a self-learning, autonomous pre-modeling agent for Google
Meridian. PreM3 turns fragmented marketing measurement data into a verified model-consumption
BigQuery endpoint, runs official Meridian pre-modeling EDA, and hands the modeler a
`MODEL_READY` package with full provenance.

## Tech stack

| Package | Version |
|---|---|
| Next.js | `16.3.1` |
| React | `19.2.8` |
| TypeScript | `5.9.3` |
| Tailwind CSS | `4.3.3` |
| shadcn/ui | CLI-managed, see `components.json` |
| lucide-react | `1.31.0` |
| Vitest | `4.1.10` |
| React Testing Library | `16.3.2` |

### Why Next.js

App Router gives server-rendered pages (so the run workspace can fetch through a data-source
boundary instead of shipping fixture JSON to the client unnecessarily), file-based routing that
matches the two-route Mission 1 information architecture, and a natural home for the future BFF
route handlers under `src/app/api/`.

### Why Firebase App Hosting

Firebase App Hosting builds and serves Next.js directly from a GitHub-connected repository,
keeps the frontend on Google's platform alongside the rest of the Google-native stack (Cloud
Run, BigQuery, GCS, Vertex AI), and supports server-side environment variables without exposing
them to the browser — required for the eventual authenticated call to the private PreM3 Cloud
Run service.

## Architecture

```text
Browser
  |
  v
Firebase App Hosting (Next.js, App Router)
  |
  v
Next.js server routes (src/app/api/*) -- thin BFF
  |
  v
[future] authenticated service-to-service request
  |
  v
Private PreM3 Cloud Run (Google ADK backend)
  |
  v
Gemini / BigQuery / GCS / Meridian / MEL
```

Everything above the "[future]" line is real, working code in this repository today. Below it
is a documented target — Mission 1 has no live Cloud Run backend to call. See "Deployment
status" below.

## Hosting

Target: **Firebase App Hosting**. The frontend is a standard Next.js app; Firebase App Hosting
builds and deploys it from this repository (GitHub as the deployment source once configured).
The PreM3 backend remains a **separate, private** Cloud Run service — this frontend never hosts
or embeds backend logic.

## Google-native deployment

```text
GitHub
  |
  v
Firebase App Hosting
  |
  v
Next.js PreM3 console (this app)
  |
  v
authenticated server-side call  [future]
  |
  v
private Cloud Run  [PreM3 ADK backend, not part of this repo path]
  |
  v
Gemini / ADK / BigQuery / GCS / Meridian / MEL
```

## Service boundary

**Frontend responsibilities:** present, navigate, proxy (future), compose presentation data
already computed by the backend, expose proof.

**Backend responsibilities:** reason, execute, transform, validate, determine `MODEL_READY`,
produce official evidence, govern learning, own DOMAIN_VIEW truth.

**The frontend never determines `MODEL_READY`.** Every status, severity, and gate value
rendered in this app comes directly from a typed `StructuredResponse`/`ModelReadyGateEvidence`
field — see `src/lib/format/status.ts` and `src/components/prem3/model-ready-card.tsx` for the
display-only mapping.

## Development

```bash
npm install
npm run dev          # http://localhost:3000
npm run lint
npm run typecheck
npm test
npm run build
```

## Repository location

`frontend/` inside the PreM3 monorepo (`https://github.com/datateamsix/prem3`).

## Brand

Source of truth: `../brand/` and `../brand/brand-assets/`.

- Approved primary logo: `../brand/brand-assets/reference/prem3-approved-primary-logo-reference.png`
  (copied into `public/brand/prem3-primary-logo.png` for the app to serve).
- Palette: Navy `#1A1F4B`, Indigo `#3B4BDB`, Cyan `#00C2F5`, Cool Gray `#E6EAF1`, Light Gray
  `#F5F7FA` (`../brand/brand-assets/tokens/prem3.tokens.json`), wired as Tailwind v4 `@theme`
  tokens in `src/app/globals.css`.
- Typography: **Satoshi** is PreM3's display face and **Inter** is the UI/body face
  (`../brand/brand-assets/tokens/prem3.tokens.json`'s `typography.display`/`typography.ui`).
  Satoshi is self-hosted via `next/font/local` (`src/app/layout.tsx`) from the approved
  package at `../brand/brand-assets/fonts/Satoshi_Complete` (ITF Free Font License —
  self-hosting permitted, see that package's `License/FFL.txt`); only the variable-font
  `woff2` files (normal + italic, weight range 300–900) are loaded, copied into
  `src/fonts/satoshi/`. Inter (via `next/font/google`) remains the UI/body face and is
  also Satoshi's own fallback chain.
- Icons: **lucide-react** only, used with supporting text (never color/icon-only status).

## Visual direction

Clerk-level product polish (typography, spacing, restraint) + Google Meridian-adjacent
analytical seriousness (evidence-oriented, technical, quiet) + PreM3's navy/indigo/cyan brand
identity. See `docs/superpowers/specs/2026-08-16-prem3-frontend-scaffold-design.md` for the full
design rationale.

## Deployment status

- [x] Scaffold complete (Next.js, TypeScript, Tailwind, shadcn/ui, Vitest)
- [x] Fixture-driven run workspace complete (`/`, `/runs/[runId]`)
- [ ] Firebase App Hosting configuration created (`apphosting.yaml` present, minimal — not yet
      connected to a live Firebase project)
- [ ] Firebase deployed
- [ ] Private Cloud Run integration live (`ApiPreM3DataSource` is a documented stub — see
      `src/lib/adapters/api-data-source.ts`)

Do not read any unchecked item above as done.

## Demo role

This app is the judge-facing operations console. It exists to make PreM3's autonomous work
observable: **show the action, show the artifact, show the proof** — the run timeline, the
BigQuery/Meridian evidence in `ModelReadyCard`, and the full evidence bundle in `ProofDrawer`.
It renders backend truth; it does not generate it.
