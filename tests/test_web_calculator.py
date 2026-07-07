"""Tests for the standalone lease calculator page and its JSON API."""

import pytest

from leasefinder.lease_math import compute_lease
from leasefinder.web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_calculator_page_renders(client):
    resp = client.get("/calculator")
    assert resp.status_code == 200
    assert b"Lease Calculator" in resp.data


def test_api_calculate_matches_core_formula(client):
    resp = client.get(
        "/api/calculate",
        query_string={
            "msrp": 45000,
            "selling_price": 42000,
            "residual_percent": 0.58,
            "money_factor": 0.00125,
            "term": 36,
            "incentives": 1500,
            "down_payment": 2000,
            "trade_in": 500,
            "acquisition_fee": 895,
            "upfront_fees": 300,
            "tax_rate": 0.07,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()

    expected = compute_lease(
        msrp=45000,
        selling_price=42000,
        residual_percent=0.58,
        money_factor=0.00125,
        term=36,
        cap_cost_reduction=2500,
        rebates=1500,
        capitalized_fees=895,
        upfront_fees=300,
        tax_rate=0.07,
    )

    assert data["base_payment"] == pytest.approx(expected.base_payment)
    assert data["monthly_payment"] == pytest.approx(expected.monthly_payment)
    assert data["due_at_signing"] == pytest.approx(expected.due_at_signing)
    assert data["total_cost"] == pytest.approx(expected.total_cost)
    assert data["effective_monthly"] == pytest.approx(expected.effective_monthly)
    assert data["one_percent"] == pytest.approx(
        expected.base_payment / expected.msrp * 100
    )

    das = data["due_at_signing_breakdown"]
    assert das["down_payment"] == pytest.approx(2000)
    assert das["trade_in"] == pytest.approx(500)
    assert das["upfront_fees"] == pytest.approx(300)
    assert das["first_month_payment"] == pytest.approx(expected.monthly_payment)


def test_api_calculate_apr_matches_equivalent_money_factor(client):
    apr_resp = client.get(
        "/api/calculate",
        query_string={
            "msrp": 40000,
            "selling_price": 38000,
            "residual_percent": 0.55,
            "apr": 3.0,
            "term": 36,
        },
    )
    mf_resp = client.get(
        "/api/calculate",
        query_string={
            "msrp": 40000,
            "selling_price": 38000,
            "residual_percent": 0.55,
            "money_factor": 0.00125,
            "term": 36,
        },
    )
    assert apr_resp.get_json()["monthly_payment"] == pytest.approx(
        mf_resp.get_json()["monthly_payment"]
    )


def test_api_calculate_rejects_missing_required_field(client):
    resp = client.get(
        "/api/calculate",
        query_string={"selling_price": 42000, "residual_percent": 0.58, "term": 36},
    )
    assert resp.status_code == 400
    assert "msrp" in resp.get_json()["error"]


def test_api_calculate_rejects_invalid_residual(client):
    resp = client.get(
        "/api/calculate",
        query_string={
            "msrp": 40000,
            "selling_price": 38000,
            "residual_percent": 1.5,
            "money_factor": 0.001,
            "term": 36,
        },
    )
    assert resp.status_code == 400
