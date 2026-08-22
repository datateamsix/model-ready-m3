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


class WebhookAckResponse(ApiModel):
    status: str
    result: str


class UploadFileRequest(ApiModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(gt=0)


class CreateUploadRequest(ApiModel):
    files: list[UploadFileRequest] = Field(min_length=1, max_length=20)


class UploadFileInstruction(ApiModel):
    upload_file_id: str
    filename: str
    method: str
    url: str
    required_headers: dict[str, str]
    expires_at: datetime


class UploadFileResponse(ApiModel):
    upload_file_id: str
    filename: str
    content_type: str
    declared_size_bytes: int
    actual_size_bytes: int | None = None
    status: str


class UploadResponse(ApiModel):
    upload_id: str
    dataset_id: str
    status: str
    files: list[UploadFileResponse]
    upload_instructions: list[UploadFileInstruction] = Field(default_factory=list)
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class CompleteUploadResponse(ApiModel):
    upload_id: str
    dataset_id: str
    status: str
    files: list[UploadFileResponse]
    package_fingerprint: str | None = None
    completed_at: datetime | None = None


class CreateEvaluationRequest(ApiModel):
    upload_id: str = Field(min_length=1, max_length=128)


class EvaluationResponse(ApiModel):
    run_id: str
    dataset_id: str
    upload_id: str
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    package_fingerprint: str | None = None


class EvaluationListResponse(ApiModel):
    items: list[EvaluationResponse]
    next_cursor: str | None = None


class GoogleOAuthStartRequest(ApiModel):
    capabilities: list[str] = Field(min_length=1, max_length=8)
    workspace_id: str | None = None
    dataset_id: str | None = None
    return_path: str | None = None


class GoogleOAuthStartResponse(ApiModel):
    authorization_url: str
    expires_at: datetime


class GoogleConnectionResponse(ApiModel):
    connection_id: str
    display_email: str | None = None
    status: str
    capabilities: list[str]
    created_at: datetime
    updated_at: datetime
    last_verified_at: datetime | None = None


class GoogleConnectionListResponse(ApiModel):
    items: list[GoogleConnectionResponse]


class DriveBindingSetupRequest(ApiModel):
    connection_id: str
    import_enabled: bool = True
    export_enabled: bool = True


class DriveBindingResponse(ApiModel):
    workspace_id: str
    connection_id: str
    root_folder_id: str
    root_folder_name: str
    imports_folder_id: str
    exports_folder_id: str
    reports_folder_id: str
    status: str
    import_enabled: bool
    export_enabled: bool
    updated_at: datetime
    last_verified_at: datetime | None = None


class BigQueryBindingSetupRequest(ApiModel):
    connection_id: str
    destination_project_id: str
    location: str
    source_project_ids: list[str] = Field(default_factory=list)
    source_dataset_ids: list[str] = Field(default_factory=list)
    create_if_missing: bool = False


class BigQueryBindingResponse(ApiModel):
    workspace_id: str
    connection_id: str
    source_project_ids: list[str]
    source_dataset_ids: list[str]
    destination_project_id: str
    destination_dataset_id: str
    destination_friendly_name: str
    location: str
    read_verified: bool
    write_verified: bool
    status: str
    updated_at: datetime
    last_verified_at: datetime | None = None


class BigQueryProjectListResponse(ApiModel):
    items: list[dict[str, str]]


class BigQueryDatasetListResponse(ApiModel):
    items: list[dict[str, str]]


class BigQueryTableListItem(ApiModel):
    project_id: str
    dataset_id: str
    table_id: str
    object_type: str
    location: str


class BigQueryTableListResponse(ApiModel):
    items: list[BigQueryTableListItem]


class ImportRoleAssignmentRequest(ApiModel):
    object_id: str
    role: str
    provider: str


class DatasetImportBindingRequest(ApiModel):
    source_type: str
    connection_id: str | None = None
    upload_id: str | None = None
    selected_object_ids: list[str] = Field(default_factory=list)
    role_assignments: list[ImportRoleAssignmentRequest] = Field(default_factory=list)


class DatasetImportBindingResponse(ApiModel):
    source_type: str
    connection_id: str | None = None
    upload_id: str | None = None
    selected_object_ids: list[str]
    role_assignments: list[ImportRoleAssignmentRequest]
    current_receipt_id: str | None = None
    updated_at: datetime


class GovernanceCheckResponse(ApiModel):
    code: str
    severity: str
    passed: bool
    message: str
    evidence: dict[str, str] = Field(default_factory=dict)


class ImportReadinessReceiptResponse(ApiModel):
    receipt_id: str
    contract_version: str
    tenant_id: str
    workspace_id: str
    dataset_id: str
    source_type: str
    status: str
    check_results: list[GovernanceCheckResponse]
    error_count: int
    attention_count: int
    selected_object_count: int | None = None
    role_assignment_count: int | None = None
    manifest_fingerprint: str
    verified_at: datetime
    superseded: bool = False


class PublishReadinessReceiptResponse(ApiModel):
    receipt_id: str
    contract_version: str
    tenant_id: str
    workspace_id: str
    dataset_id: str
    run_id: str
    status: str
    destination_summaries: list[str]
    check_results: list[GovernanceCheckResponse]
    model_ready_fingerprint: str | None = None
    contract_fingerprint: str
    verified_at: datetime
    published: bool = False
