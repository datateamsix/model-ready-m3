# Multi-Tenancy and Identity Boundary

**Status:** Mission 2 canonical constraint — revised 2026-08-17
**Applies to:** MMM Projects, Datasets, Planning, Pre-Modeling Taskmaster, billing/entitlements, and all SaaS surfaces
**Depends on:** `02_SYSTEM_ARCHITECTURE.md`, `11_ADK_RUNTIME_IDENTITY_MODEL.md`, `13_CLOUD_TASKMASTER_EXECUTION_MODEL.md`
**Architecture reconciliation:** Mission 2 frontend productization plan, 2026-08-17

---

## 1. Why this document exists

`11_ADK_RUNTIME_IDENTITY_MODEL.md` defines **workload identity** — how PreM3 authenticates to Google Cloud. It does not define **customer identity** — how PreM3 knows whose data it is operating on and proves it cannot reach anyone else's.

Today those two used to be conflated: process-global `Settings.organization_id` /
`Settings.workspace_id` were interpolated into GCS paths. Request-scoped
`TenantContext` / `WorkspaceContext` / `ExecutionContext` now own customer and
Evaluation authority. `Settings` holds infrastructure identifiers only. Registered
ADK tools no longer accept tenant, workspace, Dataset, package URI, or storage
authority arguments. Legacy CLI/cloud-proof scripts bind developer bootstrap and
may still accept a package URI through `prepare_legacy_dataset_execution`, which
is not registered on `root_agent`.

Firestore is implemented as the Mission 2 operational control-plane repository
(`app/control_plane/`) with an in-memory twin for CI. `prem3-api` / FastAPI,
Clerk verification, and Stripe SDK wiring remain pending.

The already-deployed Cloud Run Taskmaster revision still receives a user prompt
that names a package URI; that historical proof harness is not the product tool
surface. `prem3-api` will bind `ExecutionContext` before invoking the agent.

Every authenticated Mission 2 capability — account creation, paid MMM Projects, saved plans, Dataset uploads, evaluation history, Taskmaster, Meridian Integration, and billing — requires more than one tenant per process. This constraint must be resolved **before live service integration lands**, because it changes the signature of the persistence layer, service boundary, and authorization checks that those capabilities depend on.

**Core rule:** workload identity authenticates PreM3 to Google Cloud. Tenant identity is application state carried per request. They are never the same value and never derived from each other.

---

## 2. Identity and product hierarchy

Mission 2 adds a commercial/product hierarchy on top of the isolation hierarchy. Keep the customer language and internal identifiers distinct but explicitly mapped.

```text
Account / Organization
PreM3 internal: tenant_id
  └── MMM Project
      PreM3 internal: workspace_id
        ├── planning_run_id        # authenticated planning workflow
        └── Dataset
            PreM3 internal: dataset_id
              └── Evaluation Run
                  PreM3 internal: run_id

user_id              # a person; may belong to many tenants
planner_draft_id      # optional local/public Planner identifier; never an isolation key
```

Definitions:

| ID / concept | Authority | Lifetime | Notes |
|---|---|---|---|
| `tenant_id` | PreM3-issued, immutable | permanent until deletion | Billing + isolation boundary. One per customer organization. |
| `workspace_id` / **MMM Project** | PreM3-issued | permanent until deletion | Customer-facing project/client/program boundary. Commercial project capacity is counted here. |
| `dataset_id` / **Dataset** | PreM3-issued | permanent until deletion | Durable analytical/model-input configuration inside one MMM Project. One project may contain multiple datasets. |
| `run_id` / **Evaluation Run** | PreM3-issued | permanent | One assessment or re-assessment of one Dataset. Paid plans do not meter or charge by `run_id`. |
| `planning_run_id` | PreM3-issued | permanent | Authenticated planning workflow inside one MMM Project. |
| `user_id` | Clerk | provider-governed | Never used as an isolation key on its own. |
| `planner_draft_id` | frontend-generated, optional | TTL/local-storage bounded | Public Planner convenience only. Never becomes a tenant or storage boundary. |

