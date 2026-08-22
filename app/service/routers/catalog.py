from __future__ import annotations

from fastapi import APIRouter, Request

from app.service.catalog import build_plan_catalog
from app.service.models import PlanCatalogResponse

router = APIRouter(prefix="/v1/catalog", tags=["catalog"])


@router.get("/plans", operation_id="getPlanCatalog", response_model=PlanCatalogResponse)
def get_plan_catalog(request: Request) -> PlanCatalogResponse:
    catalog = getattr(request.app.state, "plan_catalog", None)
    if catalog is not None:
        return catalog
    return build_plan_catalog(checkout_eligible=False)
