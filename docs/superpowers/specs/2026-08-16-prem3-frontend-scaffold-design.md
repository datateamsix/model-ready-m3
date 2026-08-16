# PreM3 Frontend Scaffold — Design

**Status:** Approved for implementation (Mission 1)
**Branch:** `feature/prem3-frontend-scaffold`
**Worktree:** `../prem3-frontend` (sibling of the primary repo worktree, which stays on `feature/prem3-dataset-c-summit-pine`)
**Baseline SHA:** `18e9fdda8c980a6a64d2c8eae11c8e6912f18f78` (`origin/main`)
**Owner:** Claude Code — Frontend / demo console (per `docs/context/07_AGENT_DELEGATION_AND_GUARDRAILS.md`)

## 1. Origin of this design

This document records the design for Mission 1 of the PreM3 frontend. The mission brief (provided directly by the human lead) already specifies product philosophy, tech stack, hosting target, information architecture, component inventory, guardrails, and acceptance criteria in detail. This spec exists to (a) pin those decisions to a single source of truth for the implementation plan, and (b) record what was independently verified against the actual repository rather than assumed, per the delegation guardrail: *"Do not invent backend contracts. Use checked-in API schemas."*

## 2. Problem / goal

PreM3's backend (ADK agent + deterministic tools + typed response contracts + MEL) exists but has no UI. The hackathon rubric explicitly rewards judge-visible proof of autonomous action, architecture discipline, and production readiness. There is currently no frontend at all in the repo. Mission 1 builds the scaffold and the first polished, fixture-driven run workspace: an operations console (not a chatbot, not a marketing site) that renders backend truth — it never computes MODEL_READY, severity, or learning claims itself.

## 3. Verified repository truth (grounding facts)

Confirmed by direct inspection of this worktree, not assumed:

