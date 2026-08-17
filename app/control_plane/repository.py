"""ControlPlaneRepository protocol — injectable persistence for prem3-api.

Business/service code must not import Firestore document operations directly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.control_plane.models import (
    Dataset,
    DatasetEvaluationRef,
    EntitlementSnapshot,
    IdentityProviderOrganizationMapping,
    MembershipProjection,
    ProcessedWebhookEvent,
    StripeCustomerMapping,
    SubscriptionProjection,
    Tenant,
    WebhookClaimResult,
    WebhookProvider,
    Workspace,
)


@runtime_checkable
class ControlPlaneRepository(Protocol):
    """Authority-qualified Mission 2 operational control plane."""

    # --- Tenant ---
    def create_tenant(
        self,
        *,
        display_name: str,
        identity_mapping: IdentityProviderOrganizationMapping | None = None,
        with_planner_entitlement: bool = True,
    ) -> Tenant: ...

    def get_tenant(self, tenant_id: str) -> Tenant | None: ...

    def set_tenant_status(self, *, tenant_id: str, status: str) -> Tenant: ...

    # --- Identity ---
    def put_identity_organization_mapping(
        self, mapping: IdentityProviderOrganizationMapping
    ) -> IdentityProviderOrganizationMapping: ...

    def get_tenant_id_for_provider_org(
        self, *, provider: str, provider_organization_id: str
    ) -> str | None: ...

    def get_identity_organization_mapping(
        self, *, provider: str, provider_organization_id: str
    ) -> IdentityProviderOrganizationMapping | None: ...

    def upsert_membership_projection(
        self, membership: MembershipProjection
    ) -> MembershipProjection: ...

    def get_membership_projection(
        self,
        *,
        tenant_id: str,
        provider: str,
        provider_user_id: str,
    ) -> MembershipProjection | None: ...

    # --- Workspace / MMM Project ---
    def list_workspaces_for_tenant(self, tenant_id: str) -> list[Workspace]: ...

    def get_workspace_for_tenant(
        self, *, tenant_id: str, workspace_id: str
    ) -> Workspace | None: ...

    def create_workspace_with_capacity(
        self, *, tenant_id: str, name: str, workspace_id: str | None = None
    ) -> Workspace: ...

    # --- Dataset ---
    def list_datasets_for_workspace(
        self, *, tenant_id: str, workspace_id: str
    ) -> list[Dataset]: ...

    def get_dataset_for_workspace(
        self, *, tenant_id: str, workspace_id: str, dataset_id: str
    ) -> Dataset | None: ...

    def create_dataset(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        name: str,
        dataset_id: str | None = None,
    ) -> Dataset: ...

    # --- Entitlement ---
    def put_entitlement_snapshot(
        self, snapshot: EntitlementSnapshot, *, make_current: bool = True
    ) -> EntitlementSnapshot: ...

    def get_entitlement_snapshot(
        self, *, tenant_id: str, snapshot_id: str
    ) -> EntitlementSnapshot | None: ...

    def get_current_entitlement(self, tenant_id: str) -> EntitlementSnapshot: ...

    # --- Billing ---
    def put_stripe_customer_mapping(
        self, mapping: StripeCustomerMapping
    ) -> StripeCustomerMapping: ...

    def get_stripe_customer_mapping(
        self, tenant_id: str
    ) -> StripeCustomerMapping | None: ...

    def put_subscription_projection(
        self, projection: SubscriptionProjection
    ) -> SubscriptionProjection: ...

    def get_subscription_projection(
        self, tenant_id: str
    ) -> SubscriptionProjection | None: ...

    # --- Webhook idempotency ---
    def claim_webhook_event(
        self,
        *,
        provider: WebhookProvider | str,
        provider_event_id: str,
        event_type: str,
    ) -> WebhookClaimResult: ...

    def mark_webhook_event_processed(
        self,
        *,
        provider: WebhookProvider | str,
        provider_event_id: str,
        result: str | None = None,
    ) -> ProcessedWebhookEvent: ...

    def mark_webhook_event_failed(
        self,
        *,
        provider: WebhookProvider | str,
        provider_event_id: str,
        result: str | None = None,
    ) -> ProcessedWebhookEvent: ...

    def get_webhook_event(
        self, *, provider: WebhookProvider | str, provider_event_id: str
    ) -> ProcessedWebhookEvent | None: ...

    # --- Evaluation linkage seam ---
    def put_evaluation_ref(self, ref: DatasetEvaluationRef) -> DatasetEvaluationRef: ...

    def get_evaluation_ref(
        self, *, tenant_id: str, run_id: str
    ) -> DatasetEvaluationRef | None: ...
