# PreM3 Frontend Scaffold — Status

**Last updated:** 2026-08-16
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

## Progress: Tasks 1–12 of 28 complete

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

**Verification gate after every task:** `npm run typecheck && npm run lint && npm test && npm run build` —
all clean as of the last commit (`97966e5`). Test count at last check: 30 passing.

## Next up

**Task 13: `PreM3Logo`, `AppShell`, `PageHeader`** — the first actual UI
components, starting `frontend/src/components/prem3/`. Plan section starts
at line 2490 of the plan file.

## Working notes for whoever resumes this

- When a plan snippet references a Python backend contract, verify it
  field-for-field against the real source before writing the TypeScript —
  the plan's snippets are not always accurate (Task 7 had real gaps; Task 6
  didn't). Don't blindly trust "hand-verified" claims in the plan text.
- Follow strict TDD where the plan specifies it: write the test, confirm it
  fails for the right reason, implement, confirm it passes.
- Every task's data-dependent test assertions (specific counts, IDs, status
  values) get spot-checked against the real fixture JSON/dataset files
  before trusting them — this caught nothing wrong so far, but is worth
  keeping up.
- Full verification gate (typecheck/lint/test/build) before every commit,
  not just the task's own new test.
- Commit each task's implementation separately from its plan-checkbox update
  (two commits per task) — keeps the plan-doc bookkeeping out of the
  functional diff.
