"""Canonical PreM3 Model-Ready Manifest.

Machine filename remains ``model_ready_manifest.json``. Class name
``ModelReadyManifest`` is a stable contract identifier.

Status is VALIDATED_FOR_PUBLICATION. The manifest never establishes MODEL_READY.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.contracts import Issue, utc_now
from app.core.errors import ValidationBlockedError
from app.core.model_intent import ModelIntent, model_ready_columns
from app.core.state import RunStage
from app.tools.fingerprints import content_fingerprint
from app.tools.meridian_contract import MeridianInputContract
from app.tools.provenance import frame_source_roles
from app.tools.schema_compiler import (
    ModelConsumptionSchema,
    compile_model_consumption_schema,
    schema_as_records,
)

MANIFEST_VERSION = "1.0"
MANIFEST_STATUS = "VALIDATED_FOR_PUBLICATION"


class ManifestIdentity(BaseModel):
    manifest_version: str = MANIFEST_VERSION
    organization_id: str
    workspace_id: str
    run_id: str
    target_model: str
    model_scope: str
    package_uri: str
    package_fingerprint: str
    created_at: datetime = Field(default_factory=utc_now)
    canonical_artifact_uri: str
    canonical_artifact_fingerprint: str
    readiness_receipt_uri: str | None = None
    transformation_manifest_uri: str | None = None
    provenance_uri: str | None = None
    meridian_contract_uri: str | None = None


class ManifestSource(BaseModel):
    role: str
    uri: str
    sha256: str
    original_grain: str | None = None
    field_mappings: dict[str, str] = Field(default_factory=dict)


class ManifestIssue(BaseModel):
    issue_id: str
    rule_id: str
    title: str
    remediation_class: str
    original_status: str = "OPEN"
    final_status: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    resolution_action_ids: list[str] = Field(default_factory=list)
    resolution_evidence: dict[str, Any] = Field(default_factory=dict)


class ManifestTransform(BaseModel):
    action_id: str
    tool: str
    rule_id: str
    source_uri: str = ""
    output_uri: str = ""
    source_sha256: str = ""
    output_sha256: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_rows: int = 0
    output_rows: int = 0
    status: str = "APPLIED"
    reason: str = ""


class ManifestOutputContract(BaseModel):
    canonical_grain: list[str] = Field(default_factory=lambda: ["time", "geo"])
    row_count: int
    column_count: int
    expected_columns: list[str]
    expected_logical_schema: list[tuple[str, str]] = Field(default_factory=list)
    expected_physical_schema: list[dict[str, Any]] = Field(default_factory=list)
    expected_artifact_fingerprint: str
    null_policy: str = "no_unsupported_nulls"
    key_policy: str = "unique_time_geo"
    date_grain: str = "weekly"
    sorted_key_definition: list[str] = Field(default_factory=lambda: ["time", "geo"])
    partition_field: str = "time"
    clustering_fields: list[str] = Field(default_factory=lambda: ["geo"])


class ManifestSemantics(BaseModel):
    time: str = "time"
    geo: str | None = "geo"
    kpi: str
    revenue: str
    revenue_per_kpi: str = "revenue_per_kpi"
    population: str | None = "population"
    paid_media: list[dict[str, str]] = Field(default_factory=list)
    organic_media: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)


class ModelReadyManifest(BaseModel):
    identity: ManifestIdentity
    status: str = MANIFEST_STATUS
    sources: list[ManifestSource] = Field(default_factory=list)
    issues: list[ManifestIssue] = Field(default_factory=list)
    transformations: list[ManifestTransform] = Field(default_factory=list)
    output: ManifestOutputContract
    semantics: ManifestSemantics
    schema_fingerprint: str = ""
    stage_at_compile: str = RunStage.VALIDATING.value

    @property
    def run_id(self) -> str:
        return self.identity.run_id


def compile_model_ready_manifest(
    *,
    run_id: str,
    organization_id: str,
    workspace_id: str,
    package_uri: str,
    package_fingerprint: str,
    intent: ModelIntent,
    frame,
    issues: list[Issue],
    provenance: dict[str, Any],
    readiness: dict[str, Any],
    meridian_contract: MeridianInputContract | None,
    canonical_artifact_uri: str,
    canonical_artifact_fingerprint: str | None = None,
    readiness_receipt_uri: str | None = None,
    transformation_manifest_uri: str | None = None,
    provenance_uri: str | None = None,
    meridian_contract_uri: str | None = None,
    schema: ModelConsumptionSchema | None = None,
) -> ModelReadyManifest:
    if readiness.get("status") != "PASS":
        raise ValidationBlockedError("ModelReady Manifest requires a PASS readiness receipt.")
    fingerprint = canonical_artifact_fingerprint or content_fingerprint(
        frame, columns=model_ready_columns(intent), key_columns=["time", "geo"]
    )
    compiled_schema = schema or compile_model_consumption_schema(
        intent=intent,
        meridian_contract=meridian_contract,
        columns=list(frame.columns),
        table_description=(
            f"ModelReady Meridian model-input artifact for run {run_id}."
        ),
    )
    records = provenance.get("records") or provenance.get("transforms") or []
    sources = _sources_from_provenance(records)
    if not sources:
        raise ValidationBlockedError("ModelReady Manifest requires provenance source evidence.")
    roles = {item.role for item in sources}
    missing_roles = sorted(set(frame_source_roles(intent)) - roles)
    if missing_roles:
        raise ValidationBlockedError(
            f"ModelReady Manifest missing canonical source roles: {missing_roles}"
        )
    output = ManifestOutputContract(
        row_count=int(len(frame)),
        column_count=int(len(frame.columns)),
        expected_columns=list(model_ready_columns(intent)),
        expected_logical_schema=[
            (field.name, field.logical_semantic) for field in compiled_schema.fields
        ],
        expected_physical_schema=schema_as_records(compiled_schema),
        expected_artifact_fingerprint=fingerprint,
        date_grain=intent.canonical_time_grain.value,
        partition_field=compiled_schema.partition_field,
        clustering_fields=list(compiled_schema.clustering_fields),
    )
    return ModelReadyManifest(
        identity=ManifestIdentity(
            organization_id=organization_id,
            workspace_id=workspace_id,
            run_id=run_id,
            target_model=intent.target.value,
            model_scope=intent.model_scope.value,
            package_uri=package_uri,
            package_fingerprint=package_fingerprint,
            canonical_artifact_uri=canonical_artifact_uri,
            canonical_artifact_fingerprint=fingerprint,
            readiness_receipt_uri=readiness_receipt_uri,
            transformation_manifest_uri=transformation_manifest_uri,
            provenance_uri=provenance_uri,
            meridian_contract_uri=meridian_contract_uri,
        ),
        status=MANIFEST_STATUS,
        sources=sources,
        issues=[_issue_record(issue) for issue in issues],
        transformations=[_transform_record(item) for item in records],
        output=output,
        semantics=_semantics(intent),
        schema_fingerprint=compiled_schema.physical_schema_fingerprint(),
        stage_at_compile=RunStage.VALIDATING.value,
    )


def _sources_from_provenance(records: list[dict[str, Any]]) -> list[ManifestSource]:
    frame = next((item for item in records if item.get("tool") == "build_model_ready_frame"), None)
    if frame is None:
        return []
    sources: list[ManifestSource] = []
    for item in frame.get("sources") or []:
        sources.append(
            ManifestSource(
                role=str(item.get("role") or "source"),
                uri=str(item.get("uri") or ""),
                sha256=str(item.get("sha256") or ""),
            )
        )
    return sources


def _issue_record(issue: Issue) -> ManifestIssue:
    return ManifestIssue(
        issue_id=issue.issue_id,
        rule_id=issue.rule_id,
        title=issue.title,
        remediation_class=issue.remediation_class.value,
        original_status="OPEN",
        final_status=issue.status.value,
        evidence=dict(issue.evidence),
        resolution_action_ids=list(issue.resolution_action_ids),
        resolution_evidence=dict(issue.resolution_evidence),
    )


def _transform_record(item: dict[str, Any]) -> ManifestTransform:
    return ManifestTransform(
        action_id=str(item.get("action_id") or ""),
        tool=str(item.get("tool") or ""),
        rule_id=str(item.get("rule_id") or ""),
        source_uri=str(item.get("source_uri") or ""),
        output_uri=str(item.get("output_uri") or ""),
        source_sha256=str(item.get("source_sha256") or ""),
        output_sha256=str(item.get("output_sha256") or ""),
        parameters=dict(item.get("parameters") or {}),
        input_rows=int(item.get("input_rows") or 0),
        output_rows=int(item.get("output_rows") or 0),
        status=str(item.get("status") or "APPLIED"),
        reason=str(item.get("reason") or ""),
    )


def _semantics(intent: ModelIntent) -> ManifestSemantics:
    return ManifestSemantics(
        kpi=intent.kpi.canonical_field or "kpi_orders",
        revenue=intent.revenue.canonical_field or "kpi_revenue",
        population="population" if intent.population else None,
        paid_media=[
            {
                "channel": channel.channel,
                "impressions_field": channel.impressions_column,
                "spend_field": channel.spend_column,
            }
            for channel in intent.paid_media
        ],
        organic_media=[
            item.canonical_field or item.field for item in intent.organic_media if item.field
        ],
        controls=list(intent.controls),
    )