Commercial plans gate on **active MMM Project count** (`workspace_id`), not Dataset count and not Evaluation Run count. Current packaging is Planner / Project / Portfolio / Enterprise with 0 / 1 / 10 / 50 paid active-project capacity respectively. Unlimited re-evaluations means a Dataset may have many `run_id` values without consuming a commercial run quota; abuse, concurrency, storage, and compute protections remain separate operational controls.

A user is not a tenant. A project is not a tenant. A Dataset is not a run. Collapsing those distinctions later is a migration; separating them now is a constructor argument.

## 3. Request-scoped tenant context

### 3.1 The rule

Tenant identity is established **once, at the authenticated service boundary, from a verified credential**, and carried in a request-scoped context for the life of the request. It is never read from environment variables inside request handling, never passed as a tool argument, and never inferred from user prose.

Workspace / MMM Project scope is then resolved and authorized separately for project-scoped operations. Requests such as `/v1/me`, plan-catalog reads, billing settings, or project listing may have a tenant but no selected workspace. Do not make `workspace_id` mandatory in the base tenant context.

```text
Verified Clerk credential
        ↓
service middleware resolves tenant_id + user_id
        ↓
TenantContext bound to a ContextVar
        ↓
project-scoped endpoint authorizes requested workspace_id
        ↓
WorkspaceContext / require_workspace() binds project scope
        ↓
repositories, tools, and coordinators read request context
        ↓
context cleared on request completion
```

The public `/planner` path is intentionally outside this flow. It is deterministic and local/static at anonymous runtime. It does **not** call `prem3-api`, does **not** receive `TenantContext`, and does **not** require a backend anonymous session, PlanningRun, or claim handshake. There is no anonymous tenant, default tenant, or anonymous `auth_state` for `/planner`.

`app/core/run_repository.py` already uses the `ContextVar` pattern for the repository handle (`_current_repo: ContextVar[RunRepository | None]`). Generalize that seam rather than inventing an incompatible mechanism.

### 3.2 Proposed contract

```python
# app/core/tenancy.py

class TenantContext(BaseModel):
    tenant_id: str
    user_id: str | None = None
    auth_state: Literal["AUTHENTICATED", "SERVICE"]
    entitlement_snapshot_id: str | None = None


class WorkspaceContext(BaseModel):
    workspace_id: str
    dataset_id: str | None = None


_current_tenant: ContextVar[TenantContext | None] = ContextVar(
    "prem3_tenant_context", default=None
)
_current_workspace: ContextVar[WorkspaceContext | None] = ContextVar(
    "prem3_workspace_context", default=None
)


def require_tenant() -> TenantContext:
    """Fail closed. There is no default tenant."""
    ctx = _current_tenant.get()
    if ctx is None:
        raise TenantContextMissingError(
            "No tenant context bound. Refusing authenticated tenant operation."
        )
    return ctx


def require_workspace() -> WorkspaceContext:
    """Fail closed for project-scoped operations."""
    ctx = _current_workspace.get()
    if ctx is None:
        raise WorkspaceContextMissingError(
            "No authorized MMM Project context bound. Refusing project operation."
        )
    return ctx
```

`require_tenant()` and `require_workspace()` must raise rather than fall back to process settings or user-supplied identifiers. A silent default is how cross-tenant writes happen. `dataset_id` is resolved only after the Dataset is proven to belong to the already-authorized workspace.

### 3.3 What `Settings` keeps

`app/config.py` remains the authority for **infrastructure** identifiers and loses **tenant** identifiers:

| Keeps | Moves to `TenantContext` |
|---|---|
| `project_id`, `vertex_location`, `cloud_region` | `organization_id` / `tenant_id` |
| `raw_bucket`, `artifact_bucket` | `workspace_id`, `dataset_id` |
| `bq_ops_dataset`, `bq_experience_dataset`, `bq_models_dataset` (as *prefixes*) | |
| `gemini_model`, `runtime_sa`, `eda_job` | |

