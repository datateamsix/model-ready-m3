"""Service-layer entitlement helpers. Tenant comes from TenantContext only."""

from __future__ import annotations

from app.control_plane.entitlements import allows_paid_capacity_mutation
from app.control_plane.models import EntitlementSnapshot, Feature
from app.control_plane.repository import ControlPlaneRepository
from app.core.errors import EntitlementUnavailableError
from app.core.tenancy import require_tenant
from app.service.errors import entitlement_denied, entitlement_unavailable


def resolve_current_entitlement(repo: ControlPlaneRepository) -> EntitlementSnapshot:
    tenant = require_tenant()
    try:
        return repo.get_current_entitlement(tenant.tenant_id)
    except EntitlementUnavailableError as exc:
        raise entitlement_unavailable() from exc


def require_feature(repo: ControlPlaneRepository, feature: Feature) -> EntitlementSnapshot:
    snapshot = resolve_current_entitlement(repo)
    if feature not in snapshot.features:
        raise entitlement_denied()
    return snapshot


def remaining_projects(snapshot: EntitlementSnapshot, *, active_projects: int) -> int:
    remaining = snapshot.max_active_projects - active_projects
    return remaining if remaining > 0 else 0


def require_paid_capacity_mutation(snapshot: EntitlementSnapshot) -> EntitlementSnapshot:
    if not allows_paid_capacity_mutation(snapshot.status):
        raise entitlement_denied()
    return snapshot
