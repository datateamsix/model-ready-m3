from __future__ import annotations

import pytest

from app.core.errors import ValidationBlockedError
from app.core.model_intent import DATASET_A_MODEL_INTENT, MODEL_READY_COLUMNS
from app.tools.bigquery_publish import consumption_load_job_config
from app.tools.schema_compiler import compile_model_consumption_schema, normalize_bq_type

DATASET_A_PHYSICAL_TYPES = {
    "time": "DATE",
    "geo": "STRING",
    "kpi_orders": "INT64",
    "kpi_revenue": "FLOAT64",
    "revenue_per_kpi": "FLOAT64",
    "population": "INT64",
    "paid_search_impressions": "INT64",
    "paid_search_spend": "FLOAT64",
    "shopping_impressions": "INT64",
    "shopping_spend": "FLOAT64",
    "paid_social_impressions": "INT64",
    "paid_social_spend": "FLOAT64",
    "organic_sessions": "INT64",
    "consumer_sentiment_index": "FLOAT64",
    "competitor_discount_index": "FLOAT64",
    "music_center_promo": "FLOAT64",
}


def test_dataset_a_schema_compiles_physical_types_partition_cluster_and_descriptions() -> None:
    schema = compile_model_consumption_schema(intent=DATASET_A_MODEL_INTENT)
    assert [field.name for field in schema.fields] == MODEL_READY_COLUMNS
    assert schema.partition_field == "time"
    assert schema.clustering_fields == ["geo"]
    assert {field.name: field.physical_type for field in schema.fields} == DATASET_A_PHYSICAL_TYPES
    assert all(field.description.strip() for field in schema.fields)
    ddl = schema.to_create_ddl("modelready-m3.modelready_models.model_input_demo")
    assert "PARTITION BY time" in ddl
    assert "CLUSTER BY geo" in ddl
    for field in schema.fields:
        assert f"{field.name} {field.physical_type}" in ddl
        assert "NOT NULL" in ddl
        assert "OPTIONS(description=" in ddl
        assert field.description.replace("'", "''") in ddl


def test_descriptions_compile_from_semantic_contract_not_a_column_dictionary() -> None:
    schema = compile_model_consumption_schema(intent=DATASET_A_MODEL_INTENT)
    spend = schema.field_map()["paid_search_spend"]
    impressions = schema.field_map()["paid_search_impressions"]
    assert spend.semantic_family == "media_spend"
    assert spend.physical_type == "FLOAT64"
    assert spend.description == "Paid Search media spend in USD at weekly geo grain."
    assert impressions.semantic_family == "media"
    assert impressions.description == "Paid Search media impressions at weekly geo grain."
    promo = schema.field_map()["music_center_promo"]
    assert promo.semantic_family == "controls"
    assert promo.description == "Control variable music_center_promo at weekly geo grain."
    grain = (
        f"{DATASET_A_MODEL_INTENT.canonical_time_grain.value} "
        f"{DATASET_A_MODEL_INTENT.model_scope.value} grain"
    )
    assert all(grain in field.description for field in schema.fields)
    with pytest.raises(ValidationBlockedError, match="fail closed"):
        compile_model_consumption_schema(
            intent=DATASET_A_MODEL_INTENT,
            columns=[*MODEL_READY_COLUMNS, "mystery_column"],
        )


def test_load_job_restates_partition_cluster_and_column_descriptions() -> None:
    schema = compile_model_consumption_schema(intent=DATASET_A_MODEL_INTENT)
    job = consumption_load_job_config(schema)
    assert job.time_partitioning is not None
    assert job.time_partitioning.field == "time"
    assert list(job.clustering_fields or []) == ["geo"]
    loaded = {field.name: field for field in job.schema}
    for field in schema.fields:
        assert loaded[field.name].description == field.description
        assert normalize_bq_type(loaded[field.name].field_type) == field.physical_type


def test_bq_integer_alias_normalizes_to_int64() -> None:
    assert normalize_bq_type("INTEGER") == "INT64"
    assert normalize_bq_type("FLOAT") == "FLOAT64"
    assert normalize_bq_type("DATE") == "DATE"
