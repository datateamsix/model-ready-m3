"""BigQuery client helpers."""

from google.cloud import bigquery

from app.config import settings


def get_bigquery_client() -> bigquery.Client:
    return bigquery.Client(project=settings.project_id)
