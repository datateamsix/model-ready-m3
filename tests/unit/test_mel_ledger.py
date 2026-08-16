"""Append-oriented experience ledger tests."""

from __future__ import annotations

from pathlib import Path

from app.mel.ledger import experience_table_ddl, local_ledger_append, record_episode
from app.mel.models import EpisodeTerminalOutcome, ExperienceEpisode


def test_local_ledger_appends_without_rewrite(tmp_path: Path) -> None:
    episode = ExperienceEpisode(
        episode_id="ep-1",
        run_id="run-1",
        episode_started_at="2026-08-16T00:00:00+00:00",
        episode_closed_at="2026-08-16T01:00:00+00:00",
        terminal_outcome=EpisodeTerminalOutcome.MODEL_READY,
        domain_view_version="1.0.0",
        domain_view_fingerprint="fp",
        content_fingerprint="ep-fp",
    )
    path = record_episode(tmp_path, episode)
    local_ledger_append(tmp_path, "episodes", {"episode_id": "ep-2"})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert "ep-1" in lines[0]
    assert "ep-2" in lines[1]


def test_experience_table_ddl_covers_required_tables() -> None:
    statements = experience_table_ddl("example-project", "modelready_experience")
    assert set(statements) >= {
        "episodes",
        "candidate_lessons",
        "lesson_evaluations",
        "promoted_lessons",
        "learning_receipts",
        "experience_applications",
        "experience_reflections",
        "domain_view_registry",
    }
    assert all("CREATE TABLE IF NOT EXISTS" in body for body in statements.values())
    assert all("example-project" in body for body in statements.values())
