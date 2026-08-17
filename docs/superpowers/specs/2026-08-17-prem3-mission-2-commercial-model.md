# PreM3 Mission 2 — Commercial Model & Product Hierarchy

**Recorded:** 2026-08-17
**Status:** canonical — supersedes earlier informal commercial-model assumptions
**Architecture:** `docs/context/14_MULTITENANCY_AND_IDENTITY_BOUNDARY.md`,
`docs/context/15_FRONTEND_INTEGRATION_AND_SERVICE_SURFACE.md`,
`docs/context/16_AUTH_BILLING_AND_ENTITLEMENTS.md`
**Contracts:** `docs/contracts/BACKEND_REQUESTS.md`

This document is the durable commercial/hierarchy record for Mission 2. It does not implement
runtime billing.

## 1. Customer-facing object hierarchy

```text
Account / Organization
  └── MMM Project
        └── Dataset
              └── Evaluation Run
```

```text
tenant_id
  └── workspace_id       # customer-facing: MMM Project
        └── dataset_id   # durable Dataset
              └── run_id # one Evaluation / re-evaluation
```

Clerk user/org provisioning creates identity mapping and a Planner-tier entitlement
(`max_active_projects = 0`). It does **not** auto-create a paid MMM Project.

## 2. Commercial packaging

Plans gate by **active MMM Project count**, not by run/evaluation volume:

| Plan | Customer | Included active MMM Projects | Re-evaluations |
|---|---|---:|---|
| Planner | Prospective user / lead | 0 paid project slots | N/A — public Planner only |
| Project | One company / one MMM initiative | 1 | Unlimited |
| Portfolio | Agency / multi-brand team | Up to 10 | Unlimited |
| Enterprise | Large agency / enterprise | Up to 50 | Unlimited |

- The commercial gate is `max_active_projects`, not `dataset_runs_per_month`.
- Unlimited re-evaluations means commercial plans do not meter `run_id`.
- Price amounts and Stripe Price IDs come from the backend plan catalog (`REQ-012`).
- Stripe is subscription source of truth; PreM3 stores a Firestore entitlement projection.

## 3. Free tier: the PreM3 Planner

Public `/planner` is lead-generation, distinct from authenticated planning.

- Zero paid MMM Project slots.
- No GCP/PreM3 runtime execution at anonymous runtime.
- No `TenantContext` and no backend anonymous session or claim handshake.
- Uses only the versioned Planner manifest (`REQ-015`).
- Never declares `COLLECTION_READY` or `MODEL_READY`.
- Conversion CTA: **Save as an MMM Project**, which is explicit and capacity-gated.

## 4. Terminology

- Customer-facing completion term: **Meridian Integration**.
- Internal/judge `handoff_*` names may remain on proven contracts.
- `tenant_id` is never customer-facing copy.

## 5. Control-plane store

Firestore holds tenant mappings, membership, projects, datasets, entitlements, billing
projections, webhook idempotency, and registry overlay metadata. GCS and BigQuery retain
artifact and ledger roles. Clerk/Stripe IDs are mapped attributes, never storage keys.
