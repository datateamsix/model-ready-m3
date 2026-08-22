# Data Foundation + Business IQ — branch lineage

**Design freeze:** `foundational-intake-freeze-2026-08-22-v1`  
**Working branch:** `feature/prem3-data-foundation-backend`  
**Recorded:** 2026-08-22

## Locked ancestry (do not rebase now)

```text
origin_main_at_mission_start = dce8a209bb67fbaa3c8a78ae4e8a7384897252ed
dependency_base_sha          = 02cec50b6da6507838081e65086eaaf29a4a5329
dependency                   = Mission 2 / Mission 11 backend line
branch_repair_required       = no
```

`feature/prem3-data-foundation-backend` is a stacked dependency on Mission 2 / Mission 11 at `02cec50`. This work requires Clerk, Firestore, prem3-api, OAuth, M2-11 resource bindings, and the existing control-plane/runtime infrastructure.

`origin/main` at mission start (`dce8a20`, Satoshi font merge) does not contain that stack. Rebasing onto `dce8a20` now would drop the required dependency line.

`git merge-base origin/main HEAD` is `dce8a20` because Mission 2 commits sit on top of that main SHA. The working tree is therefore a descendant of main **plus** the 25-commit Mission 2 line. That is expected. It is not a reason to open a combined mega-PR.

## Merge strategy (after the dependency lands)

```text
Mission 2 / Mission 11 work
            ↓
    merges to main
            ↓
fetch updated origin/main
            ↓
rebase / restack Data Foundation
on the newly merged main
            ↓
verify resulting diff contains
Business IQ + Data Foundation work
            ↓
rerun all proofs/tests
            ↓
PR Data Foundation → main
```

If the parent Mission 2 line does not merge as expected, **stop and report** before changing ancestry. Do not silently produce a combined mega-PR that bundles the entire Mission 2 stack plus Data Foundation.

## Freeze checkpoint

```text
FOUNDATIONAL_INTAKE_BACKEND_FREEZE
foundational-intake-freeze-2026-08-22-v1
checkpoint_sha               = (recorded after freeze commit)
```

The checkpoint SHA is immutable. No new foundational-intake capability should be added on this branch after freeze. Newly discovered requirements are post-freeze refinements unless they are correctness or security defects.

## What not to do

- Do not rebase onto `dce8a20` merely to satisfy earlier §1 wording.
- Do not open a PR to `main` that casually includes the Mission 2 stack as an unrelated diff.
- Do not rewrite qualified Mission 2 HEADs.
