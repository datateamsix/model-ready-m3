"""Environment-driven configuration for PreM3.

`M3_*` and `MODELREADY_*` environment variables are legacy/internal PreM3
execution configuration. Do not rename them solely for branding.

Infrastructure identifiers on Settings remain process-global. Customer identity
is request-scoped (`app.core.tenancy`) and is not derived from this module.

`MODELREADY_ORGANIZATION_ID` / `MODELREADY_WORKSPACE_ID` are developer/CLI
bootstrap inputs only (`app.core.developer_bootstrap`). They are not Settings
fields and never bind `require_tenant()` / `require_workspace()`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _apply_env_file() -> None:
    """Load repo `.env` into os.environ without overriding already-set variables."""
    candidates = (
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    )
    env_path = next((path for path in candidates if path.is_file()), None)
    if env_path is None:
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True, slots=True)
class Settings:
    project_id: str
    vertex_location: str
    cloud_region: str
    gemini_model: str
    agent_name: str
    raw_bucket: str | None
    artifact_bucket: str | None
    bq_ops_dataset: str
    bq_experience_dataset: str
    bq_models_dataset: str
    environment: str
    log_level: str
    runtime_sa: str | None
    cloud_run_service: str | None
    eda_job: str | None
    eda_job_timeout_seconds: int
    domain_view_registry_gs_uri: str | None


def load_settings() -> Settings:
    """Load runtime settings without hard-coding cloud resource identifiers.

    GOOGLE_CLOUD_LOCATION is the Vertex AI / Gemini endpoint (often `global`).
    GOOGLE_CLOUD_REGION is Cloud Run / GCS / BigQuery regional infrastructure.
    """
    _apply_env_file()
    return Settings(
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT", "modelready-m3"),
        vertex_location=os.getenv("GOOGLE_CLOUD_LOCATION", "global"),
        cloud_region=os.getenv("GOOGLE_CLOUD_REGION", "us-central1"),
        gemini_model=os.getenv("M3_GEMINI_MODEL", "gemini-2.5-flash"),
        agent_name=os.getenv("M3_AGENT_NAME", "modelready_m3"),
        raw_bucket=os.getenv("MODELREADY_RAW_BUCKET") or None,
        artifact_bucket=os.getenv("MODELREADY_ARTIFACT_BUCKET") or None,
        bq_ops_dataset=os.getenv("MODELREADY_BQ_OPS_DATASET", "modelready_ops"),
        bq_experience_dataset=os.getenv(
            "MODELREADY_BQ_EXPERIENCE_DATASET", "modelready_experience"
        ),
        bq_models_dataset=os.getenv("MODELREADY_BQ_MODELS_DATASET", "modelready_models"),
        environment=os.getenv("MODELREADY_ENV", "dev"),
        log_level=os.getenv("MODELREADY_LOG_LEVEL", "INFO"),
        runtime_sa=os.getenv("M3_RUNTIME_SA") or None,
        cloud_run_service=os.getenv("MODELREADY_CLOUD_RUN_SERVICE") or None,
        eda_job=os.getenv("MODELREADY_EDA_JOB") or None,
        eda_job_timeout_seconds=int(os.getenv("MODELREADY_EDA_JOB_TIMEOUT", "3300")),
        domain_view_registry_gs_uri=os.getenv("MODELREADY_DOMAIN_VIEW_REGISTRY_GS_URI")
        or None,
    )


settings = load_settings()
