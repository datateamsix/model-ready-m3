"""Append-oriented BigQuery experience ledger. Optional at unit-test time."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
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
