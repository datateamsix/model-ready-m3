"""Deterministic plan defaults and subscription → entitlement projection seam.

No Stripe Price IDs or dollar amounts. Future plan catalog/HTTP is REQ-012.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from app.control_plane.ids import new_entitlement_snapshot_id
from app.control_plane.models import (
    EntitlementSnapshot,
    EntitlementSource,
    EntitlementStatus,
    Feature,
    SubscriptionProjection,
)

PLANNER_FEATURES: frozenset[Feature] = frozenset()

PAID_FEATURES: frozenset[Feature] = frozenset(
    {
        Feature.PROJECT_CREATE,
        Feature.PLANNING_RUN,
        Feature.PLAN_COMPILE,
        Feature.PLAN_EXPORT,
        Feature.DATASET_CREATE,
        Feature.DATA_UPLOAD,
        Feature.DATASET_ASSESSMENT,
        Feature.SAFE_REMEDIATION,
        Feature.BIGQUERY_PUBLISH,
        Feature.OFFICIAL_MERIDIAN_EDA,
        Feature.MERIDIAN_INTEGRATION,
        Feature.REGISTRY_RESEARCH,
        Feature.TEAM_SEATS,
    }
)


class PlanId(StrEnum):
    PLANNER = "planner"
    PROJECT = "project"
    PORTFOLIO = "portfolio"
    ENTERPRISE = "enterprise"


PLAN_MAX_ACTIVE_PROJECTS: dict[str, int] = {
    PlanId.PLANNER: 0,
    PlanId.PROJECT: 1,
    PlanId.PORTFOLIO: 10,
    PlanId.ENTERPRISE: 50,
}


def _features_for_plan(plan_id: str) -> frozenset[Feature]:
    if plan_id == PlanId.PLANNER:
        return PLANNER_FEATURES
    if plan_id in {PlanId.PROJECT, PlanId.PORTFOLIO, PlanId.ENTERPRISE}:
        return PAID_FEATURES
    raise ValueError(f"Unknown plan_id: {plan_id}")


def default_planner_entitlement(
    *,
    tenant_id: str,
    now: datetime | None = None,
    snapshot_id: str | None = None,
) -> EntitlementSnapshot:
    """Only valid default entitlement: Planner with max_active_projects = 0."""
    stamp = now or datetime.now(UTC)
    return EntitlementSnapshot(
        snapshot_id=snapshot_id or new_entitlement_snapshot_id(),
        tenant_id=tenant_id,
        plan_id=PlanId.PLANNER,
        features=PLANNER_FEATURES,
        limits={"max_active_projects": PLAN_MAX_ACTIVE_PROJECTS[PlanId.PLANNER]},
        status=EntitlementStatus.ACTIVE,
        valid_until=None,
        source=EntitlementSource.DEFAULT,
        created_at=stamp,
    )


def entitlement_for_plan(
    *,
    tenant_id: str,
    plan_id: str,
    source: EntitlementSource,
    status: EntitlementStatus = EntitlementStatus.ACTIVE,
    valid_until: datetime | None = None,
    now: datetime | None = None,
    snapshot_id: str | None = None,
) -> EntitlementSnapshot:
    if plan_id not in PLAN_MAX_ACTIVE_PROJECTS:
        raise ValueError(f"Unknown plan_id: {plan_id}")
    stamp = now or datetime.now(UTC)
    return EntitlementSnapshot(
        snapshot_id=snapshot_id or new_entitlement_snapshot_id(),
        tenant_id=tenant_id,
        plan_id=plan_id,
        features=_features_for_plan(plan_id),
        limits={"max_active_projects": PLAN_MAX_ACTIVE_PROJECTS[plan_id]},
        status=status,
        valid_until=valid_until,
        source=source,
        created_at=stamp,
    )


def project_subscription_to_entitlement(
    subscription: SubscriptionProjection,
    *,
    now: datetime | None = None,
) -> EntitlementSnapshot:
    """Pure seam: SubscriptionProjection → new immutable EntitlementSnapshot.

    Business operations consume the entitlement, never raw Stripe objects.
    """
    status_map = {
        "active": EntitlementStatus.ACTIVE,
        "trialing": EntitlementStatus.TRIALING,
        "past_due": EntitlementStatus.PAST_DUE,
        "canceled": EntitlementStatus.CANCELED,
        "incomplete": EntitlementStatus.INCOMPLETE,
    }
    mapped = status_map.get(subscription.status.lower(), EntitlementStatus.INCOMPLETE)
    return entitlement_for_plan(
        tenant_id=subscription.tenant_id,
        plan_id=subscription.plan_id,
        source=EntitlementSource.BILLING_PROVIDER,
        status=mapped,
        valid_until=subscription.current_period_end,
        now=now,
    )