Retain `MODELREADY_ORGANIZATION_ID` / `MODELREADY_WORKSPACE_ID` **only** as a developer-CLI convenience that binds explicit tenant/workspace context at the top of `scripts/run_dataset_a.py` and friends. Mark them clearly as local-development bootstrapping, not runtime configuration. This preserves the existing golden path and demo scripts unchanged.

---

## 4. The agent must not be able to name a tenant

This is a security rule, not a design preference.

Planning Mode introduces free-text intake, provider research over untrusted web content, and multi-turn agent reasoning. If `tenant_id` or `workspace_id` is ever an argument the model can populate, then a prompt-injected page or a crafted user answer can direct a read or write at another customer.

Requirements:

- No ADK tool signature accepts `tenant_id`, `workspace_id`, `dataset_id`, `organization_id`, a GCS URI, or a BigQuery dataset/table name as a model-supplied argument. This extends the existing rule in `app/agent.py` ("Never supply … filesystem paths … or BigQuery destinations") from a prompt instruction to a schema-level guarantee.
- Tools resolve all storage targets through `require_tenant()` / `require_workspace()` plus a deterministic path builder. Dataset-scoped tools resolve `dataset_id` from server-owned run/resource state, never model arguments.
- A tool that receives an unexpected path-like argument fails closed and records a safety violation, consistent with `app/core/errors.SafetyViolationError`.
- Research-derived content (§ registry enrichment) is treated as **data, never instructions**. It cannot influence path resolution under any circumstance.

Add a test that reflects over every registered tool schema and asserts no tenant-or-path-shaped parameter exists.

---

## 5. Storage layout

### 5.1 Cloud Storage

Mission 2 makes Dataset durable. Preserve the existing tenant/workspace shape while nesting evaluation artifacts under Dataset where new paths are introduced.

```text
gs://<artifact-bucket>/<tenant_id>/<workspace_id>/planning/<planning_run_id>/...
gs://<artifact-bucket>/<tenant_id>/<workspace_id>/datasets/<dataset_id>/runs/<run_id>/...
gs://<artifact-bucket>/<tenant_id>/registry/overlay/...
gs://<raw-bucket>/<tenant_id>/<workspace_id>/datasets/<dataset_id>/uploads/<upload_id>/...
```

Existing golden-path objects such as `music-center/mmm-demo/runs/...` remain valid legacy/proof artifacts. Do not force a risky migration solely for path aesthetics; new authenticated Dataset resources use the new hierarchy and the repository may support both layouts during transition.

Path construction lives in exactly one module. Any code building a `gs://` string by concatenation outside that module is a defect.

### 5.2 BigQuery

Two different isolation problems, two different answers.

**Model-consumption contract (customer-facing).** One BigQuery dataset per tenant remains the isolation boundary. Customers may eventually be granted direct read on their own consumption views; row-level filtering in a shared customer dataset is not an acceptable substitute.

Existing run-oriented physical table names may remain to preserve the proven golden path. Mission 2 adds mandatory resource linkage in the model-ready registry / metadata:

```text
tenant_id
workspace_id       # MMM Project
dataset_id         # durable Dataset
run_id             # one Evaluation
```

A stable Dataset may therefore accumulate many verified Evaluation Runs. Do not encode pricing or run quotas in BigQuery naming.

**Ops and experience analytics (internal).** Shared datasets require mandatory `tenant_id`; project/dataset/run identifiers are additionally stored wherever the record is scoped below the tenant. Any tenant-facing query path must filter through authorized views/service logic. Never expose shared internal tables directly.

Dataset naming must be sanitized: `tenant_id` values reach BigQuery identifiers, so tenant IDs should be system-generated, not user-supplied strings.

### 5.3 Isolation is enforced in application code

There is one runtime service account. IAM does not separate tenants. That means **isolation is an application invariant and must be tested like one**, not assumed.

Minimum negative tests:

