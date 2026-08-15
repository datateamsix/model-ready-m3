"""BigQuery model-artifact publishing and parity helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

import pandas as pd
from google.cloud import bigquery


def schema_fingerprint(columns: Iterable[tuple[str, str]]) -> str:
    payload = json.dumps(list(columns), separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dataframe_schema_fingerprint(frame: pd.DataFrame) -> str:
    return schema_fingerprint((str(column), str(dtype)) for column, dtype in frame.dtypes.items())


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
    bq = client or bigquery.Client(project=project_id)
    destination = f"{project_id}.{dataset_id}.{table_id}"
    job = bq.load_table_from_dataframe(
        frame,
        destination,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    job.result()
    return destination


def validate_bigquery_row_parity(
    *,
    expected_rows: int,
    table_ref: str,
    client: bigquery.Client,
) -> bool:
    table = client.get_table(table_ref)
    return int(table.num_rows) == expected_rows
