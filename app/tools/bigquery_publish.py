"""BigQuery model-artifact publishing and parity helpers."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable

import pandas as pd
from google.cloud import bigquery

from app.config import settings
from app.core.contracts import BigQueryPublishReceipt, ParityCheck
from app.core.errors import PublishParityError
from app.core.model_intent import MODEL_READY_COLUMNS
from app.tools.fingerprints import content_fingerprint, schema_signature
from app.tools.model_frame import coerce_model_frame_types

_TABLE_SAFE = re.compile(r"[^a-zA-Z0-9_]+")


def schema_fingerprint(columns: Iterable[tuple[str, str]]) -> str:
    payload = json.dumps(list(columns), separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dataframe_schema_fingerprint(frame: pd.DataFrame) -> str:
    return schema_fingerprint(schema_signature(frame, MODEL_READY_COLUMNS))


def sanitize_table_id(run_id: str) -> str:
    cleaned = _TABLE_SAFE.sub("_", run_id.strip().lower()).strip("_")
    if not cleaned:
        raise ValueError("run_id produced an empty BigQuery table id")
    if cleaned[0].isdigit():
        cleaned = f"r_{cleaned}"
    return f"model_input_{cleaned}"[:1024]


def write_bigquery_model_table(
    frame: pd.DataFrame,
    *,
    project_id: str,
    dataset_id: str,
    table_id: str,
    client: bigquery.Client | None = None,
) -> str:
    """Write a run-scoped/versioned validated artifact to BigQuery.

    Callers must run deterministic readiness checks before invoking this function.
    """
    bq = client or bigquery.Client(project=project_id, location=settings.cloud_region)
    destination = f"{project_id}.{dataset_id}.{table_id}"
    payload = coerce_model_frame_types(frame)
    job = bq.load_table_from_dataframe(
        payload,
        destination,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    job.result()
    return destination


def read_bigquery_table(
    table_ref: str,
    *,
    client: bigquery.Client,
) -> pd.DataFrame:
    query = f"SELECT * FROM `{table_ref}`"
    return client.query(query).result().to_dataframe(create_bqstorage_client=False)


def validate_bigquery_publish_parity(
    *,
    local_frame: pd.DataFrame,
    table_ref: str,
    run_id: str,
    project_id: str,
    dataset_id: str,
    table_id: str,
    client: bigquery.Client,
    meridian_contract_uri: str = "",
    provenance_uri: str = "",
) -> BigQueryPublishReceipt:
    raw_published = read_bigquery_table(table_ref, client=client)
    local = coerce_model_frame_types(local_frame)
    published = coerce_model_frame_types(raw_published)

    local_rows = int(len(local))
    published_rows = int(len(published))
    local_cols = [column for column in MODEL_READY_COLUMNS if column in local.columns]
    published_cols = [column for column in MODEL_READY_COLUMNS if column in published.columns]
    local_fp = content_fingerprint(local, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"])
    published_fp = content_fingerprint(
        published, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"]
    )
    local_schema = schema_fingerprint(schema_signature(local, MODEL_READY_COLUMNS))
    published_schema = schema_fingerprint(schema_signature(published, MODEL_READY_COLUMNS))
    local_keys = set(zip(local["time"].astype(str), local["geo"].astype(str), strict=False))
    published_keys = set(
        zip(published["time"].astype(str), published["geo"].astype(str), strict=False)
    )
    local_nulls = int(local.loc[:, MODEL_READY_COLUMNS].isna().sum().sum())
    published_nulls = int(published.loc[:, MODEL_READY_COLUMNS].isna().sum().sum())

    checks = [
        ParityCheck(
            name="row_count",
            passed=local_rows == published_rows,
            evidence={"local": local_rows, "published": published_rows},
        ),
        ParityCheck(
            name="columns",
            passed=local_cols == MODEL_READY_COLUMNS and published_cols == MODEL_READY_COLUMNS,
            evidence={"local": local_cols, "published": published_cols},
        ),
        ParityCheck(
            name="schema",
            passed=local_schema == published_schema,
            evidence={"local": local_schema, "published": published_schema},
        ),
        ParityCheck(
            name="keys",
            passed=local_keys == published_keys,
            evidence={
                "only_local": len(local_keys - published_keys),
                "only_published": len(published_keys - local_keys),
            },
        ),
        ParityCheck(
            name="nulls",
            passed=local_nulls == published_nulls,
            evidence={"local": local_nulls, "published": published_nulls},
        ),
        ParityCheck(
            name="content_fingerprint",
            passed=local_fp == published_fp,
            evidence={"local": local_fp, "published": published_fp},
        ),
    ]
    parity_pass = all(check.passed for check in checks)
    receipt = BigQueryPublishReceipt(
        run_id=run_id,
        status="PUBLISHED" if parity_pass else "PARITY_FAILED",
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id,
        row_count=published_rows,
        schema_fingerprint=published_schema,
        artifact_fingerprint=local_fp,
        published_fingerprint=published_fp,
        parity_status="PASS" if parity_pass else "FAIL",
        meridian_contract_uri=meridian_contract_uri,
        provenance_uri=provenance_uri,
        parity_checks=checks,
    )
    if not parity_pass:
        raise PublishParityError(
            f"BigQuery publish parity failed for {table_ref}: {receipt.model_dump(mode='json')}"
        )
    return receipt


def validate_bigquery_row_parity(
    *,
    expected_rows: int,
    table_ref: str,
    client: bigquery.Client,
) -> bool:
    table = client.get_table(table_ref)
    return int(table.num_rows) == expected_rows
