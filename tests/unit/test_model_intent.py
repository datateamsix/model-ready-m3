import pytest

from app.core.errors import ValidationBlockedError
from app.core.model_intent import DATASET_A_MODEL_INTENT, ModelIntent, load_model_intent


def test_dataset_a_intent_identifies_kpi_and_scope() -> None:
    intent = DATASET_A_MODEL_INTENT
    assert intent.kpi.canonical_field == "kpi_orders"
    assert intent.revenue.canonical_field == "kpi_revenue"
    assert intent.model_scope.value == "geo"
    assert intent.canonical_time_grain.value == "weekly"
    assert intent.population is not None
    assert intent.population.field == "population"


def test_invalid_intent_is_blocked() -> None:
    payload = DATASET_A_MODEL_INTENT.model_dump(mode="json")
    payload["kpi"]["canonical_field"] = payload["revenue"]["canonical_field"]
    with pytest.raises(ValidationBlockedError):
        load_model_intent(payload)


def test_geo_intent_without_population_is_blocked() -> None:
    payload = DATASET_A_MODEL_INTENT.model_dump(mode="json")
    payload["population"] = None
    with pytest.raises(ValidationBlockedError):
        load_model_intent(payload)


def test_daily_grain_is_blocked_for_phase1() -> None:
    payload = DATASET_A_MODEL_INTENT.model_dump(mode="json")
    payload["canonical_time_grain"] = "daily"
    with pytest.raises(ValidationBlockedError):
        load_model_intent(payload)


def test_model_intent_rejects_unknown_fields_quietly_via_validation() -> None:
    with pytest.raises(Exception):
        ModelIntent.model_validate({"target": "not_a_model"})
