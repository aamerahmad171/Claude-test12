"""Tests for the scoring/metrics layer."""

import pytest

from leasefinder.lease_math import compute_lease
from leasefinder.scoring import (
    compute_metrics,
    deal_score,
    discount_percent,
    effective_one_percent_ratio,
    one_percent_ratio,
)


def _quote(**overrides):
    base = dict(
        msrp=40000, selling_price=37000, residual_percent=0.58,
        money_factor=0.0015, term=36,
    )
    base.update(overrides)
    return compute_lease(**base)


def test_one_percent_ratio_is_percent_of_msrp():
    q = _quote()
    assert one_percent_ratio(q) == pytest.approx(q.base_payment / q.msrp * 100)


def test_effective_one_percent_uses_effective_monthly():
    q = _quote()
    assert effective_one_percent_ratio(q) == pytest.approx(
        q.effective_monthly / q.msrp * 100
    )


def test_discount_percent():
    q = _quote(selling_price=34000)  # 6000 off 40000 = 15%
    assert discount_percent(q) == pytest.approx(15.0)


def test_deal_score_in_range():
    q = _quote()
    s = deal_score(q)
    assert 0 <= s <= 100


def test_better_price_scores_higher():
    cheap = _quote(selling_price=33000)
    pricey = _quote(selling_price=39500)
    assert deal_score(cheap) > deal_score(pricey)


def test_lower_money_factor_scores_higher():
    low_mf = _quote(money_factor=0.0008)
    high_mf = _quote(money_factor=0.0030)
    assert deal_score(low_mf) > deal_score(high_mf)


def test_big_down_payment_does_not_inflate_score():
    # Cash down lowers monthly but the score should not reward it (cash + cost
    # components both account for it).
    no_down = _quote()
    big_down = _quote(cap_cost_reduction=5000)
    assert deal_score(big_down) <= deal_score(no_down) + 1


def test_compute_metrics_keys():
    m = compute_metrics(_quote())
    for key in [
        "base_payment", "monthly_payment", "effective_monthly", "due_at_signing",
        "total_cost", "apr", "one_percent", "effective_one_percent",
        "discount_percent", "deal_score",
    ]:
        assert key in m
