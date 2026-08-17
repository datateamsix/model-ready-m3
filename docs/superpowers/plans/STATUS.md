# PreM3 Frontend Scaffold — Status

**Last updated:** 2026-08-17
**Plan:** `docs/superpowers/plans/2026-08-16-prem3-frontend-scaffold.md` (28 tasks)
**Design spec:** `docs/superpowers/specs/2026-08-16-prem3-frontend-scaffold-design.md`

## Where this work actually lives

**Worktree:** `C:\Users\zroda\Desktop\prem3-frontend-ws` — a dedicated `git worktree`
on branch `feature/prem3-frontend-scaffold`. Always work here, not in the main
`C:\Users\zroda\Desktop\prem3` directory.

**Why:** the main `prem3` directory is a shared working tree that a Cursor agent
is concurrently using for unrelated backend work on
`feature/prem3-first-real-learning-cycle` (MEL/learning-cycle, `app/mel/*.py`
etc.). Checking out the frontend branch there once already collided with
Cursor's checkout mid-session — a commit briefly landed on the wrong branch
and had to be moved. Never run git checkout/commit for frontend work in the
main `prem3` directory.

**Stale directory to ignore:** `C:\Users\zroda\Desktop\prem3-frontend` (no
`-ws` suffix) is an orphaned leftover from before the repo was renamed from
`model-ready-m3`. Its git link is broken; its useful content was already
copied into `prem3-frontend-ws` at the start of this work. Don't use it.

## Progress: all 28 tasks complete. One step remains: pushing the branch.

Every task's steps are tracked as `- [x]` checkboxes directly in the plan
file (flip `- [ ]` → `- [x]` per task once verified and committed — this is
the source of truth for progress, not `.superpowers/sdd/progress.md`, which
is an empty stub).

1. ✅ Next.js scaffold + tooling scripts (`build`/`lint`/`typecheck`)
2. ✅ Vitest + RTL (had to pin `pool: "threads"` — the default `forks` pool
   hangs in this sandboxed shell)
3. ✅ shadcn/ui + lucide-react (CLI has moved past `--base-color`; used
   `--base base -p nova`, still resolves `baseColor: neutral`)
4. ✅ PreM3 brand tokens, Inter font, approved logo asset
5. ✅ TypeScript contracts — intelligence enums, run/state (`@/types/intelligence`, `@/types/run`)
6. ✅ TypeScript contracts — `StructuredResponse` (`@/types/response`) — full 1:1 mirror, no gaps
7. ✅ TypeScript contracts — MEL, DOMAIN_VIEW (`@/types/mel`, `@/types/domain-view`) —
   corrected several real gaps vs. the plan's snippets (missing fingerprints,
   `dataset_role`/`reflection_role`, full `RegressionResult`, `experience_provenance`)
8. ✅ Contracts barrel + `format/status.ts` + `format/timeline.ts`
9. ✅ Real `StructuredResponse` fixtures copied from `tests/fixtures/response/*.json`
10. ✅ Music Center Dataset A `UI_DEMO_FIXTURE` run composition
11. ✅ Real DOMAIN_VIEW v1 fixture + Music Center experience/reflection bundle
12. ✅ `PreM3DataSource` boundary — fixture adapter + documented `ApiPreM3DataSource` stub
13. ✅ `PreM3Logo`, `AppShell`, `PageHeader`
14. ✅ `StatusBadge`, `StatusHeader`
15. ✅ `MetricRow`, `SectionHeader`
16. ✅ `FindingCard` — fact/interpretation separation (truth-preservation critical)
17. ✅ `InsightCard`, `ActionCard`, `QuestionCard`, `ScenarioCard`
18. ✅ `AuthorityBadge`, `SourceBadge`, `MeridianFindingCard` — Meridian/PreM3
    separation (truth-preservation critical)