- **No backend HTTP API exists yet** (no FastAPI/Flask/uvicorn found under `app/`). The ADK agent (`app/agent.py`) exposes tools, not REST routes. The frontend cannot integrate with a live Cloud Run endpoint yet — fixture-first is not a fallback, it's the only viable path today.
- **Typed response contract** lives in `app/response/contracts.py` (`StructuredResponse` and friends) and is the presentation contract the frontend renders. Enums verified: `ResponseType` (24 values incl. `MODEL_READY`, `OFFICIAL_MERIDIAN_EDA`, `LEARNING`, `DOMAIN_VIEW`, `JUDGE_DEMO`), `PresentationStatus`, `SectionType`, `KnowledgeClass`/`DecisionClass`/`ResponsibleActor` (from `app/intelligence/contracts.py`).
- **Real fixture `StructuredResponse` JSON already exists** at `tests/fixtures/response/*.json` (`model_ready.json`, `judge_model_ready.json`, `official_meridian.json`, `learning.json`, `domain_view.json`, `dataset_a_assessment.json`, `dataset_a_feasibility.json`, `dataset_a_semantic_interview.json`, `dataset_a_scope_scenario.json`, `dataset_a_parameter_advisory.json`, `guided_remediation.json`, `blocked.json`, `user_resolution_pack_example.json`). These are schema-valid backend-shaped payloads, not something the frontend needs to invent. They will seed the TypeScript fixtures.
- **Run state machine** is `RunStage` in `app/core/state.py`: `NEW → DISCOVERING → PROFILING → MAPPING → ASSESSING → (WAITING_FOR_APPROVAL) → REMEDIATING → VALIDATING → PUBLISHING → EXPLORING → MODEL_READY → (WAITING_FOR_MODEL_APPROVAL → MODELING) → LEARNING → COMPLETE`, with `FAILED` reachable from most states. This is the authoritative timeline vocabulary — the mission brief's conceptual `Map/Mend/Validate/Publish/Verify/Explore/Interpret/Handoff` labels are a presentation grouping over these real stages, not a replacement for them.
- **MEL / learning truth** verified as `NOT_PROVEN`: `learning.json` and `domain_view.json` fixtures both show `promoted_lesson_count: 0`, `DOMAIN_VIEW version 1.0.0`, explicit `"do_not_claim": "That PreM3 has already learned from production runs."` This is the real current state and the honest zero-learning UI must match it exactly.
- **MEL contracts** (`app/mel/models.py`): `ExperienceEpisode`, `ExperienceReflection` (explicit `operational_authority: bool = False`, forced in `model_post_init` — reflection is architecturally incapable of carrying authority), `ReflectionSurface` enum (the "I KNOW / I OBSERVED / I DETERMINED / I BELIEVED / I WAS ALLOWED TO / I DID NOT KNOW / I EXPECTED / WHAT HAPPENED" pillars plus synthesis states `CONFIRMED/MISSED/INCOMPLETE/HUMAN_ADDED/MERIDIAN_ADDED/SURPRISES/POSSIBLE_IMPROVEMENTS`), `CandidateLesson`, `LessonEvaluation`, `PromotionReceipt` (`receipt_type: EXPERIENCE_LEARNED | EXPERIENCE_APPLIED`), `ExperienceApplication`, `DomainViewRegistryEntry`.
- **Interface contracts** in `docs/context/07_AGENT_DELEGATION_AND_GUARDRAILS.md` (Run status event, Issue, Transformation, BigQuery Publish Contract, Learning Receipt Contract) — smaller JSON shapes for the timeline/publish/receipt surfaces that sit alongside `StructuredResponse`.
- **Brand tokens** confirmed at `brand/brand-assets/tokens/prem3.tokens.json` / `.css` / `.ts`: Navy `#1A1F4B`, Indigo `#3B4BDB`, Cyan `#00C2F5`, Cool Gray `#E6EAF1`, Light Gray `#F5F7FA`; typography `Satoshi` (display) / `Inter` (UI). Approved logo/brand-board PNGs exist under `brand/brand-assets/reference/`. No Satoshi web font files are present in the repo — Inter is the implementation-safe fallback for Mission 1, documented as such.
- **Music Center Dataset A** (`tests/fixtures/music_center/`) is the golden visual fixture: weekly × geo grain, geos CA/TX/FL/NY, 131 weekly periods (2024-01-01–2026-06-29), KPI = Shopify orders, 5 seeded Phase 1 defects (duplicate Google Ads row, ISO vs `MM/DD/YYYY` date mismatch, daily vs weekly grain mismatch, currency-string spend, inconsistent Meta channel labels), exact defect catalog in `expected_manifest.json`.
- **Update 2026-08-16 (post-rebase):** the Dataset C restructure merged to `origin/main` (PR #8, commit `43df930`) and this branch has been rebased onto it (new baseline `43df930`, plan/spec commit now `4a0f86b`). `datasets/` is canonical: `datasets/music_center/{dataset_a,dataset_b}/`, `datasets/stride_and_field/dataset_b/`, `datasets/summit_and_pine/dataset_c/`. `tests/fixtures/music_center/` no longer exists — per `datasets/README.md`, `tests/fixtures/` is reserved for small isolated unit-test fixtures and must not hold a second copy of a dataset. `tests/fixtures/response/*.json` (the `StructuredResponse` payloads) were unaffected by the move and remain at their original path. Verified the relocated `datasets/music_center/expected_manifest.json` is byte-identical in content to what was read pre-rebase (same 5 defects, same date range) — the fixture facts used below are unchanged, only the path is. Music Center Dataset A path used from here on: `datasets/music_center/dataset_a/`.

## 4. Architecture

```
Browser
  ↓
Firebase App Hosting (Next.js, App Router)
  ↓
Next.js server route(s) — thin BFF (frontend/src/app/api/*)
  ↓
[future] authenticated service-to-service request
  ↓
Private PreM3 Cloud Run (ADK backend — not built in Mission 1)
  ↓
Gemini / BigQuery / GCS / Meridian / MEL
```

Mission 1 implements everything above the "future" line as a real, working Next.js app; below that line is a documented target, not live code. The data-source boundary (`PreM3DataSource` interface, §7) is what lets that swap happen later without touching components.

**Frontend responsibilities:** present, navigate, compose presentation data from the typed contract, expose proof. **Never:** determine `MODEL_READY`, recompute severity, rewrite Meridian findings, fabricate learning claims. This boundary is enforced structurally — no component takes raw numbers and derives a status; every status/severity value a component renders is read directly off the contract.

## 5. Tech stack

Next.js (App Router) + React + TypeScript + Tailwind CSS + shadcn/ui + lucide-react, npm, Vitest + React Testing Library. No Redux, GraphQL, WebSockets, or heavy chart libs. TanStack Query only if/when live API integration needs it — not for fixture data.

## 6. Information architecture

- `/` — console entry: PreM3 logo/product line, "New Assessment", Recent Runs, demo assignments (Music Center live; Stride & Field / Summit & Pine shown only if fixture data exists — not stubbed as fake-live).
- `/runs/[runId]` — the primary product screen: header, run timeline (real `RunStage` values), metrics, findings, insights, actions, semantic questions, Meridian (official vs. interpretation, kept visually distinct), MODEL_READY/handoff, experience/reflection/learning, proof drawer.
- `/api/health` — trivial BFF liveness route, establishing the server-route pattern early.

## 7. Data-source boundary

```ts
interface PreM3DataSource {
  getRun(runId: string): Promise<RunSummary>
  getRunResponse(runId: string): Promise<StructuredResponse>
  getArtifacts(runId: string): Promise<ArtifactRef[]>
  getExperience(runId: string): Promise<ExperienceBundle | null>
  getDomainView(): Promise<DomainViewSummary>
}
```

`FixturePreM3DataSource` is the only implementation in Mission 1, reading from `frontend/src/lib/fixtures/` (seeded from the real `tests/fixtures/response/*.json` payloads plus Music Center facts). `ApiPreM3DataSource` is stubbed with the same interface and a clear "not implemented" path, so wiring a real Cloud Run endpoint later is a one-file change, not a rewrite.

## 8. TypeScript contracts

Generated by hand from the verified Python source (§3), not from prose memory of it — field-for-field match to `app/response/contracts.py`, `app/core/state.py`, and the relevant `app/mel/models.py` shapes needed for the reflection/learning surfaces. Any place Python and the mission brief's conceptual language diverge (e.g., timeline stage naming), the code follows the Python enum and the UI applies a presentation label on top — never the reverse.

## 9. Component inventory (initial)

`AppShell`, `PreM3Logo`, `PageHeader`, `StatusHeader`, `StatusBadge`, `RunTimeline`, `RunStage`, `MetricRow`/`MetricItem`, `SectionHeader`, `FindingCard`, `InsightCard`, `ActionCard`, `QuestionCard`, `ScenarioCard`, `MeridianFindingCard`, `AuthorityBadge`, `SourceBadge`, `ModelReadyCard`, `ArtifactRow`, `ProofDrawer`, `ExperienceEpisodeCard`, `ReflectionCard`, `LearningReceiptCard`, `DomainViewCard`, `DomainViewDiff`, `ExperienceAppliedCard`, `EmptyState`, `LoadingState`, `ErrorState`. Built only as real surfaces need them — no speculative abstraction.

## 10. Visual direction

Clerk-level restraint and typographic polish + Meridian-adjacent analytical seriousness + PreM3 navy/indigo/cyan identity. Off-white surfaces, navy type, light neutral separators, indigo structural accents, cyan reserved for meaningful emphasis. Sections/rows/tables over card proliferation. No gradients, glassmorphism, neon, chat bubbles, or decorative motion. Lucide React only, used with supporting text. Desktop ~1440px / 16:9 is the primary target (screen-recorded demo); laptop width and one narrow breakpoint are also checked; mobile stays usable but isn't optimized for.

## 11. Truth-preservation rules (non-negotiable)

- Frontend never calculates `MODEL_READY`; it renders `gate_evidence` / `PresentationStatus` as given.
- Official Meridian severity (`official_severity`, `official_finding_text`) is always rendered separately from PreM3 interpretation (`prem3_interpretation`) — never merged into one block.
- Reflection surfaces render as evidence with a visible "no operational authority" framing; never implied to be a decision.
- Learning UI shows real fixture state: 0 promoted lessons, DOMAIN_VIEW 1.0.0, no `EXPERIENCE_APPLIED`. Any synthetic-only visual fixture is labeled `UI_DEMO_FIXTURE` and must not resemble a real receipt.
- Dataset C (Summit & Pine) is never presented as training data if/when it appears.

## 12. Testing

Vitest + RTL covering: status rendering, run timeline rendering, Meridian source separation, official-severity preservation, fact-vs-interpretation separation, MODEL_READY display-only behavior, zero-learning state, reflection no-authority framing, DOMAIN_VIEW state, fixture adapter behavior, loading state, blocked state. `npm run lint`, `typecheck`, `test`, `build` all must pass before handoff.

## 13. Explicitly out of scope for Mission 1

Public marketing site, real auth/org/billing, provider registry editor, WebSockets, chat-first UX, full Eventarc UI, complex upload orchestration, Meridian model fitting UI, heavy charting, and any fabricated learning/receipt/DOMAIN_VIEW v2 state.

## 14. Risks / open gaps to carry into the plan

- No real Cloud Run endpoint exists — `ApiPreM3DataSource` will remain unimplemented after Mission 1; documented as a known gap in the README, not hidden.
- ~~`datasets/` restructure and Dataset C seal are not yet on `origin/main`~~ — resolved: rebased onto `origin/main` @ `43df930` on 2026-08-16 (see §3 update above). No further rebase expected to be required for Mission 1 unless more work lands on `main` before handoff, in which case repeat the rebase and re-run lint/typecheck/test/build per the mission brief's Section 50.
- Satoshi web assets are not in the repo; Inter is used and documented as the fallback until licensed Satoshi files are added.
