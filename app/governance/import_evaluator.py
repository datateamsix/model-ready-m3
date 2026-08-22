"""Deterministic IMPORT_READY evaluator. Gemini cannot emit this state."""

from __future__ import annotations

from datetime import UTC, datetime

from app.control_plane.ids import new_receipt_id
from app.core.source_inventory import CanonicalRole
from app.governance.codes import (
    IMPORT_CONTRACT_VERSION,
    SUPPORTED_BQ_IMPORT_TYPES,
    SUPPORTED_IMPORT_FORMATS,
    BigQueryObjectType,
    CheckSeverity,
    GovernanceCheckCode,
    ImportReadinessStatus,
    SourceType,
)
from app.governance.import_contract import (
    GovernanceCheckResult,
    ImportReadinessReceipt,
    PreM3ImportContractV1,
)


def evaluate_import_readiness(contract: PreM3ImportContractV1) -> ImportReadinessReceipt:
    """Sole function allowed to return IMPORT_READY."""
    checks: list[GovernanceCheckResult] = []
    checks.extend(_connection_and_binding(contract))
    checks.extend(_objects(contract))
    checks.extend(_roles(contract))
    checks.append(
        _check(
            GovernanceCheckCode.MANIFEST_COMPLETE,
            bool(contract.objects) and bool(contract.role_assignments),
            "Import contract objects and role assignments are present.",
            "MANIFEST_COMPLETE failed: objects or role assignments missing.",
        )
    )
    fingerprint = contract.compute_fingerprint()
    errors = [item for item in checks if item.severity is CheckSeverity.ERROR]
    attentions = [item for item in checks if item.severity is CheckSeverity.ATTENTION]
    status = (
        ImportReadinessStatus.IMPORT_READY
        if not errors and contract.objects
        else ImportReadinessStatus.NOT_IMPORT_READY
    )
    now = datetime.now(UTC)
    return ImportReadinessReceipt(
        receipt_id=new_receipt_id(),
        contract_version=IMPORT_CONTRACT_VERSION,
        tenant_id=contract.tenant_id,
        workspace_id=contract.workspace_id,
        dataset_id=contract.dataset_id,
        source_type=contract.source_type,
        status=status,
        check_results=checks,
        error_count=len(errors),
        attention_count=len(attentions),
        manifest_fingerprint=fingerprint,
        verified_at=now,
        superseded=False,
    )


def _connection_and_binding(contract: PreM3ImportContractV1) -> list[GovernanceCheckResult]:
    if contract.source_type is SourceType.GCS_UPLOAD:
        bound = bool(contract.source_binding_id)
        return [
            _check(
                GovernanceCheckCode.SOURCE_BOUND,
                bound,
                "Verified GCS upload is bound.",
                "BINDING_MISSING: verified upload_id is required.",
                fail_code=GovernanceCheckCode.BINDING_MISSING,
            )
        ]
    bound = bool(contract.source_binding_id)
    return [
        _check(
            GovernanceCheckCode.CONNECTION_ACTIVE,
            bound,
            "Google connection/binding reference is present.",
            "CONNECTION_INACTIVE: connection/binding missing.",
            fail_code=GovernanceCheckCode.CONNECTION_INACTIVE,
        ),
        _check(
            GovernanceCheckCode.SOURCE_BOUND,
            bound,
            "Source binding is present.",
            "BINDING_MISSING: workspace source binding is required.",
            fail_code=GovernanceCheckCode.BINDING_MISSING,
        ),
        _check(
            GovernanceCheckCode.SOURCE_AUTHORIZED,
            bound,
            "Source is authorized through the bound connection.",
            "PERMISSION_DENIED: source is not authorized.",
            fail_code=GovernanceCheckCode.PERMISSION_DENIED,
        ),
    ]


