"""Firestore-backed ControlPlaneRepository.

Uses google.cloud.firestore.Client (sync) with ADC or FIRESTORE_EMULATOR_HOST.
Inject the client — no hidden module-level singleton required by callers.
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud import firestore
from google.cloud.firestore import transactional

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
from app.control_plane.serialization import document_to_model, model_to_document
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

COLLECTION_TENANTS = "tenants"
COLLECTION_IDENTITY_MAPPINGS = "identity_org_mappings"
COLLECTION_MEMBERSHIPS = "memberships"
COLLECTION_WORKSPACES = "workspaces"
COLLECTION_DATASETS = "datasets"
COLLECTION_ENTITLEMENTS = "entitlements"
COLLECTION_BILLING_CUSTOMERS = "billing_customers"
COLLECTION_BILLING_SUBSCRIPTIONS = "billing_subscriptions"
COLLECTION_EVALUATION_REFS = "evaluation_refs"
COLLECTION_WEBHOOKS = "processed_webhook_events"


class FirestoreControlPlaneRepository:
    def __init__(self, client: firestore.Client) -> None:
        self._db = client

    @classmethod
    def from_settings(
        cls,
        *,
        project_id: str,
        database: str = "(default)",
    ) -> FirestoreControlPlaneRepository:
        return cls(firestore.Client(project=project_id, database=database))

    # --- refs ---

    def _tenant_ref(self, tenant_id: str):
        return self._db.collection(COLLECTION_TENANTS).document(tenant_id)

    def _workspace_ref(self, tenant_id: str, workspace_id: str):
        return (
            self._tenant_ref(tenant_id)
            .collection(COLLECTION_WORKSPACES)
            .document(workspace_id)
        )

    def _dataset_ref(self, tenant_id: str, workspace_id: str, dataset_id: str):
        return (
            self._workspace_ref(tenant_id, workspace_id)
            .collection(COLLECTION_DATASETS)
            .document(dataset_id)
        )

    def _entitlement_ref(self, tenant_id: str, snapshot_id: str):
        return (
            self._tenant_ref(tenant_id)
            .collection(COLLECTION_ENTITLEMENTS)
            .document(snapshot_id)
        )

    def _membership_ref(self, tenant_id: str, provider: str, provider_user_id: str):
        return (
            self._tenant_ref(tenant_id)
            .collection(COLLECTION_MEMBERSHIPS)
            .document(membership_doc_id(provider, provider_user_id))
        )

    def _customer_ref(self, tenant_id: str, billing_provider: BillingProvider | str):
        return (
            self._tenant_ref(tenant_id)
            .collection(COLLECTION_BILLING_CUSTOMERS)
            .document(billing_customer_doc_id(billing_provider))
        )

    def _subscription_ref(self, tenant_id: str, billing_provider: BillingProvider | str):
        return (
            self._tenant_ref(tenant_id)
            .collection(COLLECTION_BILLING_SUBSCRIPTIONS)
            .document(billing_subscription_doc_id(billing_provider))
        )

    def _evaluation_ref_doc(self, tenant_id: str, run_id: str):
        return (
            self._tenant_ref(tenant_id)
            .collection(COLLECTION_EVALUATION_REFS)
            .document(run_id)
        )

    def _identity_ref(self, provider: str, provider_organization_id: str):
        return self._db.collection(COLLECTION_IDENTITY_MAPPINGS).document(
            identity_mapping_doc_id(provider, provider_organization_id)
        )

    def _webhook_ref(self, provider: WebhookProvider | str, provider_event_id: str):
        return self._db.collection(COLLECTION_WEBHOOKS).document(
            webhook_event_doc_id(provider, provider_event_id)
        )

    # --- Tenant ---

    def create_tenant(
        self,
        *,
        display_name: str,
        identity_mapping: IdentityProviderOrganizationMapping | None = None,
        with_planner_entitlement: bool = True,
    ) -> Tenant:
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
        batch = self._db.batch()
        batch.create(self._tenant_ref(tenant_id), model_to_document(tenant))
        if identity_mapping is not None:
            mapped = identity_mapping.model_copy(
                update={"tenant_id": tenant_id, "created_at": now, "updated_at": now}
            )
            mapping_ref = self._identity_ref(
                mapped.provider.value, mapped.provider_organization_id
            )
            existing = mapping_ref.get()
            if existing.exists:
                prior = document_to_model(
                    IdentityProviderOrganizationMapping, existing.to_dict()
                )
                if prior.tenant_id != tenant_id:
                    raise ProviderMappingConflictError(
                        "Provider organization is already mapped to another PreM3 tenant."
                    )
            batch.set(mapping_ref, model_to_document(mapped))
        if with_planner_entitlement:
            snapshot = default_planner_entitlement(tenant_id=tenant_id, now=now)
            batch.create(
                self._entitlement_ref(tenant_id, snapshot.snapshot_id),
                model_to_document(snapshot),
            )
            tenant = tenant.model_copy(
                update={"current_entitlement_snapshot_id": snapshot.snapshot_id}
            )
            batch.set(self._tenant_ref(tenant_id), model_to_document(tenant))
        batch.commit()
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        snap = self._tenant_ref(tenant_id).get()
        if not snap.exists:
            return None
        return document_to_model(Tenant, snap.to_dict())

    def set_tenant_status(self, *, tenant_id: str, status: str) -> Tenant:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant does not exist.")
        updated = tenant.model_copy(
            update={"status": TenantStatus(status), "updated_at": datetime.now(UTC)}
        )
        self._tenant_ref(tenant_id).set(model_to_document(updated))
        return updated

    def put_identity_organization_mapping(
        self, mapping: IdentityProviderOrganizationMapping
    ) -> IdentityProviderOrganizationMapping:
        if self.get_tenant(mapping.tenant_id) is None:
            raise TenantNotFoundError("Tenant does not exist.")
        ref = self._identity_ref(mapping.provider.value, mapping.provider_organization_id)
        existing = ref.get()
        if existing.exists:
            prior = document_to_model(
                IdentityProviderOrganizationMapping, existing.to_dict()
            )
            if prior.tenant_id != mapping.tenant_id:
                raise ProviderMappingConflictError(
                    "Provider organization is already mapped to another PreM3 tenant."
                )
        ref.set(model_to_document(mapping))
        return mapping

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
        snap = self._identity_ref(provider, provider_organization_id).get()
        if not snap.exists:
            return None
        return document_to_model(IdentityProviderOrganizationMapping, snap.to_dict())

    def upsert_membership_projection(
        self, membership: MembershipProjection
    ) -> MembershipProjection:
        if self.get_tenant(membership.tenant_id) is None:
            raise TenantNotFoundError("Tenant does not exist.")
        self._membership_ref(
            membership.tenant_id,
            membership.provider.value,
            membership.provider_user_id,
        ).set(model_to_document(membership))
        return membership

    def get_membership_projection(
        self,
        *,
        tenant_id: str,
        provider: str,
        provider_user_id: str,
    ) -> MembershipProjection | None:
        snap = self._membership_ref(tenant_id, provider, provider_user_id).get()
        if not snap.exists:
            return None
        return document_to_model(MembershipProjection, snap.to_dict())

    def list_workspaces_for_tenant(self, tenant_id: str) -> list[Workspace]:
        if self.get_tenant(tenant_id) is None:
            raise TenantNotFoundError("Tenant does not exist.")
        rows: list[Workspace] = []
        for snap in self._tenant_ref(tenant_id).collection(COLLECTION_WORKSPACES).stream():
            rows.append(document_to_model(Workspace, snap.to_dict()))
        rows.sort(key=lambda item: item.created_at)
        return rows

    def get_workspace_for_tenant(
        self, *, tenant_id: str, workspace_id: str
    ) -> Workspace | None:
        snap = self._workspace_ref(tenant_id, workspace_id).get()
        if not snap.exists:
            return None
        workspace = document_to_model(Workspace, snap.to_dict())
        if workspace.tenant_id != tenant_id:
            return None
        return workspace

    def create_workspace_with_capacity(
        self, *, tenant_id: str, name: str, workspace_id: str | None = None
    ) -> Workspace:
        wsp_id = workspace_id or new_workspace_id()
        validate_resource_identifier(wsp_id, field="workspace_id")
        transaction = self._db.transaction()

        @transactional
        def _create(txn: firestore.Transaction) -> Workspace:
            tenant_ref = self._tenant_ref(tenant_id)
            tenant_snap = tenant_ref.get(transaction=txn)
            if not tenant_snap.exists:
                raise TenantNotFoundError("Tenant does not exist.")
            tenant = document_to_model(Tenant, tenant_snap.to_dict())
            if tenant.current_entitlement_snapshot_id is None:
                raise EntitlementUnavailableError(
                    "No current entitlement snapshot for tenant."
                )
            ent_ref = self._entitlement_ref(
                tenant_id, tenant.current_entitlement_snapshot_id
            )
            ent_snap = ent_ref.get(transaction=txn)
            if not ent_snap.exists:
                raise EntitlementUnavailableError("Current entitlement snapshot is missing.")
            entitlement = document_to_model(EntitlementSnapshot, ent_snap.to_dict())
            if tenant.active_workspace_count >= entitlement.max_active_projects:
                raise ProjectLimitReachedError(
                    "Active MMM Project capacity reached for current entitlement."
                )
            workspace_ref = self._workspace_ref(tenant_id, wsp_id)
            existing = workspace_ref.get(transaction=txn)
            if existing.exists:
                raise ProviderMappingConflictError(
                    "workspace_id already exists for tenant."
                )
            now = datetime.now(UTC)
            workspace = Workspace(
                tenant_id=tenant_id,
                workspace_id=wsp_id,
                name=name,
                status=WorkspaceStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            txn.create(workspace_ref, model_to_document(workspace))
            updated_tenant = tenant.model_copy(
                update={
                    "active_workspace_count": tenant.active_workspace_count + 1,
                    "updated_at": now,
                }
            )
            txn.set(tenant_ref, model_to_document(updated_tenant))
            return workspace

        return _create(transaction)

    def list_datasets_for_workspace(
        self, *, tenant_id: str, workspace_id: str
    ) -> list[Dataset]:
        if self.get_workspace_for_tenant(tenant_id=tenant_id, workspace_id=workspace_id) is None:
            raise WorkspaceNotFoundError("MMM Project does not exist.")
        rows: list[Dataset] = []
        for snap in (
            self._workspace_ref(tenant_id, workspace_id)
            .collection(COLLECTION_DATASETS)
            .stream()
        ):
            rows.append(document_to_model(Dataset, snap.to_dict()))
        rows.sort(key=lambda item: item.created_at)
        return rows

    def get_dataset_for_workspace(
        self, *, tenant_id: str, workspace_id: str, dataset_id: str
    ) -> Dataset | None:
        snap = self._dataset_ref(tenant_id, workspace_id, dataset_id).get()
        if not snap.exists:
            return None
        dataset = document_to_model(Dataset, snap.to_dict())
        if dataset.tenant_id != tenant_id or dataset.workspace_id != workspace_id:
            return None
        return dataset

    def create_dataset(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        name: str,
        dataset_id: str | None = None,
    ) -> Dataset:
        if self.get_workspace_for_tenant(tenant_id=tenant_id, workspace_id=workspace_id) is None:
            raise WorkspaceNotFoundError("MMM Project does not exist.")
        dset_id = dataset_id or new_dataset_id()
        validate_resource_identifier(dset_id, field="dataset_id")
        ref = self._dataset_ref(tenant_id, workspace_id, dset_id)
        if ref.get().exists:
            raise ProviderMappingConflictError("dataset_id already exists for workspace.")
        now = datetime.now(UTC)
        dataset = Dataset(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            dataset_id=dset_id,
            name=name,
            status=DatasetStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        ref.create(model_to_document(dataset))
        return dataset

    def put_entitlement_snapshot(
        self, snapshot: EntitlementSnapshot, *, make_current: bool = True
    ) -> EntitlementSnapshot:
        tenant = self.get_tenant(snapshot.tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant does not exist.")
        ref = self._entitlement_ref(snapshot.tenant_id, snapshot.snapshot_id)
        existing = ref.get()
        if existing.exists:
            prior = document_to_model(EntitlementSnapshot, existing.to_dict())
            if prior != snapshot:
                raise ProviderMappingConflictError(
                    "Entitlement snapshot_id is immutable and already exists "
                    "with different content."
                )
        else:
            ref.create(model_to_document(snapshot))
        if make_current:
            updated = tenant.model_copy(
                update={
                    "current_entitlement_snapshot_id": snapshot.snapshot_id,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._tenant_ref(snapshot.tenant_id).set(model_to_document(updated))
        return snapshot

    def get_entitlement_snapshot(
        self, *, tenant_id: str, snapshot_id: str
    ) -> EntitlementSnapshot | None:
        snap = self._entitlement_ref(tenant_id, snapshot_id).get()
        if not snap.exists:
            return None
        entitlement = document_to_model(EntitlementSnapshot, snap.to_dict())
        if entitlement.tenant_id != tenant_id:
            return None
        return entitlement

    def get_current_entitlement(self, tenant_id: str) -> EntitlementSnapshot:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant does not exist.")
        if tenant.current_entitlement_snapshot_id is None:
            raise EntitlementUnavailableError("No current entitlement snapshot for tenant.")
        snap = self.get_entitlement_snapshot(
            tenant_id=tenant_id, snapshot_id=tenant.current_entitlement_snapshot_id
        )
        if snap is None:
            raise EntitlementUnavailableError("Current entitlement snapshot is missing.")
        return snap

    def put_stripe_customer_mapping(
        self, mapping: StripeCustomerMapping
    ) -> StripeCustomerMapping:
        if self.get_tenant(mapping.tenant_id) is None:
            raise TenantNotFoundError("Tenant does not exist.")
        self._customer_ref(mapping.tenant_id, mapping.billing_provider).set(
            model_to_document(mapping)
        )
        return mapping

    def get_stripe_customer_mapping(self, tenant_id: str) -> StripeCustomerMapping | None:
        snap = self._customer_ref(tenant_id, BillingProvider.STRIPE).get()
        if not snap.exists:
            return None
        return document_to_model(StripeCustomerMapping, snap.to_dict())

    def put_subscription_projection(
        self, projection: SubscriptionProjection
    ) -> SubscriptionProjection:
        if self.get_tenant(projection.tenant_id) is None:
            raise TenantNotFoundError("Tenant does not exist.")
        self._subscription_ref(projection.tenant_id, projection.billing_provider).set(
            model_to_document(projection)
        )
        return projection

    def get_subscription_projection(self, tenant_id: str) -> SubscriptionProjection | None:
        snap = self._subscription_ref(tenant_id, BillingProvider.STRIPE).get()
        if not snap.exists:
            return None
        return document_to_model(SubscriptionProjection, snap.to_dict())

    def claim_webhook_event(
        self,
        *,
        provider: WebhookProvider | str,
        provider_event_id: str,
        event_type: str,
    ) -> WebhookClaimResult:
        transaction = self._db.transaction()
        provider_enum = (
            provider if isinstance(provider, WebhookProvider) else WebhookProvider(provider)
        )

        @transactional
        def _claim(txn: firestore.Transaction) -> WebhookClaimResult:
            ref = self._webhook_ref(provider_enum, provider_event_id)
            snap = ref.get(transaction=txn)
            now = datetime.now(UTC)
            if snap.exists:
                existing = document_to_model(ProcessedWebhookEvent, snap.to_dict())
                if existing.status == WebhookEventStatus.FAILED:
                    event = ProcessedWebhookEvent(
                        provider=provider_enum,
                        provider_event_id=provider_event_id,
                        event_type=event_type,
                        status=WebhookEventStatus.CLAIMED,
                        claimed_at=now,
                        processed_at=None,
                        result=None,
                    )
                    txn.set(ref, model_to_document(event))
                    return WebhookClaimResult(status=WebhookClaimStatus.WON, event=event)
                if existing.status == WebhookEventStatus.PROCESSED:
                    return WebhookClaimResult(
                        status=WebhookClaimStatus.ALREADY_PROCESSED, event=existing
                    )
                return WebhookClaimResult(
                    status=WebhookClaimStatus.ALREADY_CLAIMED, event=existing
                )
            event = ProcessedWebhookEvent(
                provider=provider_enum,
                provider_event_id=provider_event_id,
                event_type=event_type,
                status=WebhookEventStatus.CLAIMED,
                claimed_at=now,
                processed_at=None,
                result=None,
            )
            txn.create(ref, model_to_document(event))
            return WebhookClaimResult(status=WebhookClaimStatus.WON, event=event)

        return _claim(transaction)

    def mark_webhook_event_processed(
        self,
        *,
        provider: WebhookProvider | str,
        provider_event_id: str,
        result: str | None = None,
    ) -> ProcessedWebhookEvent:
        ref = self._webhook_ref(provider, provider_event_id)
        snap = ref.get()
        if not snap.exists:
            raise WebhookAlreadyProcessedError("Webhook event was not claimed.")
        existing = document_to_model(ProcessedWebhookEvent, snap.to_dict())
        if existing.status == WebhookEventStatus.PROCESSED:
            return existing
        updated = existing.model_copy(
            update={
                "status": WebhookEventStatus.PROCESSED,
                "processed_at": datetime.now(UTC),
                "result": result,
            }
        )
        ref.set(model_to_document(updated))
        return updated

    def mark_webhook_event_failed(
        self,
        *,
        provider: WebhookProvider | str,
        provider_event_id: str,
        result: str | None = None,
    ) -> ProcessedWebhookEvent:
        ref = self._webhook_ref(provider, provider_event_id)
        snap = ref.get()
        if not snap.exists:
            raise WebhookAlreadyProcessedError("Webhook event was not claimed.")
        existing = document_to_model(ProcessedWebhookEvent, snap.to_dict())
        updated = existing.model_copy(
            update={
                "status": WebhookEventStatus.FAILED,
                "processed_at": datetime.now(UTC),
                "result": result,
            }
        )
        ref.set(model_to_document(updated))
        return updated

    def get_webhook_event(
        self, *, provider: WebhookProvider | str, provider_event_id: str
    ) -> ProcessedWebhookEvent | None:
        snap = self._webhook_ref(provider, provider_event_id).get()
        if not snap.exists:
            return None
        return document_to_model(ProcessedWebhookEvent, snap.to_dict())

    def put_evaluation_ref(self, ref: DatasetEvaluationRef) -> DatasetEvaluationRef:
        dataset = self.get_dataset_for_workspace(
            tenant_id=ref.tenant_id,
            workspace_id=ref.workspace_id,
            dataset_id=ref.dataset_id,
        )
        if dataset is None:
            raise DatasetNotFoundError("Dataset does not exist for evaluation linkage.")
        self._evaluation_ref_doc(ref.tenant_id, ref.run_id).set(model_to_document(ref))
        return ref

    def get_evaluation_ref(
        self, *, tenant_id: str, run_id: str
    ) -> DatasetEvaluationRef | None:
        snap = self._evaluation_ref_doc(tenant_id, run_id).get()
        if not snap.exists:
            return None
        ref = document_to_model(DatasetEvaluationRef, snap.to_dict())
        if ref.tenant_id != tenant_id:
            return None
        return ref

    def delete_document_tree_for_qualification(self, tenant_id: str) -> list[str]:
        """Delete a synthetic qualification tenant subtree. Not a product API."""
        deleted: list[str] = []
        tenant_ref = self._tenant_ref(tenant_id)
        for collection in (
            COLLECTION_MEMBERSHIPS,
            COLLECTION_ENTITLEMENTS,
            COLLECTION_BILLING_CUSTOMERS,
            COLLECTION_BILLING_SUBSCRIPTIONS,
            COLLECTION_EVALUATION_REFS,
        ):
            for snap in tenant_ref.collection(collection).stream():
                snap.reference.delete()
                deleted.append(snap.reference.path)
        for ws in tenant_ref.collection(COLLECTION_WORKSPACES).stream():
            for ds in ws.reference.collection(COLLECTION_DATASETS).stream():
                ds.reference.delete()
                deleted.append(ds.reference.path)
            ws.reference.delete()
            deleted.append(ws.reference.path)
        tenant_ref.delete()
        deleted.append(tenant_ref.path)
        return deleted
