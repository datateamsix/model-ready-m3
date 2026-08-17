@AGENTS.md

# frontend/CLAUDE.md

Durable rules for working in `frontend/`. See also
`docs/superpowers/specs/2026-08-16-prem3-frontend-scaffold-design.md` and the parent repo's
`AGENTS.md` / `docs/context/07_AGENT_DELEGATION_AND_GUARDRAILS.md`.

- PreM3 is operations-console-first, not chatbot-first. No persistent AI assistant panel, no
  "Ask PreM3 anything" as the primary interaction.
- Never invent backend facts. If a value isn't in a typed contract (`src/types/*`) or a real
  fixture, don't render it.
- Structured backend contracts (`src/types/response.ts`, `run.ts`, `mel.ts`, `domain-view.ts`)
  are hand-mirrored from `app/response/contracts.py`, `app/core/state.py`, `app/core/contracts.py`,
  `app/mel/models.py`, `app/domain/intelligence/models.py`. If the Python source changes, update
  the mirror — don't let them drift silently.
- `MODEL_READY` is backend truth. Components only render `ModelReadyGateEvidence` fields; they
  never compute readiness from raw numbers.
- Official Meridian findings and PreM3 interpretation render in separate, clearly labeled
  blocks — never merged (`meridian-finding-card.tsx` enforces this).
- Learning claims require evidence. `DomainViewCard` must show the honest zero-promoted-lesson
  state when `promoted_lesson_count === 0` — never a vaguer "coming soon."
- Reflection has no operational authority (`app/mel/models.py` forces this at the backend model
  level too). `ReflectionCard` always states this visibly.
- `EXPERIENCE_APPLIED` requires a later, separate validated assignment. Never render one from a
  single episode.
- DOMAIN_VIEW is versioned, backend-controlled operational knowledge. The frontend reads it; it
  never edits or diffs it speculatively (`DomainViewDiff` shows "no changes yet" until a real
  diff exists).
- Use the existing brand package (`../brand/`) as the source of truth — do not redraw the logo
  or invent a new palette.
- lucide-react is the only icon system.
- Target Clerk-level fit and finish; target Meridian-compatible analytical character.
- Keep interaction crisp and restrained — sections/rows/tables over card proliferation.
- Accessibility is required: status is never color-only, focus states are visible, drawers are
  keyboard-operable.
- Desktop ~1440px / 16:9 screen recording is the first-priority target.
- The frontend presents; it does not determine readiness.
- Private Cloud Run stays private — no service-account credentials or privileged secrets in
  `NEXT_PUBLIC_*` variables or client components.
- Do not duplicate backend business logic in `src/app/api/*` route handlers.
- Components take typed props; only pages (`src/app/**/page.tsx`) and `src/lib/adapters/*` import
  from `src/lib/fixtures/*`. If a `src/components/prem3/*` file imports a fixture directly,
  that's a boundary violation — route the data through `preM3DataSource` instead.
