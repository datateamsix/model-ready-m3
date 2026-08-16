"""Typed contracts shared by PreM3 agents, tools, UI, storage, and tests."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.core.state import RunStage


def utc_now() -> datetime:
    return datetime.now(UTC)


class Severity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class RemediationClass(StrEnum):
    AUTO_SAFE = "AUTO_SAFE"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BLOCKED = "BLOCKED"


class ActionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class IssueStatus(StrEnum):
    OPEN = "OPEN"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"


class RunStatusEvent(BaseModel):
    run_id: str
    stage: RunStage
    status: str
    message: str
    timestamp: datetime = Field(default_factory=utc_now)
    progress: float = Field(ge=0.0, le=1.0)


class Issue(BaseModel):
    issue_id: str
    rule_id: str
    severity: Severity
    title: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    remediation_class: RemediationClass
    proposed_action: dict[str, Any] = Field(default_factory=dict)
    status: IssueStatus = IssueStatus.OPEN
    resolution_action_ids: list[str] = Field(default_factory=list)
    resolved_at: datetime | None = None
    resolution_evidence: dict[str, Any] = Field(default_factory=dict)


class Transformation(BaseModel):
    action_id: str
    tool: str
    source_fields: list[str] = Field(default_factory=list)
    target_fields: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str
    lesson_ids: list[str] = Field(default_factory=list)
    status: ActionStatus = ActionStatus.PROPOSED


class SourceArtifactEvidence(BaseModel):
    role: str
    uri: str
    sha256: str


class TransformationEvidence(BaseModel):
    action_id: str
    run_id: str
    rule_id: str
    tool: str
    source_uri: str
    output_uri: str
    source_sha256: str
    output_sha256: str
    sources: list[SourceArtifactEvidence] = Field(default_factory=list)
    input_rows: int
    output_rows: int
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str
    status: str = "APPLIED"
    timestamp: datetime = Field(default_factory=utc_now)


class ReadinessCheck(BaseModel):
    rule_id: str
    passed: bool
    evidence: dict[str, Any] = Field(default_factory=dict)


class ReadinessReceipt(BaseModel):
    run_id: str
    status: str
    blocking_checks_passed: bool
    checks: list[ReadinessCheck] = Field(default_factory=list)
    artifact_uri: str | None = None


class ParityCheck(BaseModel):
    name: str
    passed: bool
    evidence: dict[str, Any] = Field(default_factory=dict)


class BigQueryPublishReceipt(BaseModel):
    run_id: str
    status: str
    project_id: str
    dataset_id: str
    table_id: str
    view_id: str | None = None
    row_count: int = Field(ge=0)
    schema_fingerprint: str
    artifact_fingerprint: str
    published_fingerprint: str = ""
    parity_status: str
    meridian_contract_uri: str = ""
    provenance_uri: str = ""
    parity_checks: list[ParityCheck] = Field(default_factory=list)
    physical_schema_fingerprint: str = ""
    partition_field: str | None = None
    clustering_fields: list[str] = Field(default_factory=list)
    consumption_view: str = ""
    model_ready_manifest_uri: str = ""


class DurableRunState(BaseModel):
    """Operational cloud run metadata. Never stores dataframes or model reasoning."""

    run_id: str
    organization_id: str
    workspace_id: str
    package_uri: str
    package_fingerprint: str
    stage: RunStage
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    detected_issue_ids: list[str] = Field(default_factory=list)
    resolved_issue_ids: list[str] = Field(default_factory=list)
    open_issue_ids: list[str] = Field(default_factory=list)
    artifact_prefix: str
    model_artifact_uri: str | None = None
    readiness_uri: str | None = None
    provenance_uri: str | None = None
    manifest_uri: str | None = None
    publish_receipt_uri: str | None = None
    meridian_contract_uri: str | None = None
    run_summary_uri: str | None = None
    bigquery_table: str | None = None
    model_ready_manifest_uri: str | None = None
    model_consumption_view: str | None = None
    model_consumption_receipt_uri: str | None = None
    model_ready_confirmation_receipt_uri: str | None = None
    meridian_eda_receipt_uri: str | None = None
    meridian_eda_report_uri: str | None = None
    meridian_eda_config_uri: str | None = None
    meridian_user_feedback_uri: str | None = None
    m3_eda_analysis_uri: str | None = None
    pre_modeling_handoff_uri: str | None = None
    physical_schema_fingerprint: str | None = None
    status: str
    google_ready_relpath: str | None = None
    meta_ready_relpath: str | None = None
    source_objects: list[dict[str, Any]] = Field(default_factory=list)
    scratch_dir: str | None = None
    input_file_count: int = 0


class LearningReceiptType(StrEnum):
    EXPERIENCE_LEARNED = "EXPERIENCE_LEARNED"
    EXPERIENCE_APPLIED = "EXPERIENCE_APPLIED"


class LearningReceipt(BaseModel):
    receipt_id: str
    receipt_type: LearningReceiptType
    run_id: str
    lesson_id: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    risk: str
    measured_change: dict[str, Any] = Field(default_factory=dict)
    validation_status: str