- `test_tenant_context_required` — repository operations raise without a bound context.
- `test_no_default_tenant_fallback` — clearing `TenantContext` never falls back to `settings`.
- `test_path_builder_rejects_traversal` — `../`, absolute paths, and empty segments are rejected.
- `test_tool_schemas_have_no_tenant_arguments` — reflective check over all ADK tools.
- `test_cross_tenant_read_denied` — a project, Dataset, plan, or run created under tenant A is not resolvable under tenant B by identifier alone.
- `test_cross_workspace_dataset_denied` — a Dataset from workspace A cannot be bound under workspace B even inside the same tenant.
- `test_run_belongs_to_dataset` — a run cannot be re-parented to a different Dataset through a request body or agent/tool argument.
- `test_context_cleared_between_requests` — no leakage across sequential requests in one process.

### 5.4 Firestore — Mission 2 operational control plane

Firestore is the selected Mission 2 operational control-plane store. It does not replace GCS artifact storage or BigQuery model-consumption / experience-ledger roles.

Store in Firestore:

- tenant ↔ Clerk Organization mappings (PreM3 `tenant_id` is the storage key; Clerk IDs are mapped attributes);
- membership projections;
- MMM Projects (`workspace_id`);
- Datasets (`dataset_id`) and Dataset-to-Evaluation linkage metadata;
- entitlement snapshots / projections;
- Stripe subscription projections (Stripe Customer/Price IDs are mapped attributes, never storage keys);
- webhook idempotency records;
- tenant registry overlay **metadata** (layer, version, trust, provenance pointers).

GCS retains raw uploads, planning artifacts, Dataset/Evaluation run artifacts, and any large overlay payload objects referenced by Firestore metadata. BigQuery retains model-consumption publication and the auditable ops/experience ledger. Vertex AI Memory Bank remains validated generalized memory only.

Do not use Clerk Organization IDs, Clerk User IDs, Stripe Customer IDs, or Stripe Price IDs as Firestore document IDs for tenant/project/dataset isolation, as GCS path segments, or as BigQuery dataset names.

---

## 6. Registry scoping

The provider registry becomes tenant-aware the moment Planning Mode can create entries. Today `app/registry/loader.py` is `@lru_cache(maxsize=1)`, reads one packaged JSON, and hard-fails unless the catalog contains exactly 52 entries — so it cannot hold runtime additions at all, let alone tenant-scoped ones.

Target composition, resolved in this order:

```text
1. BUNDLED     app/registry/providers/*.json      shipped, versioned, immutable at runtime
2. PROMOTED    global runtime store               validated, de-identified, cross-tenant
3. OVERLAY     tenant-scoped Firestore metadata   this tenant's researched/unknown providers
               (+ optional GCS payload objects)
```

Rules:

- Resolution precedence is OVERLAY → PROMOTED → BUNDLED, with the winning layer recorded on every resolution for provenance.
- An entry created by tenant A's intake is written to A's overlay only. Promotion to the global layer requires validation **and** de-identification, per the privacy boundary in the Planning scope (§13.10 there).
- Trust level and layer are orthogonal. An overlay entry may be `DIRECTORY` trust; it may not be `EXECUTABLE` on documentation alone.
- The `== 52` assertion becomes a bundled-layer manifest check (`len(bundled) == manifest.expected_count`), so seed integrity is still guarded without freezing the catalog.
- The `lru_cache` becomes a version-keyed cache. Any runtime write invalidates the composed catalog for that tenant only.
- `registry_version` in run identity (`02_SYSTEM_ARCHITECTURE.md` § Run identity) becomes a composite: `bundled@x.y.z + promoted@n + overlay@m`. Plans and Meridian Integration / model-consumption contracts pin it.

### 6.1 Public Planner manifest boundary

The anonymous PreM3 Planner does not query the tenant-aware registry at runtime. A build/export step may produce a versioned, non-sensitive Planner manifest from approved BUNDLED/PROMOTED provider metadata and deterministic planning rules. The manifest is shipped with the frontend and contains no tenant overlays, credentials, storage paths, or executable instructions.

Tenant OVERLAY entries are available only inside authenticated project workflows through `prem3-api`.

