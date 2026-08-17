"""Backend-owned public plan catalog. No Stripe Price IDs. No invented prices."""

from __future__ import annotations

from app.control_plane.entitlements import PLAN_MAX_ACTIVE_PROJECTS, PlanId
from app.service.models import PlanCatalogEntry, PlanCatalogResponse

_PLAN_COPY: dict[str, tuple[str, str, list[str]]] = {
    PlanId.PLANNER: (
        "Planner",
        "Public deterministic PreM3 Planner. No paid MMM Project slot.",
        ["Deterministic public Planner"],
    ),
    PlanId.PROJECT: (
        "Project",
        "One paid MMM Project with unlimited commercial re-evaluations.",
        ["One MMM Project", "Unlimited re-evaluations", "Meridian Integration"],
    ),
    PlanId.PORTFOLIO: (
        "Portfolio",
        "Up to ten paid MMM Projects with unlimited commercial re-evaluations.",
        ["Up to 10 MMM Projects", "Unlimited re-evaluations", "Meridian Integration"],
    ),
    PlanId.ENTERPRISE: (
        "Enterprise",
        "Up to fifty paid MMM Projects with unlimited commercial re-evaluations.",
        ["Up to 50 MMM Projects", "Unlimited re-evaluations", "Meridian Integration"],
    ),
}


def build_plan_catalog(*, checkout_eligible: bool = False) -> PlanCatalogResponse:
    plans: list[PlanCatalogEntry] = []
    for plan_id in (PlanId.PLANNER, PlanId.PROJECT, PlanId.PORTFOLIO, PlanId.ENTERPRISE):
        display_name, description, features = _PLAN_COPY[plan_id]
        paid = plan_id != PlanId.PLANNER
        plans.append(
            PlanCatalogEntry(
                plan_id=plan_id,
                display_name=display_name,
                description=description,
                max_active_projects=PLAN_MAX_ACTIVE_PROJECTS[plan_id],
                feature_summary=features,
                billing_interval="month",
                display_price=None,
                amount=None,
                currency=None,
                checkout_eligible=bool(checkout_eligible and paid),
                unlimited_reevaluations=paid,
            )
        )
    return PlanCatalogResponse(plans=plans)
