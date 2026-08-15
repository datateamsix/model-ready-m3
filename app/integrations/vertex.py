"""Vertex AI / memory integration boundary.

MVP note: keep Memory Bank retrieval behind this adapter so the core M3 run can
ship before MEL persistence is fully wired.
"""

from app.config import settings


def vertex_context() -> dict[str, str]:
    return {"project": settings.project_id, "location": settings.location}