---

## 7. Public Planner state and authenticated conversion

Mission 2 supersedes the earlier assumption that the free lead-generation funnel creates an anonymous backend planning session.

### 7.1 Public Planner

The public `/planner` experience is deterministic and useful without registration. At anonymous runtime it must not invoke Gemini/Vertex AI, ADK, Meridian/EDA, BigQuery, GCS, autonomous registry research, file upload, or `prem3-api` planning execution.

Planner draft/result state may be kept in versioned, expiration-aware browser storage. It is **not tenant state**, is never an isolation key, and must contain no credentials or uploaded files. A generated `planner_manifest_version` should be recorded with the local result so stale drafts can be detected after rules change.

### 7.2 Conversion into an MMM Project

Conversion is explicit:

```text
Public Planner result
        ↓
Clerk sign-up / sign-in
        ↓
verified tenant context + entitlement check
        ↓
create or select MMM Project (workspace_id)
        ↓
optionally import Planner brief as candidate planning facts
        ↓
authenticated Planning Run
```

Imported Planner fields are **candidate / unconfirmed inputs**. The backend validates the manifest/schema version and records provenance; it must not silently promote local browser content to confirmed backend truth.

There is no anonymous GCS prefix, anonymous Firestore document, backend PlanningRun, or claim handshake required for the public Planner. Any earlier requirement that `/planner` create or claim anonymous backend session state is **SUPERSEDED**. If a future public backend workflow introduces anonymous server-side state, it must be separately specified with TTL, quarantine, rate limits, and one-way authenticated claim semantics before deployment.

## 8. Deletion and retention

A tenant deletion is a defined, testable operation, not a support ticket. It must remove:

- the GCS tenant prefix in both buckets;
- the tenant's BigQuery model-consumption dataset;
- tenant rows from shared ops/experience tables;
- the tenant registry overlay;
- planning reports/receipts, Dataset resources and Evaluation histories, and MEL episodes scoped to the tenant;
- any cached entitlement and Stripe subscription projection.

It must **not** remove globally promoted, de-identified registry knowledge, because that layer by construction contains no tenant-identifying content. If it does contain such content, the de-identification gate is broken and that is the bug to fix — not the deletion job.

Retention policy is per-tenant configuration with a documented default. Publish it before the free tier opens, because the free tier is where you will hold data for people who never signed a contract.

---

## 9. Sequencing

This work is the backend foundation for the Mission 2 frontend and should be implemented before live project/dataset integration.

| Order | Work | Blocks |
|---|---|---|
| 1 | `TenantContext` + `WorkspaceContext` + fail-closed path builder | everything below. **Local primitive implemented 2026-08-17** (`app/core/tenancy.py`, `app/core/resource_paths.py`). Not a service boundary. |
| 2 | Repository/tool refactor to context-based resolution | service layer |
| 3 | Isolation test suite (§5.3) | any public authenticated deployment |
| 4 | First-class MMM Project (`workspace_id`) + Dataset (`dataset_id`) resource persistence | planning, uploads, evaluation history |
| 5 | Registry layer composition + versioned public Planner manifest export | authenticated planning + free Planner synchronization |
| 6 | Tenant deletion/retention including projects/datasets/plans/subscription projection | GA / public paid launch |

The free Planner itself does not wait on these steps because it is local/static at anonymous runtime. Any transition from Planner into saved planning or data execution begins only after authenticated tenant/project resolution.

## 10. Non-goals

- Per-tenant service accounts or per-tenant GCP projects. One runtime identity, application-enforced isolation, tested.
- Customer-managed encryption keys.
- Region pinning / data residency selection.
- Cross-tenant sharing of plans, projects, or datasets.
- Charging or metering by Evaluation Run. Commercial plans gate active MMM Projects; operational compute protections are separate.
- Replacing the existing `run_id` idempotency semantics.

Each is a real enterprise requirement and none belongs in the first multi-tenant cut. Record them in `08_DECISION_LOG.md` as deferred with a reason, so they are not re-litigated mid-build.
