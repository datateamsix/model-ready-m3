# Backend Integration Contract

This directory is the shared integration contract between `prem3-api` (backend) and the
frontend, per Mission 2's `M2-02` prompt
(`frontend/docs/mission-2/PREM3_MISSION_2_FRONTEND_EXECUTION_PROMPT_PACK.md`).

**Status as of 2026-08-17: not yet populated.** Neither `openapi.yaml` (this directory) nor
the JSON Schema exports (`schema/`) exist yet. See `docs/contracts/BACKEND_REQUESTS.md`'s
`REQ-001` (contract schema export) and `REQ-002` (OpenAPI freeze) — both `NOT STARTED`.

## Intended layout, once populated

```text
contracts/
  openapi.yaml       # the integration contract (REQ-002)
  schema/            # backend JSON Schema exports (REQ-001)
```

## Intended pipeline, once populated

`frontend/package.json` scripts (already added, currently informational no-ops — see each
script's own message):

- `contracts:check` — validates `contracts/openapi.yaml` exists and is well-formed; fails CI on
  drift once wired to a real generator.
- `contracts:generate` — generates TypeScript into `frontend/src/types/generated/` from
  `contracts/openapi.yaml`.
- `api:generate` — generates a typed API client from the same source.

None of these can do real work until `openapi.yaml` exists. They currently print a clear
"blocked on REQ-002" message and exit 0 (not a hard CI failure) — CI going red over an unmet
cross-team dependency isn't the same signal as catching real contract drift, and would block all
other frontend work over something the frontend track doesn't own. Once `contracts/openapi.yaml`
lands, wire a real generator (e.g. `openapi-typescript`) into `contracts:generate` and make
`contracts:check` a real drift gate run before `npm run typecheck` in CI.

## Why this isn't fabricated

Per the Mission 2 prompt pack's standing rule 5 ("never invent missing backend behavior in
frontend code — add/update a backend contract request instead"), this directory intentionally
does not contain a placeholder or example OpenAPI document that could be mistaken for a real
contract. `docs/contracts/BACKEND_REQUESTS.md` is where that dependency is tracked instead.
