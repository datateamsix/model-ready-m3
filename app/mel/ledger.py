"""Append-oriented BigQuery experience ledger. Optional at unit-test time."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.cloud import bigquery

from app.config import settings
from app.core.contracts import utc_now
from app.integrations.bigquery import get_bigquery_client
from app.mel.models import (
    CandidateLesson,
    ExperienceApplication,
    ExperienceEpisode,
    ExperienceReflection,
    LessonEvaluation,
    PromotionReceipt,
)

TABLES = (
    "episodes",
    "candidate_lessons",
    "lesson_evaluations",
    "promoted_lessons",
    "learning_receipts",
    "experience_applications",
    "experience_reflections",
    "domain_view_registry",
)


def local_ledger_append(root: Path, table: str, row: dict[str, Any]) -> Path:
    path = root / f"{table}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    return path


def record_episode(root: Path, episode: ExperienceEpisode) -> Path:
    return local_ledger_append(root, "episodes", episode.model_dump(mode="json"))


def record_candidate(root: Path, candidate: CandidateLesson) -> Path:
    return local_ledger_append(root, "candidate_lessons", candidate.model_dump(mode="json"))


def record_evaluation(root: Path, evaluation: LessonEvaluation) -> Path:
    return local_ledger_append(root, "lesson_evaluations", evaluation.model_dump(mode="json"))


def record_promotion(root: Path, receipt: PromotionReceipt) -> Path:
    return local_ledger_append(root, "learning_receipts", receipt.model_dump(mode="json"))


def record_reflection(root: Path, reflection: ExperienceReflection) -> Path:
    return local_ledger_append(
        root,
        "experience_reflections",
        {
            "reflection_id": reflection.reflection_id,
            "episode_id": reflection.episode_id,
            "run_id": reflection.run_id,
            "reflection_fingerprint": reflection.content_fingerprint,
            "reflection_version": reflection.reflection_version,
            "summary": reflection.reflection_summary,
            "confirmed_count": len(reflection.confirmed),
            "missed_count": len(reflection.missed),
            "unknown_count": len(reflection.unknown),
            "possible_improvement_count": len(reflection.possible_improvements),
            "created_at": reflection.created_at,
            "artifact": "experience/experience_reflection.json",
        },
    )


def record_application(root: Path, application: ExperienceApplication) -> Path:
    return local_ledger_append(
        root, "experience_applications", application.model_dump(mode="json")
    )


def experience_dataset() -> str:
    return settings.bq_experience_dataset


EXPERIENCE_TABLE_COLUMNS = (
    "episode_id STRING",
    "run_id STRING",
    "record_id STRING",
    "content_fingerprint STRING",
    "status STRING",
    "payload JSON",
    "recorded_at TIMESTAMP",
)


def experience_table_ddl(project_id: str, dataset: str | None = None) -> dict[str, str]:
    """CREATE TABLE IF NOT EXISTS statements. Does not interpolate a hard-coded project."""
    dataset_id = dataset or experience_dataset()
    columns = ",\n  ".join(EXPERIENCE_TABLE_COLUMNS)
    statements: dict[str, str] = {}
    for table in TABLES:
        statements[table] = (
            f"CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.{table}` (\n"
            f"  {columns}\n"
            ")"
        )
    return statements


def experience_row(
    *,
    table: str,
    record_id: str,
    payload: dict[str, Any],
    episode_id: str = "",
    run_id: str = "",
    fingerprint: str = "",
    status: str = "",
) -> dict[str, Any]:
    if table not in TABLES:
        raise ValueError(f"unknown experience table: {table}")
    return {
        "episode_id": episode_id,
        "run_id": run_id,
        "record_id": record_id,
        "content_fingerprint": fingerprint,
        "status": status,
        "payload": payload,
        "recorded_at": utc_now().isoformat(),
    }


def ensure_experience_tables() -> list[str]:
    """Create the experience dataset/tables if they do not exist."""
    client = get_bigquery_client()
    dataset_id = f"{settings.project_id}.{experience_dataset()}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = settings.cloud_region
    client.create_dataset(dataset, exists_ok=True)
    created: list[str] = []
    for table, ddl in experience_table_ddl(settings.project_id).items():
        client.query(ddl, location=settings.cloud_region).result()
        created.append(table)
    return created


def write_experience_row(table: str, row: dict[str, Any]) -> str:
    if table not in TABLES:
        raise ValueError(f"unknown experience table: {table}")
    client = get_bigquery_client()
    table_id = f"{settings.project_id}.{experience_dataset()}.{table}"
    errors = client.insert_rows_json(table_id, [row])
    if errors:
        raise RuntimeError(f"experience ledger insert failed: {errors}")
    return str(row["record_id"])


def read_experience_row(table: str, record_id: str) -> dict[str, Any] | None:
    if table not in TABLES:
        raise ValueError(f"unknown experience table: {table}")
    client = get_bigquery_client()
    table_id = f"{settings.project_id}.{experience_dataset()}.{table}"
    job = client.query(
        (
            f"SELECT episode_id, run_id, record_id, content_fingerprint, status, "
            f"TO_JSON_STRING(payload) AS payload, recorded_at "
            f"FROM `{table_id}` WHERE record_id = @record_id LIMIT 1"
        ),
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("record_id", "STRING", record_id)
            ]
        ),
        location=settings.cloud_region,
    )
    rows = list(job.result())
    if not rows:
        return None
    item = dict(rows[0])
    payload = item.get("payload")
    if isinstance(payload, str) and payload:
        item["payload"] = json.loads(payload)
    return item
