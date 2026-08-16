"""Resolve the independently verified BigQuery model-consumption input.

Production diagnostics fail closed when the endpoint cannot be proven to
represent the verified run. Unit tests may inject a fixture adapter.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import pandas as pd
from google.cloud import bigquery

from app.core.contracts import utc_now
from app.core.errors import ValidationBlockedError
from app.core.run_repository import RunRepository, get_run_repository
from app.intelligence.contracts import SourceMode
from app.intelligence.snapshot import (
    DiagnosticSnapshot,
    VerifiedEndpoint,
    resolve_knots_assumption,
)
from app.tools.fingerprints import content_fingerprint, schema_signature
from app.tools.meridian_contract import MeridianInputContract


class FixtureAdapter:
    """Deterministic local adapter. Never used as a silent production fallback."""

    def __init__(
        self,
        *,
        run_id: str,
        frame: pd.DataFrame,
        contract: MeridianInputContract,
        expected_fingerprint: str,
        schema_fingerprint: str,
        project_id: str = "fixture-project",
        dataset_id: str = "fixture_dataset",
        table_id: str = "fixture_table",
        view_id: str | None = None,
        eda_receipt: dict[str, Any] | None = None,
        confirmed_confounders: list[str] | None = None,
        optional_predictors: list[str] | None = None,
        transformation_provenance: list[dict[str, Any]] | None = None,
        issues: list[dict[str, Any]] | None = None,
        semantic_answers: list[dict[str, Any]] | None = None,
        mapping_confidence: dict[str, str] | None = None,
        modeler_n_knots: int | None = None,
    ) -> None:
        self.run_id = run_id
        self.frame = frame
        self.contract = contract
        self.expected_fingerprint = expected_fingerprint
        self.schema_fingerprint = schema_fingerprint
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.view_id = view_id
        self.eda_receipt = eda_receipt
        self.confirmed_confounders = confirmed_confounders or []
        self.optional_predictors = optional_predictors or []
        self.transformation_provenance = transformation_provenance or []
        self.issues = issues or []
        self.semantic_answers = semantic_answers or []
        self.mapping_confidence = mapping_confidence or {}
        self.modeler_n_knots = modeler_n_knots


def load_verified_snapshot(
    run_id: str,
    *,
    repo: RunRepository | None = None,
    adapter: FixtureAdapter | None = None,
    bq_client: bigquery.Client | None = None,
    modeler_n_knots: int | None = None,
) -> DiagnosticSnapshot:
    if adapter is not None:
        return _snapshot_from_adapter(adapter, modeler_n_knots=modeler_n_knots)
    repository = repo or get_run_repository()
    return _snapshot_from_verified_bigquery(
        run_id,
        repo=repository,
        bq_client=bq_client,
        modeler_n_knots=modeler_n_knots,
    )


def fingerprint_frame(frame: pd.DataFrame, contract: MeridianInputContract) -> str:
    columns = _fingerprint_columns(frame, contract)
    keys = ["time"]
    if contract.fields.geo and contract.fields.geo in frame.columns:
        keys.append("geo")
    return content_fingerprint(frame, columns=columns, key_columns=keys)


def schema_fingerprint_for(frame: pd.DataFrame, contract: MeridianInputContract) -> str:
    columns = _fingerprint_columns(frame, contract)
    signature = schema_signature(frame, columns=columns)
    payload = "|".join(f"{name}:{logical}" for name, logical in signature)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _snapshot_from_adapter(
    adapter: FixtureAdapter, *, modeler_n_knots: int | None
) -> DiagnosticSnapshot:
    frame = coerce_diagnostic_frame(adapter.frame.copy(), adapter.contract)
    actual = fingerprint_frame(frame, adapter.contract)
    if actual != adapter.expected_fingerprint:
        raise ValidationBlockedError(
            "Fixture adapter fingerprint mismatch: the provided frame is not the "
            f"verified input. expected={adapter.expected_fingerprint} actual={actual}"
        )
    queried_at = utc_now()
    knots = resolve_knots_assumption(
        frame=frame,
        contract=adapter.contract,
        eda_receipt=adapter.eda_receipt,
        modeler_n_knots=modeler_n_knots if modeler_n_knots is not None else adapter.modeler_n_knots,
    )
    endpoint = VerifiedEndpoint(
        run_id=adapter.run_id,
        project_id=adapter.project_id,
        dataset_id=adapter.dataset_id,
        table_id=adapter.table_id,
        view_id=adapter.view_id,
        resolved_source=(
            f"{adapter.project_id}.{adapter.dataset_id}."
            f"{adapter.view_id or adapter.table_id}"
        ),
        source_mode=SourceMode.FIXTURE_ADAPTER,
        input_fingerprint=actual,
        schema_fingerprint=adapter.schema_fingerprint,
        expected_fingerprint=adapter.expected_fingerprint,
        row_count=int(len(frame)),
        queried_at=queried_at,
        consumption_view=adapter.view_id,
    )
    return DiagnosticSnapshot(
        endpoint=endpoint,
        contract=adapter.contract,
        frame=frame,
        knots=knots,
        time_grain="weekly",
        model_scope=adapter.contract.model_scope,
        confirmed_confounders=list(adapter.confirmed_confounders),
        optional_predictors=list(adapter.optional_predictors),
        transformation_provenance=list(adapter.transformation_provenance),
        issues=list(adapter.issues),
        eda_receipt=adapter.eda_receipt,
        semantic_answers=list(adapter.semantic_answers),
        mapping_confidence=dict(adapter.mapping_confidence),
    )


def _snapshot_from_verified_bigquery(
    run_id: str,
    *,
    repo: RunRepository,
    bq_client: bigquery.Client | None,
    modeler_n_knots: int | None,
) -> DiagnosticSnapshot:
    state = repo.load_run(run_id)
    if state.run_id != run_id:
        raise ValidationBlockedError("Run identity mismatch while resolving diagnostic source.")
    publish = repo.load_json(run_id, "publish_receipt.json")
    contract_payload = repo.load_json(run_id, "meridian_input_contract.json")
    if not publish:
        raise ValidationBlockedError(
            "Pre-EDA diagnostics fail closed: missing BigQuery publish receipt."
        )
    if not contract_payload:
        raise ValidationBlockedError(
            "Pre-EDA diagnostics fail closed: missing Meridian input contract."
        )
    if str(publish.get("status")) != "PUBLISHED" or str(publish.get("parity_status")) != "PASS":
        raise ValidationBlockedError(
            "Pre-EDA diagnostics fail closed: BigQuery verification did not pass."
        )
    contract = MeridianInputContract.model_validate(contract_payload)
    if contract.run_id != run_id:
        raise ValidationBlockedError("Contract run_id does not match the requested run.")
    expected_fp = str(
        publish.get("published_fingerprint") or publish.get("artifact_fingerprint") or ""
    )
    if not expected_fp:
        raise ValidationBlockedError(
            "Pre-EDA diagnostics fail closed: publish receipt has no input fingerprint."
        )
    project_id = str(publish.get("project_id") or contract.source.project_id)
    dataset_id = str(publish.get("dataset_id") or contract.source.dataset_id)
    table_id = str(publish.get("table_id") or contract.source.table_id)
    view_id = str(publish.get("consumption_view") or state.model_consumption_view or "") or None
    if view_id and "." in view_id:
        resolved = view_id
    elif view_id:
        resolved = f"{project_id}.{dataset_id}.{view_id}"
    else:
        resolved = f"{project_id}.{dataset_id}.{table_id}"
    if not project_id or not dataset_id or not table_id:
        raise ValidationBlockedError(
            "Pre-EDA diagnostics fail closed: incomplete BigQuery endpoint identity."
        )
    client = bq_client or bigquery.Client(project=project_id)
    queried_at = utc_now()
    frame = coerce_diagnostic_frame(_read_consumption_table(client, resolved, queried_at), contract)
    actual_fp = fingerprint_frame(frame, contract)
    if actual_fp != expected_fp:
        raise ValidationBlockedError(
            "Pre-EDA diagnostics fail closed: verified endpoint fingerprint mismatch. "
            f"expected={expected_fp} actual={actual_fp}"
        )
    expected_rows = int(publish.get("row_count") or 0)
    if expected_rows and int(len(frame)) != expected_rows:
        raise ValidationBlockedError(
            "Pre-EDA diagnostics fail closed: row count mismatch against publish receipt."
        )
    schema_fp = str(publish.get("schema_fingerprint") or "")
    eda_receipt = repo.load_json(run_id, "eda/meridian_eda_receipt.json")
    provenance = repo.load_json(run_id, "provenance.json") or {}
    issues = [
        issue.model_dump(mode="json") if hasattr(issue, "model_dump") else issue
        for issue in repo.load_issues(run_id)
    ]
    semantic_payload = repo.load_json(run_id, "intelligence/semantic_context.json") or {}
    knots = resolve_knots_assumption(
        frame=frame,
        contract=contract,
        eda_receipt=eda_receipt,
        modeler_n_knots=modeler_n_knots,
    )
    endpoint = VerifiedEndpoint(
        run_id=run_id,
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id,
        view_id=view_id,
        resolved_source=resolved,
        source_mode=SourceMode.BIGQUERY,
        input_fingerprint=actual_fp,
        schema_fingerprint=schema_fp,
        expected_fingerprint=expected_fp,
        row_count=int(len(frame)),
        queried_at=queried_at,
        consumption_view=view_id,
    )
    return DiagnosticSnapshot(
        endpoint=endpoint,
        contract=contract,
        frame=frame,
        knots=knots,
        time_grain="weekly",
        model_scope=contract.model_scope,
        transformation_provenance=list(
            provenance.get("records") or provenance.get("transforms") or []
        ),
        issues=issues,
        eda_receipt=eda_receipt,
        semantic_answers=list(semantic_payload.get("answers") or []),
    )


def _read_consumption_table(
    client: bigquery.Client, table_ref: str, queried_at: datetime
) -> pd.DataFrame:
    del queried_at
    query = f"SELECT * FROM `{table_ref}`"
    return client.query(query).result().to_dataframe(create_bqstorage_client=False)


def coerce_diagnostic_frame(frame: pd.DataFrame, contract: MeridianInputContract) -> pd.DataFrame:
    result = frame.copy(deep=True)
    time_col = contract.fields.time
    if time_col not in result.columns:
        raise ValidationBlockedError("Verified input is missing the contract time field.")
    result[time_col] = pd.to_datetime(result[time_col], errors="raise").dt.strftime("%Y-%m-%d")
    geo_col = contract.fields.geo
    if geo_col and geo_col in result.columns:
        result[geo_col] = result[geo_col].astype(str)
    return result


def _fingerprint_columns(frame: pd.DataFrame, contract: MeridianInputContract) -> list[str]:
    ordered = [
        contract.fields.time,
        contract.fields.geo,
        contract.fields.kpi,
        contract.fields.revenue_per_kpi,
        contract.fields.population,
        *contract.media.values(),
        *contract.media_spend.values(),
        *contract.organic_media,
        *contract.controls,
    ]
    seen: list[str] = []
    for column in ordered:
        if column and column in frame.columns and column not in seen:
            seen.append(column)
    return seen
