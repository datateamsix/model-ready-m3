"""Typed PreM3 Import Contract v1 and ImportReadinessReceipt."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.identifiers import validate_resource_identifier
from app.core.source_inventory import CanonicalRole
from app.governance.codes import (
    CheckSeverity,
    GovernanceCheckCode,
    ImportReadinessStatus,
    SourceType,
)
from app.governance.fingerprint import sha256_canonical


class GovernanceCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: GovernanceCheckCode
    severity: CheckSeverity
    passed: bool
    message: str
    evidence: dict[str, str] = Field(default_factory=dict)


class ImportSourceObject(BaseModel):
    """Provider-neutral selected source object. No credentials."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    object_id: str
    provider: str
    role: CanonicalRole
    logical_name: str
    source_identity: str
    version_identity: str
    object_type: str
    format: str | None = None
    schema_fingerprint: str | None = None
    size_bytes: int | None = None
    row_estimate: int | None = None
    source_metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("object_id")
    @classmethod
    def _object_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="object_id")


class RoleAssignment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    object_id: str
    role: CanonicalRole
    provider: str


class PreM3ImportContractV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: str
    tenant_id: str
    workspace_id: str
    dataset_id: str
    source_type: SourceType
    source_binding_id: str | None = None
    objects: list[ImportSourceObject]
    role_assignments: list[RoleAssignment]
    created_at: datetime
    verified_at: datetime | None = None
    status: ImportReadinessStatus
    manifest_fingerprint: str

    @field_validator("tenant_id")
    @classmethod
    def _tenant_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="tenant_id")

    @field_validator("workspace_id")
    @classmethod
    def _workspace_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="workspace_id")

    @field_validator("dataset_id")
    @classmethod
    def _dataset_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="dataset_id")

    def semantic_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "dataset_id": self.dataset_id,
            "source_type": self.source_type.value,
            "source_binding_id": self.source_binding_id,
            "objects": [
                {
                    "object_id": item.object_id,
                    "provider": item.provider,
                    "role": item.role.value,
                    "source_identity": item.source_identity,
                    "version_identity": item.version_identity,
                    "object_type": item.object_type,
                    "format": item.format,
                    "schema_fingerprint": item.schema_fingerprint,
                }
                for item in sorted(self.objects, key=lambda row: row.object_id)
            ],
            "role_assignments": [
                {
                    "object_id": item.object_id,
                    "role": item.role.value,
                    "provider": item.provider,
                }
                for item in sorted(
                    self.role_assignments, key=lambda row: (row.object_id, row.role.value)
                )
            ],
        }

    def compute_fingerprint(self) -> str:
        return sha256_canonical(self.semantic_payload())


class ImportReadinessReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    receipt_id: str
    contract_version: str
    tenant_id: str
    workspace_id: str
    dataset_id: str
    source_type: SourceType
    status: ImportReadinessStatus
    check_results: list[GovernanceCheckResult]
    error_count: int
    attention_count: int
    manifest_fingerprint: str
    verified_at: datetime
    superseded: bool = False

    @field_validator("receipt_id")
    @classmethod
    def _receipt_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="receipt_id")

    @property
    def is_current_import_ready(self) -> bool:
        return self.status is ImportReadinessStatus.IMPORT_READY and not self.superseded
