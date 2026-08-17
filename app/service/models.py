"""Presentation-safe prem3-api contracts. Not Firestore persistence models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HealthResponse(ApiModel):
    status: str


class ReadyProviderStatus(ApiModel):
    control_plane: str
    auth_provider: str
    billing_provider: str


class ReadyResponse(ApiModel):
    status: str
    dependencies: ReadyProviderStatus


class MeUser(ApiModel):
    user_id: str


class MeOrganization(ApiModel):
    tenant_id: str
    display_name: str


class MePlan(ApiModel):
    plan_id: str
    status: str
    feature_summary: list[str]


class MeProjectCapacity(ApiModel):
    active_projects: int
    max_active_projects: int
    remaining_projects: int


class MeResponse(ApiModel):
    user: MeUser
    organization: MeOrganization
    plan: MePlan
    project_capacity: MeProjectCapacity


class PlanCatalogEntry(ApiModel):
    plan_id: str
    display_name: str
    description: str
    max_active_projects: int
    feature_summary: list[str]
    billing_interval: str
    display_price: str | None = None
    amount: int | None = None
    currency: str | None = None
    checkout_eligible: bool
    unlimited_reevaluations: bool


class PlanCatalogResponse(ApiModel):
    plans: list[PlanCatalogEntry]


class CreateWorkspaceRequest(ApiModel):
    name: str = Field(min_length=1, max_length=120)


class WorkspaceResponse(ApiModel):
    workspace_id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class WorkspaceListResponse(ApiModel):
    items: list[WorkspaceResponse]
    next_cursor: str | None = None


class CreateDatasetRequest(ApiModel):
    name: str = Field(min_length=1, max_length=120)


class DatasetResponse(ApiModel):
    dataset_id: str
    workspace_id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(ApiModel):
    items: list[DatasetResponse]
    next_cursor: str | None = None


class CheckoutSessionRequest(ApiModel):
    plan_id: str
    return_path: str | None = None


class PortalSessionRequest(ApiModel):
    return_path: str | None = None


class BillingSessionResponse(ApiModel):
    url: str
    expires_at: datetime | None = None
