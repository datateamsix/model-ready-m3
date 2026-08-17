"""In-memory ControlPlaneRepository for CI, API tests, and concurrency proofs.

Not more permissive than Firestore. Uses an RLock around mutating transactions.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock

from app.control_plane.entitlements import default_planner_entitlement
from app.control_plane.ids import new_dataset_id, new_tenant_id, new_workspace_id
from app.control_plane.layout import (
    billing_customer_doc_id,
    billing_subscription_doc_id,
    identity_mapping_doc_id,
    membership_doc_id,
    webhook_event_doc_id,
)
from app.control_plane.models import (
    BillingProvider,
    Dataset,
    DatasetEvaluationRef,
    DatasetStatus,
    EntitlementSnapshot,
    IdentityProviderOrganizationMapping,
    MembershipProjection,
    ProcessedWebhookEvent,
    StripeCustomerMapping,
    SubscriptionProjection,
    Tenant,
    TenantStatus,
    WebhookClaimResult,
    WebhookClaimStatus,
    WebhookEventStatus,
    WebhookProvider,
    Workspace,
    WorkspaceStatus,
)
from app.core.errors import (
    DatasetNotFoundError,
    EntitlementUnavailableError,
    ProjectLimitReachedError,
    ProviderMappingConflictError,
    TenantNotFoundError,
    WebhookAlreadyProcessedError,
    WorkspaceNotFoundError,
)
from app.core.identifiers import validate_resource_identifier


class InMemoryControlPlaneRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._tenants: dict[str, Tenant] = {}
        self._identity_mappings: dict[str, IdentityProviderOrganizationMapping] = {}
        self._memberships: dict[str, MembershipProjection] = {}
        self._workspaces: dict[str, Workspace] = {}
        self._datasets: dict[str, Dataset] = {}
        self._entitlements: dict[str, EntitlementSnapshot] = {}
        self._customers: dict[str, StripeCustomerMapping] = {}
        self._subscriptions: dict[str, SubscriptionProjection] = {}
        self._webhooks: dict[str, ProcessedWebhookEvent] = {}
        self._evaluation_refs: dict[str, DatasetEvaluationRef] = {}

    def create_tenant(
        self,
        *,
        display_name: str,
        identity_mapping: IdentityProviderOrganizationMapping | None = None,
        with_planner_entitlement: bool = True,
    ) -> Tenant:
        with self._lock:
            now = datetime.now(UTC)
            tenant_id = new_tenant_id()
            tenant = Tenant(
                tenant_id=tenant_id,
                display_name=display_name,
                status=TenantStatus.ACTIVE,
                created_at=now,
                updated_at=now,
                current_entitlement_snapshot_id=None,
                active_workspace_count=0,
            )
            self._tenants[tenant_id] = tenant
            if identity_mapping is not None:
                mapped = identity_mapping.model_copy(
                    update={
                        "tenant_id": tenant_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                self._put_identity_mapping_locked(mapped)
            if with_planner_entitlement:
                snapshot = default_planner_entitlement(tenant_id=tenant_id, now=now)
                self._put_entitlement_locked(snapshot, make_current=True)
                tenant = self._tenants[tenant_id]
            return deepcopy(tenant)

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            return deepcopy(tenant) if tenant is not None else None

    def set_tenant_status(self, *, tenant_id: str, status: str) -> Tenant:
        with self._lock:
            tenant = self._require_tenant_locked(tenant_id)
            updated = tenant.model_copy(
                update={"status": TenantStatus(status), "updated_at": datetime.now(UTC)}
            )
            self._tenants[tenant_id] = updated
            return deepcopy(updated)

    def put_identity_organization_mapping(
        self, mapping: IdentityProviderOrganizationMapping
    ) -> IdentityProviderOrganizationMapping:
        with self._lock:
            return deepcopy(self._put_identity_mapping_locked(mapping))

    def get_tenant_id_for_provider_org(
        self, *, provider: str, provider_organization_id: str
    ) -> str | None:
        mapping = self.get_identity_organization_mapping(
            provider=provider, provider_organization_id=provider_organization_id
        )
        return mapping.tenant_id if mapping is not None else None

    def get_identity_organization_mapping(
        self, *, provider: str, provider_organization_id: str
    ) -> IdentityProviderOrganizationMapping | None:
        with self._lock:
            key = identity_mapping_doc_id(provider, provider_organization_id)
            mapping = self._identity_mappings.get(key)
            return deepcopy(mapping) if mapping is not None else None

    def upsert_membership_projection(
        self, membership: MembershipProjection
    ) -> MembershipProjection:
        with self._lock:
            self._require_tenant_locked(membership.tenant_id)
            key = (
                f"{membership.tenant_id}/"
                f"{membership_doc_id(membership.provider, membership.provider_user_id)}"
            )
            self._memberships[key] = membership
            return deepcopy(membership)

    def get_membership_projection(
        self,
        *,
        tenant_id: str,
        provider: str,
        provider_user_id: str,
    ) -> MembershipProjection | None:
        with self._lock:
            key = f"{tenant_id}/{membership_doc_id(provider, provider_user_id)}"
            membership = self._memberships.get(key)
            return deepcopy(membership) if membership is not None else None

    def list_workspaces_for_tenant(self, tenant_id: str) -> list[Workspace]:
        with self._lock:
            self._require_tenant_locked(tenant_id)
            rows = [
                deepcopy(ws)
                for key, ws in self._workspaces.items()
                if key.startswith(f"{tenant_id}/")
            ]
            rows.sort(key=lambda item: item.created_at)
            return rows

    def get_workspace_for_tenant(
        self, *, tenant_id: str, workspace_id: str
    ) -> Workspace | None:
        with self._lock:
            ws = self._workspaces.get(f"{tenant_id}/{workspace_id}")
            if ws is None or ws.tenant_id != tenant_id:
                return None
            return deepcopy(ws)

    def create_workspace_with_capacity(
        self, *, tenant_id: str, name: str, workspace_id: str | None = None
    ) -> Workspace:
        with self._lock:
            tenant = self._require_tenant_locked(tenant_id)
            entitlement = self._require_current_entitlement_locked(tenant_id)
            if tenant.active_workspace_count >= entitlement.max_active_projects:
                raise ProjectLimitReachedError(
                    "Active MMM Project capacity reached for current entitlement."
                )
            now = datetime.now(UTC)
            wsp_id = workspace_id or new_workspace_id()
            validate_resource_identifier(wsp_id, field="workspace_id")
            key = f"{tenant_id}/{wsp_id}"
            if key in self._workspaces:
                raise ProviderMappingConflictError("workspace_id already exists for tenant.")
            workspace = Workspace(
                tenant_id=tenant_id,
                workspace_id=wsp_id,
                name=name,
                status=WorkspaceStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            self._workspaces[key] = workspace
            self._tenants[tenant_id] = tenant.model_copy(
                update={
                    "active_workspace_count": tenant.active_workspace_count + 1,
                    "updated_at": now,
                }
            )
            return deepcopy(workspace)

    def list_datasets_for_workspace(
        self, *, tenant_id: str, workspace_id: str
    ) -> list[Dataset]:
        with self._lock:
            self._require_workspace_locked(tenant_id, workspace_id)
            prefix = f"{tenant_id}/{workspace_id}/"
            rows = [
                deepcopy(ds)
                for key, ds in self._datasets.items()
                if key.startswith(prefix)
            ]
            rows.sort(key=lambda item: item.created_at)
            return rows

    def get_dataset_for_workspace(
        self, *, tenant_id: str, workspace_id: str, dataset_id: str
    ) -> Dataset | None:
        with self._lock:
            ds = self._datasets.get(f"{tenant_id}/{workspace_id}/{dataset_id}")
            if ds is None:
                return None
            if ds.tenant_id != tenant_id or ds.workspace_id != workspace_id:
                return None
            return deepcopy(ds)

    def create_dataset(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        name: str,
        dataset_id: str | None = None,
    ) -> Dataset:
        with self._lock:
            self._require_workspace_locked(tenant_id, workspace_id)
            now = datetime.now(UTC)
            dset_id = dataset_id or new_dataset_id()
            validate_resource_identifier(dset_id, field="dataset_id")
            key = f"{tenant_id}/{workspace_id}/{dset_id}"
            if key in self._datasets:
                raise ProviderMappingConflictError("dataset_id already exists for workspace.")
            dataset = Dataset(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                dataset_id=dset_id,
                name=name,
                status=DatasetStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            self._datasets[key] = dataset
            return deepcopy(dataset)

    def put_entitlement_snapshot(
        self, snapshot: EntitlementSnapshot, *, make_current: bool = True
    ) -> EntitlementSnapshot:
        with self._lock:
            return deepcopy(self._put_entitlement_locked(snapshot, make_current=make_current))

    def get_entitlement_snapshot(
        self, *, tenant_id: str, snapshot_id: str
    ) -> EntitlementSnapshot | None:
        with self._lock:
            snap = self._entitlements.get(f"{tenant_id}/{snapshot_id}")
            if snap is None or snap.tenant_id != tenant_id:
                return None
            return deepcopy(snap)

    def get_current_entitlement(self, tenant_id: str) -> EntitlementSnapshot:
        with self._lock:
            return deepcopy(self._require_current_entitlement_locked(tenant_id))

    def put_stripe_customer_mapping(
        self, mapping: StripeCustomerMapping
    ) -> StripeCustomerMapping:
        with self._lock:
            self._require_tenant_locked(mapping.tenant_id)
            key = f"{mapping.tenant_id}/{billing_customer_doc_id(mapping.billing_provider)}"
            self._customers[key] = mapping
            return deepcopy(mapping)

    def get_stripe_customer_mapping(self, tenant_id: str) -> StripeCustomerMapping | None:
        with self._lock:
            key = f"{tenant_id}/{billing_customer_doc_id(BillingProvider.STRIPE)}"
            mapping = self._customers.get(key)
            return deepcopy(mapping) if mapping is not None else None

    def put_subscription_projection(
        self, projection: SubscriptionProjection
    ) -> SubscriptionProjection:
        with self._lock:
            self._require_tenant_locked(projection.tenant_id)
            key = (
                f"{projection.tenant_id}/"
                f"{billing_subscription_doc_id(projection.billing_provider)}"
            )
            self._subscriptions[key] = projection
            return deepcopy(projection)

    def get_subscription_projection(self, tenant_id: str) -> SubscriptionProjection | None:
        with self._lock:
            key = f"{tenant_id}/{billing_subscription_doc_id(BillingProvider.STRIPE)}"
            projection = self._subscriptions.get(key)
            return deepcopy(projection) if projection is not None else None

    def claim_webhook_event(
        self,
        *,
        provider: WebhookProvider | str,
        provider_event_id: str,
        event_type: str,
    ) -> WebhookClaimResult:
        with self._lock:
            key = webhook_event_doc_id(provider, provider_event_id)
            existing = self._webhooks.get(key)
            now = datetime.now(UTC)
            provider_enum = (
                provider if isinstance(provider, WebhookProvider) else WebhookProvider(provider)
            )
            if existing is None or existing.status == WebhookEventStatus.FAILED:
                event = ProcessedWebhookEvent(
                    provider=provider_enum,
                    provider_event_id=provider_event_id,
                    event_type=event_type,
                    status=WebhookEventStatus.CLAIMED,
                    claimed_at=now,
                    processed_at=None,
                    result=None,
                )
                self._webhooks[key] = event
                return WebhookClaimResult(status=WebhookClaimStatus.WON, event=deepcopy(event))
            if existing.status == WebhookEventStatus.PROCESSED:
                return WebhookClaimResult(
                    status=WebhookClaimStatus.ALREADY_PROCESSED,
                    event=deepcopy(existing),
                )
            return WebhookClaimResult(
                status=WebhookClaimStatus.ALREADY_CLAIMED,
                event=deepcopy(existing),
            )

    def mark_webhook_event_processed(
        self,
        *,
        provider: WebhookProvider | str,
        provider_event_id: str,
        result: str | None = None,
    ) -> ProcessedWebhookEvent:
        with self._lock:
            key = webhook_event_doc_id(provider, provider_event_id)
            existing = self._webhooks.get(key)
            if existing is None:
                raise WebhookAlreadyProcessedError("Webhook event was not claimed.")
            if existing.status == WebhookEventStatus.PROCESSED:
                return deepcopy(existing)
            updated = existing.model_copy(
                update={
                    "status": WebhookEventStatus.PROCESSED,
                    "processed_at": datetime.now(UTC),
                    "result": result,
                }
            )
            self._webhooks[key] = updated
            return deepcopy(updated)

    def mark_webhook_event_failed(
        self,
        *,
        provider: WebhookProvider | str,
        provider_event_id: str,
        result: str | None = None,
    ) -> ProcessedWebhookEvent:
        with self._lock:
            key = webhook_event_doc_id(provider, provider_event_id)
            existing = self._webhooks.get(key)
            if existing is None:
                raise WebhookAlreadyProcessedError("Webhook event was not claimed.")
            updated = existing.model_copy(
                update={
                    "status": WebhookEventStatus.FAILED,
                    "processed_at": datetime.now(UTC),
                    "result": result,
                }
            )
            self._webhooks[key] = updated
            return deepcopy(updated)

    def get_webhook_event(
        self, *, provider: WebhookProvider | str, provider_event_id: str
    ) -> ProcessedWebhookEvent | None:
        with self._lock:
            event = self._webhooks.get(webhook_event_doc_id(provider, provider_event_id))
            return deepcopy(event) if event is not None else None

    def put_evaluation_ref(self, ref: DatasetEvaluationRef) -> DatasetEvaluationRef:
        with self._lock:
            dataset = self.get_dataset_for_workspace(
                tenant_id=ref.tenant_id,
                workspace_id=ref.workspace_id,
                dataset_id=ref.dataset_id,
            )
            if dataset is None:
                raise DatasetNotFoundError("Dataset does not exist for evaluation linkage.")
            key = f"{ref.tenant_id}/{ref.run_id}"
            self._evaluation_refs[key] = ref
            return deepcopy(ref)

    def get_evaluation_ref(
        self, *, tenant_id: str, run_id: str
    ) -> DatasetEvaluationRef | None:
        with self._lock:
            ref = self._evaluation_refs.get(f"{tenant_id}/{run_id}")
            if ref is None or ref.tenant_id != tenant_id:
                return None
            return deepcopy(ref)

    # --- locked helpers ---

    def _put_identity_mapping_locked(
        self, mapping: IdentityProviderOrganizationMapping
    ) -> IdentityProviderOrganizationMapping:
        self._require_tenant_locked(mapping.tenant_id)
        key = identity_mapping_doc_id(mapping.provider, mapping.provider_organization_id)
        existing = self._identity_mappings.get(key)
        if existing is not None and existing.tenant_id != mapping.tenant_id:
            raise ProviderMappingConflictError(
                "Provider organization is already mapped to another PreM3 tenant."
            )
        self._identity_mappings[key] = mapping
        return mapping

    def _put_entitlement_locked(
        self, snapshot: EntitlementSnapshot, *, make_current: bool
    ) -> EntitlementSnapshot:
        tenant = self._require_tenant_locked(snapshot.tenant_id)
        key = f"{snapshot.tenant_id}/{snapshot.snapshot_id}"
        existing = self._entitlements.get(key)
        if existing is not None and existing != snapshot:
            raise ProviderMappingConflictError(
                "Entitlement snapshot_id is immutable and already exists with different content."
            )
        if existing is None:
            self._entitlements[key] = snapshot
        if make_current:
            self._tenants[snapshot.tenant_id] = tenant.model_copy(
                update={
                    "current_entitlement_snapshot_id": snapshot.snapshot_id,
                    "updated_at": datetime.now(UTC),
                }
            )
        return snapshot

    def _require_tenant_locked(self, tenant_id: str) -> Tenant:
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant does not exist.")
        return tenant

    def _require_workspace_locked(self, tenant_id: str, workspace_id: str) -> Workspace:
        self._require_tenant_locked(tenant_id)
        workspace = self._workspaces.get(f"{tenant_id}/{workspace_id}")
        if workspace is None or workspace.tenant_id != tenant_id:
            raise WorkspaceNotFoundError("MMM Project does not exist.")
        return workspace

    def _require_current_entitlement_locked(self, tenant_id: str) -> EntitlementSnapshot:
        tenant = self._require_tenant_locked(tenant_id)
        if tenant.current_entitlement_snapshot_id is None:
            raise EntitlementUnavailableError("No current entitlement snapshot for tenant.")
        snap = self._entitlements.get(
            f"{tenant_id}/{tenant.current_entitlement_snapshot_id}"
        )
        if snap is None:
            raise EntitlementUnavailableError("Current entitlement snapshot is missing.")
        return snap
