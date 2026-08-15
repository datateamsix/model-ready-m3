"""Environment-driven configuration for ModelReady/M3."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Settings:
    project_id: str
    location: str
    gemini_model: str
    agent_name: str
    organization_id: str
    workspace_id: str
    raw_bucket: str | None
    artifact_bucket: str | None
    bq_ops_dataset: str
    bq_experience_dataset: str
    bq_models_dataset: str
    environment: str
    log_level: str


def load_settings() -> Settings:
    """Load runtime settings without hard-coding cloud resource identifiers."""
    return Settings(
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT", "model-ready-m3"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        gemini_model=os.getenv("M3_GEMINI_MODEL", "gemini-flash-latest"),
        agent_name=os.getenv("M3_AGENT_NAME", "modelready_m3"),
        organization_id=os.getenv("MODELREADY_ORGANIZATION_ID", "music-center"),
        workspace_id=os.getenv("MODELREADY_WORKSPACE_ID", "mmm-demo"),
        raw_bucket=os.getenv("MODELREADY_RAW_BUCKET") or None,
        artifact_bucket=os.getenv("MODELREADY_ARTIFACT_BUCKET") or None,
        bq_ops_dataset=os.getenv("MODELREADY_BQ_OPS_DATASET", "modelready_ops"),
        bq_experience_dataset=os.getenv(
            "MODELREADY_BQ_EXPERIENCE_DATASET", "modelready_experience"
        ),
        bq_models_dataset=os.getenv("MODELREADY_BQ_MODELS_DATASET", "modelready_models"),
        environment=os.getenv("MODELREADY_ENV", "dev"),
        log_level=os.getenv("MODELREADY_LOG_LEVEL", "INFO"),
    )


settings = load_settings()
