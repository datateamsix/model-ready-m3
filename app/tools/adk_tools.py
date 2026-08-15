"""ADK-callable wrappers around deterministic M3 primitives.

Keep pandas and BigQuery inside these functions. Arguments and returns are JSON-safe.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.errors import ValidationBlockedError
from app.core.model_intent import load_model_intent
from app.integrations.bigquery import get_bigquery_client
from app.registry.loader import lookup_provider, search_providers
from app.rules.pocket_card import MERIDIAN_POCKET_CARD
from app.tools.artifacts import sha256_file, write_json_artifact
from app.tools.bigquery_publish import (
    sanitize_table_id,
    validate_bigquery_publish_parity,
    write_bigquery_model_table,
)
from app.tools.gate import evaluate_model_ready_gate
from app.tools.inventory import inventory_files
from app.tools.io import read_table, write_table
from app.tools.mapping import apply_mapping
from app.tools.meridian_contract import generate_meridian_input_contract
from app.tools.model_frame import build_model_ready_frame
from app.tools.profiling import (
    detect_duplicates,
    detect_grain,
    detect_non_summable_columns,
    profile_dataframe,
)
from app.tools.provenance import FRAME_SOURCE_ROLES, record_transform
from app.tools.remediation import (
    aggregate_campaign_to_channel,
    aggregate_to_week,
    canonicalize_channel_labels,
    normalize_dates,
    normalize_numeric_values,
    remove_exact_duplicates,
)
from app.tools.validation import (
    all_blocking_checks_pass,
    readiness_from_path,
    validate_iso_dates,
    validate_no_missing,
    validate_unique_grain,
)


def get_meridian_pocket_card() -> dict[str, Any]:
    """Return the compact Meridian readiness card (rule IDs, not full documentation)."""
    return dict(MERIDIAN_POCKET_CARD)


def lookup_provider_card(query: str) -> dict[str, Any]:
    """Return one provider registry card by id, name, or filename hint.

    Directory cards are identification and Meridian-gap context only.
    """
    entry = lookup_provider(query)
    if entry is None:
        return {"found": False, "query": query}
    return {"found": True, "entry": entry.model_dump(mode="json")}


def search_provider_directory(query: str, limit: int = 8) -> dict[str, Any]:
    """Search provider ids and one-line Meridian gap summaries. Does not return field maps."""
    return {"query": query, "matches": search_providers(query, limit=limit)}


def inventory_package(root: str) -> dict[str, Any]:
    """List files under a local package root. Use the same contract for later GCS adapters."""
    records = inventory_files(root)
    names = [str(item["path"]) for item in records]
    if any("expected_model_ready" in name for name in names):
        raise ValidationBlockedError("Runtime inventory must not include regression truth files.")
    return {"root": root, "file_count": len(records), "files": records}


def profile_source(path: str) -> dict[str, Any]:
    """Return a compact deterministic profile of a CSV or parquet file."""
    frame = read_table(path)
    profile = profile_dataframe(frame)
    profile["path"] = path
    return profile


def detect_duplicates_in_file(path: str, subset: list[str] | None = None) -> dict[str, Any]:
    """Detect duplicate rows, optionally at a canonical grain."""
    frame = read_table(path)
    result = detect_duplicates(frame, subset)
    result["path"] = path
    return result


def detect_grain_in_file(path: str, date_column: str) -> dict[str, Any]:
    """Infer daily, weekly, or monthly grain from a date column."""
    frame = read_table(path)
    result = detect_grain(frame, date_column)
    result["path"] = path
    return result


def detect_non_summable_metrics(path: str, provider_id: str | None = None) -> dict[str, Any]:
    """Flag CTR/CPC and other non-summable rates. Presence is not a seeded defect."""
    frame = read_table(path)
    result = detect_non_summable_columns(frame, provider_id)
    result["path"] = path
    return result


def remove_exact_duplicates_from_file(path: str, output_path: str) -> dict[str, Any]:
    """Drop exact duplicate rows into a versioned output file. Raw input is not modified."""
    source = read_table(path)
    result = remove_exact_duplicates(source)
    written = write_table(result, output_path)
    payload = {
        "tool": "remove_exact_duplicates",
        "source_path": path,
        "output_path": str(written),
        "input_rows": int(len(source)),
        "output_rows": int(len(result)),
    }
    payload["provenance"] = record_transform(
        tool="remove_exact_duplicates",
        rule_id="MR-010",
        source_uri=path,
        output_uri=str(written),
        input_rows=int(len(source)),
        output_rows=int(len(result)),
        parameters={},
        reason="Remove exact duplicate observations.",
    )
    return payload


def normalize_dates_in_file(
    path: str,
    column: str,
    output_path: str,
    expected_format: str,
) -> dict[str, Any]:
    """Normalize dates with an explicit source format to YYYY-MM-DD."""
    source = read_table(path)
    result = normalize_dates(source, column, expected_format)
    written = write_table(result, output_path)
    payload = {
        "tool": "normalize_dates",
        "source_path": path,
        "output_path": str(written),
        "column": column,
        "expected_format": expected_format,
    }
    payload["provenance"] = record_transform(
        tool="normalize_dates",
        rule_id="MR-001",
        source_uri=path,
        output_uri=str(written),
        input_rows=int(len(source)),
        output_rows=int(len(result)),
        parameters={"column": column, "expected_format": expected_format},
        reason="Normalize unambiguous source dates to ISO.",
    )
    return payload


def normalize_numeric_values_in_file(path: str, column: str, output_path: str) -> dict[str, Any]:
    """Coerce currency/percent strings to numbers. Fails closed on lossy conversion."""
    source = read_table(path)
    result = normalize_numeric_values(source, column)
    written = write_table(result, output_path)
    payload = {
        "tool": "normalize_numeric_values",
        "source_path": path,
        "output_path": str(written),
        "column": column,
    }
    payload["provenance"] = record_transform(
        tool="normalize_numeric_values",
        rule_id="MR-017",
        source_uri=path,
        output_uri=str(written),
        input_rows=int(len(source)),
        output_rows=int(len(result)),
        parameters={"column": column},
        reason="Lossless numeric/currency coercion.",
    )
    return payload


def canonicalize_channel_labels_in_file(
    path: str,
    column: str,
    mapping: dict[str, str],
    output_path: str,
) -> dict[str, Any]:
    """Rewrite channel labels with an explicit mapping and report leftover values."""
    source = read_table(path)
    result = canonicalize_channel_labels(source, column, mapping)
    written = write_table(result, output_path)
    originals = [str(value) for value in source[column].tolist()]
    unmapped = sorted({value for value in originals if value not in mapping})
    payload = {
        "tool": "canonicalize_channel_labels",
        "source_path": path,
        "output_path": str(written),
        "column": column,
        "unmapped_values": unmapped,
    }
    payload["provenance"] = record_transform(
        tool="canonicalize_channel_labels",
        rule_id="MR-009",
        source_uri=path,
        output_uri=str(written),
        input_rows=int(len(source)),
        output_rows=int(len(result)),
        parameters={"column": column, "mapping": mapping},
        reason="Canonicalize channel taxonomy with an explicit map.",
    )
    return payload


def aggregate_campaign_to_channel_in_file(
    path: str,
    grain_columns: list[str],
    sum_columns: list[str],
    output_path: str,
    provider_id: str | None = None,
) -> dict[str, Any]:
    """Aggregate campaign rows to modeled channel grain using summable metrics only."""
    source = read_table(path)
    result = aggregate_campaign_to_channel(
        source,
        grain_columns=grain_columns,
        sum_columns=sum_columns,
        provider_id=provider_id,
    )
    written = write_table(result, output_path)
    payload = {
        "tool": "aggregate_campaign_to_channel",
        "source_path": path,
        "output_path": str(written),
        "input_rows": int(len(source)),
        "output_rows": int(len(result)),
        "sum_columns": sum_columns,
        "provider_id": provider_id,
    }
    payload["provenance"] = record_transform(
        tool="aggregate_campaign_to_channel",
        rule_id="MR-009",
        source_uri=path,
        output_uri=str(written),
        input_rows=int(len(source)),
        output_rows=int(len(result)),
        parameters={
            "grain_columns": grain_columns,
            "sum_columns": sum_columns,
            "provider_id": provider_id,
        },
        reason="Aggregate campaign rows to modeled channels.",
    )
    return payload


def aggregate_file_to_week(
    path: str,
    date_column: str,
    group_columns: list[str],
    sum_columns: list[str],
    output_path: str,
    provider_id: str | None = None,
) -> dict[str, Any]:
    """Aggregate summable columns to Monday-start weeks. Rejects rate columns."""
    source = read_table(path)
    result = aggregate_to_week(
        source,
        date_column=date_column,
        group_columns=group_columns,
        sum_columns=sum_columns,
        provider_id=provider_id,
    )
    written = write_table(result, output_path)
    payload = {
        "tool": "aggregate_to_week",
        "source_path": path,
        "output_path": str(written),
        "input_rows": int(len(source)),
        "output_rows": int(len(result)),
        "sum_columns": sum_columns,
        "provider_id": provider_id,
    }
    payload["provenance"] = record_transform(
        tool="aggregate_to_week",
        rule_id="MR-003",
        source_uri=path,
        output_uri=str(written),
        input_rows=int(len(source)),
        output_rows=int(len(result)),
        parameters={
            "date_column": date_column,
            "group_columns": group_columns,
            "sum_columns": sum_columns,
            "provider_id": provider_id,
        },
        reason="Align source grain to Monday-start weeks.",
    )
    return payload


def apply_mapping_to_file(
    path: str,
    mapping: dict[str, str],
    output_path: str,
    provider_id: str | None = None,
) -> dict[str, Any]:
    """Apply a rename map. Executable providers must not contradict registry semantics."""
    source = read_table(path)
    result = apply_mapping(source, mapping, provider_id=provider_id)
    written = write_table(result, output_path)
    payload = {
        "tool": "apply_mapping",
        "source_path": path,
        "output_path": str(written),
        "provider_id": provider_id,
        "mapping": mapping,
    }
    payload["provenance"] = record_transform(
        tool="apply_mapping",
        rule_id="MR-009",
        source_uri=path,
        output_uri=str(written),
        input_rows=int(len(source)),
        output_rows=int(len(result)),
        parameters={"mapping": mapping, "provider_id": provider_id},
        reason="Apply provider-backed field mapping.",
    )
    return payload


def build_model_ready_frame_from_files(
    google_path: str,
    meta_path: str,
    shopify_path: str,
    ga4_path: str,
    controls_path: str,
    population_path: str,
    intent_json_path: str,
    output_path: str,
) -> dict[str, Any]:
    """Assemble the canonical time × geo model frame from repaired sources + model intent."""
    intent = load_model_intent(json.loads(Path(intent_json_path).read_text(encoding="utf-8")))
    frame = build_model_ready_frame(
        google=read_table(google_path),
        meta=read_table(meta_path),
        shopify=read_table(shopify_path),
        ga4=read_table(ga4_path),
        controls=read_table(controls_path),
        population=read_table(population_path),
        intent=intent,
    )
    written = write_table(frame, output_path)
    payload = {
        "tool": "build_model_ready_frame",
        "output_path": str(written),
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
    }
    payload["provenance"] = record_transform(
        tool="build_model_ready_frame",
        rule_id="MR-018",
        source_uri=google_path,
        output_uri=str(written),
        input_rows=int(len(frame)),
        output_rows=int(len(frame)),
        sources=[
            {"role": "google_media", "uri": google_path},
            {"role": "meta_media", "uri": meta_path},
            {"role": "kpi_revenue", "uri": shopify_path},
            {"role": "organic_media", "uri": ga4_path},
            {"role": "controls", "uri": controls_path},
            {"role": "population", "uri": population_path},
            {"role": "model_intent", "uri": intent_json_path},
        ],
        parameters={"source_roles": list(FRAME_SOURCE_ROLES)},
        reason="Join repaired sources into the canonical model frame.",
    )
    return payload


def validate_model_ready_artifact_file(
    path: str,
    intent_json_path: str,
    provenance_path: str,
    run_id: str,
) -> dict[str, Any]:
    """Write/return a deterministic readiness receipt. Agent prose cannot PASS."""
    intent = load_model_intent(json.loads(Path(intent_json_path).read_text(encoding="utf-8")))
    manifest = json.loads(Path(provenance_path).read_text(encoding="utf-8"))
    receipt = readiness_from_path(
        path,
        run_id=run_id,
        intent=intent,
        provenance_manifest=manifest,
    )
    return receipt.model_dump(mode="json")


def validate_readiness_file(
    path: str,
    required_columns: list[str],
    grain_columns: list[str],
    date_column: str | None = None,
) -> dict[str, Any]:
    """Narrow readiness checks used by intermediate repaired files."""
    frame = read_table(path)
    results = [
        validate_no_missing(frame, required_columns),
        validate_unique_grain(frame, grain_columns),
    ]
    if date_column:
        results.append(validate_iso_dates(frame, date_column))
    return {
        "path": path,
        "all_passed": all_blocking_checks_pass(results),
        "checks": [
            {"rule_id": item.rule_id, "passed": item.passed, "message": item.message}
            for item in results
        ],
    }


def write_json_report(path: str, payload_json: str) -> dict[str, Any]:
    """Write a JSON artifact (readiness report, manifest, provenance, or contract)."""
    payload = json.loads(payload_json)
    written = write_json_artifact(path, payload)
    return {"path": str(written), "sha256": sha256_file(written)}


def publish_model_ready_table(artifact_path: str, run_id: str) -> dict[str, Any]:
    """Publish the validated artifact to the configured models dataset."""
    frame = read_table(artifact_path)
    project_id = settings.project_id
    dataset_id = settings.bq_models_dataset
    table_id = sanitize_table_id(run_id)
    client = get_bigquery_client()
    destination = write_bigquery_model_table(
        frame,
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id,
        client=client,
    )
    return {
        "status": "WRITTEN",
        "table_ref": destination,
        "project_id": project_id,
        "dataset_id": dataset_id,
        "table_id": table_id,
        "row_count": int(len(frame)),
        "artifact_path": artifact_path,
        "run_id": run_id,
    }


def validate_bigquery_publish_parity_for_run(
    artifact_path: str,
    run_id: str,
    table_id: str,
    provenance_uri: str = "",
    meridian_contract_uri: str = "",
) -> dict[str, Any]:
    """Compare the local validated artifact to the published BigQuery table."""
    frame = read_table(artifact_path)
    project_id = settings.project_id
    dataset_id = settings.bq_models_dataset
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    receipt = validate_bigquery_publish_parity(
        local_frame=frame,
        table_ref=table_ref,
        run_id=run_id,
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id,
        client=get_bigquery_client(),
        meridian_contract_uri=meridian_contract_uri,
        provenance_uri=provenance_uri,
    )
    return receipt.model_dump(mode="json")


def generate_meridian_input_contract_file(
    artifact_path: str,
    intent_json_path: str,
    run_id: str,
    table_id: str,
    output_path: str,
) -> dict[str, Any]:
    """Generate MR-020 from the validated schema, intent, and published table identity."""
    intent = load_model_intent(json.loads(Path(intent_json_path).read_text(encoding="utf-8")))
    frame = read_table(artifact_path)
    contract = generate_meridian_input_contract(
        run_id=run_id,
        intent=intent,
        frame=frame,
        project_id=settings.project_id,
        dataset_id=settings.bq_models_dataset,
        table_id=table_id,
    )
    written = write_json_artifact(output_path, contract.model_dump(mode="json"))
    return {"path": str(written), "contract": contract.model_dump(mode="json")}


def evaluate_model_ready_gate_from_files(
    readiness_path: str,
    publish_receipt_path: str,
    meridian_contract_path: str,
    provenance_path: str,
) -> dict[str, Any]:
    """Terminal gate. PASS fields are read from deterministic receipts, never caller strings."""
    return evaluate_model_ready_gate(
        readiness=readiness_path,
        publish=publish_receipt_path,
        meridian_contract=meridian_contract_path,
        provenance=provenance_path,
    )


PHASE1_ADK_TOOLS = [
    get_meridian_pocket_card,
    lookup_provider_card,
    search_provider_directory,
    inventory_package,
    profile_source,
    detect_duplicates_in_file,
    detect_grain_in_file,
    detect_non_summable_metrics,
    remove_exact_duplicates_from_file,
    normalize_dates_in_file,
    normalize_numeric_values_in_file,
    canonicalize_channel_labels_in_file,
    aggregate_campaign_to_channel_in_file,
    aggregate_file_to_week,
    apply_mapping_to_file,
    build_model_ready_frame_from_files,
    validate_readiness_file,
    validate_model_ready_artifact_file,
    write_json_report,
    publish_model_ready_table,
    validate_bigquery_publish_parity_for_run,
    generate_meridian_input_contract_file,
    evaluate_model_ready_gate_from_files,
]
