"""Tests for the depreciation-based residual/money-factor model."""

import pytest

from leasefinder.lease_math import compute_lease, mf_to_apr
from leasefinder.residual_model import (
    MAX_RESIDUAL,
    MIN_RESIDUAL,
    estimate_money_factor,
    estimate_residual_percent,
)
from leasefinder.sources.estimated import (
    EstimatedPriceSource,
    EstimatedResidualSource,
)


def test_residual_falls_with_term():
    r24 = estimate_residual_percent("Sedan", 24, 12000)
    r36 = estimate_residual_percent("Sedan", 36, 12000)
    r48 = estimate_residual_percent("Sedan", 48, 12000)
    assert r24 > r36 > r48


def test_36mo_sedan_in_expected_band():
    # The model is anchored to reproduce the familiar ~58% for a 36-mo lease.
    assert estimate_residual_percent("Sedan", 36, 12000) == pytest.approx(0.58, abs=0.01)


def test_trucks_hold_value_better_than_evs():
    truck = estimate_residual_percent("Truck", 36, 12000)
    sedan = estimate_residual_percent("Sedan", 36, 12000)
    ev = estimate_residual_percent("EV", 36, 12000)
    assert truck > sedan > ev


def test_lower_mileage_raises_residual():
    lo = estimate_residual_percent("SUV", 36, 10000)
    mid = estimate_residual_percent("SUV", 36, 12000)
    hi = estimate_residual_percent("SUV", 36, 15000)
    assert lo > mid > hi


def test_residual_is_clamped():
    # Very long term + fast-depreciating segment + high miles stays in band.
    r = estimate_residual_percent("EV", 60, 15000)
    assert MIN_RESIDUAL <= r <= MAX_RESIDUAL


def test_money_factor_matches_apr():
    mf = estimate_money_factor(6.0)
    assert mf_to_apr(mf) == pytest.approx(6.0)


def test_estimated_source_generates_valid_programs():
    src = EstimatedResidualSource()
    vehicles = src.vehicles()
    assert len(vehicles) >= 10
    for v in vehicles:
        programs = src.programs_for(v)
        assert programs
        for p in programs:
            assert 0 < p.residual_percent <= 1
            assert p.money_factor >= 0
            assert p.source == "estimated"


def test_estimated_program_feeds_lease_math():
    src = EstimatedResidualSource()
    v = src.vehicles()[0]
    p = src.programs_for(v)[0]
    quote = compute_lease(
        msrp=v.msrp,
        selling_price=v.msrp * 0.95,
        residual_percent=p.residual_percent,
        money_factor=p.money_factor,
        term=p.term,
    )
    assert quote.base_payment > 0


def test_estimated_price_below_msrp():
    res = EstimatedResidualSource()
    prices = EstimatedPriceSource()
    for v in res.vehicles():
        quote = prices.best_price_for(v)
        assert quote is not None
        assert 0 < quote.selling_price < v.msrp
