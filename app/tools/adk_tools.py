"""ADK-callable wrappers around deterministic M3 primitives.

Keep pandas and BigQuery inside these functions. Arguments and returns are JSON-safe.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.errors import ValidationBlockedError
from app.registry.loader import lookup_provider, require_executable, search_providers
from app.rules.pocket_card import MERIDIAN_POCKET_CARD
from app.tools.artifacts import sha256_file, write_json_artifact
from app.tools.inventory import inventory_files
from app.tools.io import read_table, write_table
from app.tools.mapping import apply_mapping
from app.tools.profiling import detect_duplicates, detect_grain, profile_dataframe
from app.tools.remediation import (
    aggregate_to_week,
    canonicalize_channel_labels,
    normalize_dates,
    normalize_numeric_values,
    remove_exact_duplicates,
)
from app.tools.validation import (
    all_blocking_checks_pass,
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


def remove_exact_duplicates_from_file(path: str, output_path: str) -> dict[str, Any]:
    """Drop exact duplicate rows into a versioned output file. Raw input is not modified."""
    source = read_table(path)
    result = remove_exact_duplicates(source)
    written = write_table(result, output_path)
    return {
        "tool": "remove_exact_duplicates",
        "source_path": path,
        "output_path": str(written),
        "input_rows": int(len(source)),
        "output_rows": int(len(result)),
    }


def normalize_dates_in_file(path: str, column: str, output_path: str) -> dict[str, Any]:
    """Normalize unambiguous dates to YYYY-MM-DD in a copied output file."""
    source = read_table(path)
    result = normalize_dates(source, column)
    written = write_table(result, output_path)
    return {
        "tool": "normalize_dates",
        "source_path": path,
        "output_path": str(written),
        "column": column,
    }


def normalize_numeric_values_in_file(path: str, column: str, output_path: str) -> dict[str, Any]:
    """Coerce currency/percent strings to numbers. Fails closed on lossy conversion."""
    source = read_table(path)
    result = normalize_numeric_values(source, column)
    written = write_table(result, output_path)
    return {
        "tool": "normalize_numeric_values",
        "source_path": path,
        "output_path": str(written),
        "column": column,
    }


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
    return {
        "tool": "canonicalize_channel_labels",
        "source_path": path,
        "output_path": str(written),
        "column": column,
        "unmapped_values": unmapped,
    }


def aggregate_file_to_week(
    path: str,
    date_column: str,
    group_columns: list[str],
    sum_columns: list[str],
    output_path: str,
) -> dict[str, Any]:
    """Aggregate summable columns to Monday-start weeks. Do not pass rate columns."""
    source = read_table(path)
    result = aggregate_to_week(
        source,
        date_column=date_column,
        group_columns=group_columns,
        sum_columns=sum_columns,
    )
    written = write_table(result, output_path)
    return {
        "tool": "aggregate_to_week",
        "source_path": path,
        "output_path": str(written),
        "input_rows": int(len(source)),
        "output_rows": int(len(result)),
        "sum_columns": sum_columns,
    }


def apply_mapping_to_file(
    path: str,
    mapping: dict[str, str],
    output_path: str,
    provider_id: str | None = None,
) -> dict[str, Any]:
    """Apply a rename map. If provider_id is set, it must be trust=executable."""
    if provider_id:
        require_executable(provider_id)
    source = read_table(path)
    result = apply_mapping(source, mapping)
    written = write_table(result, output_path)
    return {
        "tool": "apply_mapping",
        "source_path": path,
        "output_path": str(written),
        "provider_id": provider_id,
        "mapping": mapping,
    }


def validate_readiness_file(
    path: str,
    required_columns: list[str],
    grain_columns: list[str],
    date_column: str | None = None,
) -> dict[str, Any]:
    """Run deterministic readiness checks. Never treat model prose as PASS."""
    frame = read_table(path)
    results = [
        validate_no_missing(frame, required_columns),
        validate_unique_grain(frame, grain_columns),
    ]
    if date_column:
        results.append(validate_iso_dates(frame, date_column))
    payload = {
        "path": path,
        "all_passed": all_blocking_checks_pass(results),
        "checks": [
            {"rule_id": item.rule_id, "passed": item.passed, "message": item.message}
            for item in results
        ],
    }
    return payload


def write_json_report(path: str, payload_json: str) -> dict[str, Any]:
    """Write a JSON artifact (readiness report, manifest, provenance, or contract)."""
    payload = json.loads(payload_json)
    written = write_json_artifact(path, payload)
    return {"path": str(written), "sha256": sha256_file(written)}


def write_meridian_contract(
    path: str,
    run_id: str,
    project_id: str,
    dataset_id: str,
    table_id: str,
    time_field: str,
    kpi_field: str,
    geo_field: str | None = None,
    media_columns: list[str] | None = None,
    spend_columns: list[str] | None = None,
) -> dict[str, Any]:
    """Write the minimum Meridian handoff contract (MR-020). Does not choose priors."""
    contract = {
        "run_id": run_id,
        "project_id": project_id,
        "dataset_id": dataset_id,
        "table_id": table_id,
        "time_field": time_field,
        "kpi_field": kpi_field,
        "geo_field": geo_field,
        "media_columns": media_columns or [],
        "spend_columns": spend_columns or [],
        "status": "COMPLETE" if time_field and kpi_field and table_id else "INCOMPLETE",
    }
    written = write_json_artifact(path, contract)
    return {"path": str(written), "contract": contract}


def set_model_ready_gate(
    readiness_report_path: str,
    parity_status: str,
    meridian_contract_path: str,
) -> dict[str, Any]:
    """Return MODEL_READY only when readiness, parity, and contract files prove it."""
    report = json.loads(Path(readiness_report_path).read_text(encoding="utf-8"))
    contract = json.loads(Path(meridian_contract_path).read_text(encoding="utf-8"))
    readiness_pass = bool(report.get("all_passed"))
    parity_pass = parity_status == "PASS"
    contract_pass = contract.get("status") == "COMPLETE"
    if not (readiness_pass and parity_pass and contract_pass):
        raise ValidationBlockedError(
            "MODEL_READY blocked: "
            f"readiness={readiness_pass} parity={parity_pass} contract={contract_pass}"
        )
    return {
        "status": "MODEL_READY",
        "readiness_pass": True,
        "parity_pass": True,
        "contract_pass": True,
    }


PHASE1_ADK_TOOLS = [
    get_meridian_pocket_card,
    lookup_provider_card,
    search_provider_directory,
    inventory_package,
    profile_source,
    detect_duplicates_in_file,
    detect_grain_in_file,
    remove_exact_duplicates_from_file,
    normalize_dates_in_file,
    normalize_numeric_values_in_file,
    canonicalize_channel_labels_in_file,
    aggregate_file_to_week,
    apply_mapping_to_file,
    validate_readiness_file,
    write_json_report,
    write_meridian_contract,
    set_model_ready_gate,
]
