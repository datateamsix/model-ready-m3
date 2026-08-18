"""Public plan catalog contract tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.service.app import create_app
from app.service.catalog import build_plan_catalog
from tests.unit.stripe_support import PRICE_PROJECT, billing_config_for_tests


def test_plan_catalog_is_public() -> None:
    client = TestClient(create_app())
    response = client.get("/v1/catalog/plans")
    assert response.status_code == 200
    assert len(response.json()["plans"]) == 4


def test_planner_capacity_zero() -> None:
    _assert_capacity("planner", 0)


def test_project_capacity_one() -> None:
    _assert_capacity("project", 1)


def test_portfolio_capacity_ten() -> None:
    _assert_capacity("portfolio", 10)


def test_enterprise_capacity_fifty() -> None:
    _assert_capacity("enterprise", 50)


def _assert_capacity(plan_id: str, expected: int) -> None:
    client = TestClient(create_app())
    plans = {item["plan_id"]: item for item in client.get("/v1/catalog/plans").json()["plans"]}
    assert plans[plan_id]["max_active_projects"] == expected


def test_catalog_has_no_run_credit_balance() -> None:
    client = TestClient(create_app())
    payload = client.get("/v1/catalog/plans").text
    assert "run_balance" not in payload
    assert "dataset_runs_per_month" not in payload
    assert "credits" not in payload


def test_catalog_exposes_no_stripe_price_id() -> None:
    client = TestClient(create_app())
    payload = client.get("/v1/catalog/plans").text.lower()
    assert "price_" not in payload
    assert "stripe_price" not in payload


def test_catalog_does_not_invent_unconfigured_price() -> None:
    client = TestClient(create_app())
    for plan in client.get("/v1/catalog/plans").json()["plans"]:
        assert plan["display_price"] is None
        assert plan["amount"] is None
        assert plan["currency"] is None
        if plan["plan_id"] == "planner":
            assert plan["checkout_eligible"] is False
        else:
            assert plan["checkout_eligible"] is False


def test_configured_catalog_returns_backend_prices_without_provider_ids() -> None:
    config = billing_config_for_tests()
    app = create_app(plan_catalog=build_plan_catalog(config=config))
    payload = TestClient(app).get("/v1/catalog/plans")
    text = payload.text.lower()
    assert PRICE_PROJECT.lower() not in text
    assert "cus_" not in text
    plans = {item["plan_id"]: item for item in payload.json()["plans"]}
    assert plans["planner"]["checkout_eligible"] is False
    assert plans["project"]["checkout_eligible"] is True
    assert plans["project"]["amount"] == 9900
    assert plans["project"]["currency"] == "usd"
    assert plans["project"]["billing_interval"] == "month"
