"""Tests for the finder orchestration, filtering, ranking, and sources."""

import pytest

from leasefinder.finder import DealFilter, LeaseFinder
from leasefinder.sources.sample import SamplePriceSource, SampleResidualSource


def test_sample_sources_load():
    res = SampleResidualSource()
    prices = SamplePriceSource()
    vehicles = res.vehicles()
    assert len(vehicles) >= 5
    # Every vehicle has at least one program and a best price.
    for v in vehicles:
        assert res.programs_for(v), f"no programs for {v}"
        assert prices.best_price_for(v) is not None, f"no price for {v}"


def test_best_price_is_minimum():
    prices = SamplePriceSource()
    res = SampleResidualSource()
    civic = next(v for v in res.vehicles() if v.model == "Civic")
    quotes = prices.prices_for(civic)
    best = prices.best_price_for(civic)
    assert best.selling_price == min(q.selling_price for q in quotes)


def test_evaluate_all_builds_deals():
    finder = LeaseFinder()
    deals = finder.evaluate_all()
    assert deals
    for d in deals:
        assert d.quote.base_payment > 0
        assert "deal_score" in d.metrics


def test_default_sort_is_descending_score():
    finder = LeaseFinder()
    deals = finder.find_best_deals(sort="deal_score")
    scores = [d.metrics["deal_score"] for d in deals]
    assert scores == sorted(scores, reverse=True)


def test_sort_effective_monthly_ascending():
    finder = LeaseFinder()
    deals = finder.find_best_deals(sort="effective_monthly")
    vals = [d.metrics["effective_monthly"] for d in deals]
    assert vals == sorted(vals)


def test_top_truncates():
    finder = LeaseFinder()
    assert len(finder.find_best_deals(top=3)) == 3


def test_filter_by_body_style():
    finder = LeaseFinder()
    deals = finder.find_best_deals(deal_filter=DealFilter(body_style="SUV"))
    assert deals
    assert all(d.vehicle.body_style == "SUV" for d in deals)


def test_filter_by_max_payment():
    finder = LeaseFinder()
    deals = finder.find_best_deals(deal_filter=DealFilter(max_payment=400))
    assert all(d.quote.base_payment <= 400 for d in deals)


def test_filter_by_make_and_term():
    finder = LeaseFinder()
    deals = finder.find_best_deals(
        deal_filter=DealFilter(make="Honda", term=36)
    )
    assert deals
    assert all(d.vehicle.make == "Honda" and d.program.term == 36 for d in deals)


def test_unknown_sort_raises():
    finder = LeaseFinder()
    with pytest.raises(ValueError):
        finder.find_best_deals(sort="nonsense")


def test_tax_rate_increases_payment():
    no_tax = LeaseFinder(tax_rate=0.0).evaluate_all()[0]
    taxed = LeaseFinder(tax_rate=0.08).evaluate_all()[0]
    # Same first deal (deterministic order), taxed monthly payment is higher.
    assert taxed.quote.monthly_payment > no_tax.quote.monthly_payment