def _objects(contract: PreM3ImportContractV1) -> list[GovernanceCheckResult]:
    results: list[GovernanceCheckResult] = []
    ids = [item.object_id for item in contract.objects]
    results.append(
        _check(
            GovernanceCheckCode.DUPLICATE_SELECTION_ABSENT,
            len(ids) == len(set(ids)) and len(ids) > 0,
            "Selected objects are unique and non-empty.",
            "Duplicate or empty object selection.",
        )
    )
    results.append(
        _check(
            GovernanceCheckCode.RESOURCE_EXISTS,
            bool(contract.objects),
            "At least one source object is selected.",
            "RESOURCE_NOT_FOUND: no selected objects.",
            fail_code=GovernanceCheckCode.RESOURCE_NOT_FOUND,
        )
    )
    for item in contract.objects:
        fmt = (item.format or "").lower().lstrip(".")
        if contract.source_type is SourceType.BIGQUERY:
            try:
                bq_type = BigQueryObjectType(item.object_type)
            except ValueError:
                bq_type = BigQueryObjectType.UNKNOWN
            supported = bq_type in SUPPORTED_BQ_IMPORT_TYPES
            results.append(
                _check(
                    GovernanceCheckCode.FORMAT_SUPPORTED,
                    supported,
                    f"{item.object_id} BigQuery type is supported.",
                    f"FORMAT_UNSUPPORTED: {item.object_type}",
                    fail_code=GovernanceCheckCode.FORMAT_UNSUPPORTED,
                    evidence={"object_id": item.object_id, "object_type": item.object_type},
                )
            )
        else:
            results.append(
                _check(
                    GovernanceCheckCode.FORMAT_SUPPORTED,
                    fmt in SUPPORTED_IMPORT_FORMATS,
                    f"{item.object_id} format is supported.",
                    f"FORMAT_UNSUPPORTED: {item.format}",
                    fail_code=GovernanceCheckCode.FORMAT_UNSUPPORTED,
                    evidence={"object_id": item.object_id, "format": item.format or ""},
                )
            )
        nonempty = (item.size_bytes or 0) > 0 or (item.row_estimate or 0) > 0
        results.append(
            _check(
                GovernanceCheckCode.OBJECT_NONEMPTY,
                nonempty,
                f"{item.object_id} is non-empty.",
                "OBJECT_EMPTY",
                fail_code=GovernanceCheckCode.OBJECT_EMPTY,
                evidence={"object_id": item.object_id},
            )
        )
        schema_ok = bool(item.schema_fingerprint) or fmt in {"csv", "parquet", "json"} or (
            contract.source_type is SourceType.BIGQUERY and bool(item.schema_fingerprint)
        )
        if contract.source_type is SourceType.BIGQUERY:
            schema_ok = bool(item.schema_fingerprint)
        results.append(
            _check(
                GovernanceCheckCode.SCHEMA_INSPECTABLE,
                schema_ok,
                f"{item.object_id} schema/metadata is inspectable.",
                "SCHEMA_UNREADABLE",
                fail_code=GovernanceCheckCode.SCHEMA_UNREADABLE,
                evidence={"object_id": item.object_id},
            )
        )
        version_ok = bool(item.version_identity.strip())
        results.append(
            _check(
                GovernanceCheckCode.VERSION_IDENTITY_AVAILABLE,
                version_ok,
                f"{item.object_id} has a provider version identity.",
                "SOURCE_VERSION_UNVERIFIABLE",
                fail_code=GovernanceCheckCode.SOURCE_VERSION_UNVERIFIABLE,
                evidence={"object_id": item.object_id},
            )
        )
        provider_ok = bool(item.provider) and item.provider not in {"unknown", "unresolved"}
        results.append(
            _check(
                GovernanceCheckCode.PROVIDER_RESOLVED,
                provider_ok,
                f"{item.object_id} provider is resolved.",
                "PROVIDER_UNRESOLVED",
                fail_code=GovernanceCheckCode.PROVIDER_UNRESOLVED,
                evidence={"object_id": item.object_id, "provider": item.provider},
            )
        )
    return results


def _roles(contract: PreM3ImportContractV1) -> list[GovernanceCheckResult]:
    assigned = {item.object_id: item.role for item in contract.role_assignments}
    object_ids = {item.object_id for item in contract.objects}
    missing = object_ids - set(assigned)
    extras = set(assigned) - object_ids
    unknown = [
        item.object_id
        for item in contract.role_assignments
        if item.role is CanonicalRole.UNKNOWN
    ]
    duplicate_roles: dict[str, list[CanonicalRole]] = {}
    for item in contract.role_assignments:
        duplicate_roles.setdefault(item.object_id, []).append(item.role)
    ambiguous = [
        object_id for object_id, roles in duplicate_roles.items() if len(set(roles)) > 1
    ]
    return [
        _check(
            GovernanceCheckCode.ROLE_ASSIGNED,
            not missing and not extras and not unknown,
            "Every selected object has an explicit canonical role.",
            "SOURCE_ROLE_MISSING",
            fail_code=GovernanceCheckCode.SOURCE_ROLE_MISSING,
            evidence={"missing": ",".join(sorted(missing | set(unknown)))},
        ),
        _check(
            GovernanceCheckCode.ROLE_MAPPING_UNAMBIGUOUS,
            not ambiguous,
            "No object is mapped to mutually exclusive roles.",
            "SOURCE_ROLE_AMBIGUOUS",
            fail_code=GovernanceCheckCode.SOURCE_ROLE_AMBIGUOUS,
            evidence={"ambiguous": ",".join(sorted(ambiguous))},
        ),
    ]


def _check(
    pass_code: GovernanceCheckCode,
    ok: bool,
    ok_message: str,
    fail_message: str,
    *,
    fail_code: GovernanceCheckCode | None = None,
    evidence: dict[str, str] | None = None,
) -> GovernanceCheckResult:
    if ok:
        return GovernanceCheckResult(
            code=pass_code,
            severity=CheckSeverity.PASS,
            passed=True,
            message=ok_message,
            evidence=evidence or {},
        )
    return GovernanceCheckResult(
        code=fail_code or pass_code,
        severity=CheckSeverity.ERROR,
        passed=False,
        message=fail_message,
        evidence=evidence or {},
    )