19. ✅ `RunTimeline` — golden-path stage dots from `computeStageStatuses`
20. ✅ `ModelReadyCard` — renders exactly the five gate booleans + ERROR count,
    never derives a MODEL_READY-ish conclusion (truth-preservation critical;
    fixed an ambiguous ByText query in the plan's own test)
21. ✅ `ProofDrawer`, `ArtifactRow` — found and fixed a real bug: the plan's
    `SheetTrigger asChild` snippet doesn't work with this stack's installed
    `@base-ui/react` primitives (which use a `render` prop, not Radix's
    `asChild`); using `asChild` silently produced nested `<button>`s (a real
    hydration error). Also fixed an unescaped apostrophe the plan's own JSX
    would have failed lint on.
22. ✅ `ExperienceEpisodeCard`, `ReflectionCard` — no-authority framing
    (truth-preservation critical; fixed missing required `ExperienceReflection`
    fields in the plan's test fixture, same fields Task 7 added)
23. ✅ `DomainViewCard`, `DomainViewDiff`, `LearningReceiptCard`,
    `ExperienceAppliedCard` — honest zero-learning state (truth-preservation
    critical), verified against real fixture values (35 claims, v1.0.0)
24. ✅ `EmptyState`, `LoadingState`, `ErrorState`
25. ✅ Root layout + `/` console entry page — replaced create-next-app's
    default scaffold; fixed an ambiguous ByText query (both demo
    assignments render the same "not yet available" note by design)
26. ✅ `ResponsePanel`, the `/runs/[runId]` workspace, `/api/health` — the
    payoff task, rendering the Music Center fixture end to end. Fixed two
    ambiguous ByText queries in the plan's own tests (same failure class as
    Tasks 20/25 — the fixture legitimately mirrors one finding into both
    `findings[]` and `official_meridian[]`; "Music Center" is PageHeader's
    eyebrow `<span>`, not part of the `<h1>`'s accessible name).
27. ✅ `frontend/README.md`, `frontend/CLAUDE.md`, `frontend/apphosting.yaml` —
    README's version table filled with real installed versions, not left as
    `<version>` placeholders. CLAUDE.md keeps the pre-existing `@AGENTS.md`
    import (regenerated by `next dev`) at the top, plan's durable rules below.
28. ✅ Steps 1–6 complete: full gate clean, both routes smoke-tested, visual
    QA done at 1440/1280/390px (found and fixed a real bug — see below),
    `MODEL_READY` grep audit clean, no backend files touched, no rebase
    needed (`origin/main` still at the branch's merge-base `43df930`).
    **Step 7 (push to origin) intentionally left undone** — outward-facing
    on a shared repo, held for your go-ahead.

**Visual QA finding + fix (Task 28 Step 3):** the approved icon reference
asset is 385×265px, not square, but `PreM3Logo` passed equal width/height —
squishing it and triggering a Next.js console warning. Fixed by deriving
height from the real aspect ratio. Also: none of the brand package's
reference PNGs have an alpha channel (opaque RGB with a baked-in white
background), so the icon showed as a white box on any non-white surface.
`public/brand/prem3-icon.png` is a new transparent derivative (chroma-keyed
via `sharp`, already a project dependency).

**Post-plan design change (user-directed, after Task 28):** removed the
"Map. Mend. Model." tagline from under the logo everywhere, enlarged
`PreM3Logo` (sm 24→28, md 32→40, lg 44→72px, wordmark text now scales with
size), and switched to the new transparent icon asset above. Homepage hero
keeps a real `<h1>PreM3</h1>` rather than routing it through `PreM3Logo`'s
`<span>` wordmark, to preserve the page's only heading for accessibility.

**Verification gate after every change:** `npm run typecheck && npm run lint && npm test && npm run build` —
all clean as of the last commit (`864a35d`). Test count at last check: 78 passing.

## Post-merge-prep hardening (2026-08-17, after the plan's 28 tasks)

Branch was pushed, then three more items landed before opening the PR to `main`:

1. **Fixed a real run-timeline bug:** `RUN_STAGE_ORDER` only encodes the
   golden path (12 of 16 `RunStage` values) — `WAITING_FOR_APPROVAL`,
   `WAITING_FOR_MODEL_APPROVAL`, `MODELING`, and `FAILED` aren't in it.
   `computeStageStatuses()` used a bare `indexOf()`, so any run sitting in
   one of the three real off-path branch/waiting states (per
   `app/core/state.py`'s actual `_LEGAL_TRANSITIONS` graph) had its entire
   timeline collapse to `NOT_STARTED`, hiding real completed progress.
   Fixed via a `BRANCH_STAGE_ANCHOR` map resolving each branch stage to the
   golden-path stage it occurs after (`lib/format/timeline.ts`). TDD: wrote
   4 failing tests first, confirmed the bug, then fixed. Test count 78→84.
2. **Added frontend CI**: `.github/workflows/frontend.yml` — lint,
   typecheck, test, build on Node 24, verified locally via a clean
   `npm ci` (not just `npm install`) before committing.

## Next up

Open the PR from `feature/prem3-frontend-scaffold` to `main`, wait for CI,
and merge once green with no blocking issues.

## Working notes for whoever resumes this

- When a plan snippet references a Python backend contract, verify it
  field-for-field against the real source before writing the TypeScript —
  the plan's snippets are not always accurate (Task 7 had real gaps; Task 6
  didn't). Don't blindly trust "hand-verified" claims in the plan text.
- Follow strict TDD where the plan specifies it: write the test, confirm it
  fails for the right reason, implement, confirm it passes.
- Every task's data-dependent test assertions (specific counts, IDs, status
  values) get spot-checked against the real fixture JSON/dataset files
  before trusting them.
- Full verification gate (typecheck/lint/test/build) before every commit,
  not just the task's own new test.
- Commit each task's implementation separately from its plan-checkbox update
  (two commits per task) — keeps the plan-doc bookkeeping out of the
  functional diff.
- Watch for two recurring failure classes in this codebase's own plan
  snippets, both found more than once: (1) ambiguous `getByText` queries
  when the same string legitimately renders in two places (scope with
  `within()` or a more specific role/level query instead of loosening the
  assertion); (2) this stack's `@base-ui/react` primitives use a `render`
  prop, not Radix/shadcn's `asChild`, wherever a trigger needs to merge
  onto a custom styled child.
