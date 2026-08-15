"""Typed contracts shared by M3 agents, tools, UI, storage, and tests."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.core.state import RunStage


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    status: str = "OPEN"


class Transformation(BaseModel):
    action_id: str
    tool: str
    source_fields: list[str] = Field(default_factory=list)
    target_fields: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str
    lesson_ids: list[str] = Field(default_factory=list)
    status: ActionStatus = ActionStatus.PROPOSED


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
    parity_status: str
    meridian_contract_uri: str
    provenance_uri: str


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
