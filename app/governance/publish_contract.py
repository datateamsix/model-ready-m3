"""Typed PreM3 Publish Contract v1 and PublishReadinessReceipt."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.identifiers import validate_resource_identifier
from app.governance.codes import PublishReadinessStatus
from app.governance.fingerprint import sha256_canonical
from app.governance.import_contract import GovernanceCheckResult


class PublishDestinationKind(StrEnum):
    GOOGLE_DRIVE = "GOOGLE_DRIVE"
    BIGQUERY = "BIGQUERY"


class PublishDestination(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: PublishDestinationKind
    binding_id: str
    target_identity: str
    location: str | None = None
    write_verified: bool = False


class PreM3PublishContractV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: str
    tenant_id: str
    workspace_id: str
    dataset_id: str
    run_id: str
    model_ready_fingerprint: str | None
    model_ready_verified: bool
    destinations: list[PublishDestination]
    required_artifacts: list[str]
    created_at: datetime
    status: PublishReadinessStatus
    contract_fingerprint: str
    overwrite_policy: str = "versioned_run_id"

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

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="run_id")

    def semantic_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "dataset_id": self.dataset_id,
            "run_id": self.run_id,
            "model_ready_fingerprint": self.model_ready_fingerprint,
            "model_ready_verified": self.model_ready_verified,
            "destinations": [
                {
                    "kind": item.kind.value,
                    "binding_id": item.binding_id,
                    "target_identity": item.target_identity,
                    "location": item.location,
                    "write_verified": item.write_verified,
                }
                for item in sorted(self.destinations, key=lambda row: row.kind.value)
            ],
            "required_artifacts": sorted(self.required_artifacts),
            "overwrite_policy": self.overwrite_policy,
        }

    def compute_fingerprint(self) -> str:
        return sha256_canonical(self.semantic_payload())


class PublishReadinessReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    receipt_id: str
    contract_version: str
    tenant_id: str
    workspace_id: str
    dataset_id: str
    run_id: str
    status: PublishReadinessStatus
    destination_summaries: list[str] = Field(default_factory=list)
    check_results: list[GovernanceCheckResult]
    model_ready_fingerprint: str | None
    contract_fingerprint: str
    verified_at: datetime
    published: bool = False

    @field_validator("receipt_id")
    @classmethod
    def _receipt_id(cls, value: str) -> str:
        return validate_resource_identifier(value, field="receipt_id")
