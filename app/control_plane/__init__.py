"""Mission 2 operational control plane.

Firestore (and the in-memory twin) store tenant, project, Dataset, entitlement,
and billing projection state. GCS and BigQuery retain artifact and ledger roles.
Persistence models here are server-internal — not REQ-001 public frontend contracts.
"""

from __future__ import annotations

from app.control_plane.entitlements import (
    PLAN_MAX_ACTIVE_PROJECTS,
    PlanId,
    default_planner_entitlement,
    project_subscription_to_entitlement,
)
from app.control_plane.firestore_repo import FirestoreControlPlaneRepository
from app.control_plane.ids import (
    new_dataset_id,
    new_entitlement_snapshot_id,
    new_tenant_id,
    new_workspace_id,
)
from app.control_plane.memory import InMemoryControlPlaneRepository
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
    WebhookClaimStatus,
    Workspace,
)
from app.control_plane.repository import ControlPlaneRepository

__all__ = [
    "ControlPlaneRepository",
    "Dataset",
    "DatasetEvaluationRef",
    "EntitlementSnapshot",
    "IdentityProviderOrganizationMapping",
    "FirestoreControlPlaneRepository",
    "InMemoryControlPlaneRepository",
    "MembershipProjection",
    "PLAN_MAX_ACTIVE_PROJECTS",
    "PlanId",
    "ProcessedWebhookEvent",
    "StripeCustomerMapping",
    "SubscriptionProjection",
    "Tenant",
    "WebhookClaimResult",
    "WebhookClaimStatus",
    "Workspace",
    "default_planner_entitlement",
    "new_dataset_id",
    "new_entitlement_snapshot_id",
    "new_tenant_id",
    "new_workspace_id",
    "project_subscription_to_entitlement",
]
