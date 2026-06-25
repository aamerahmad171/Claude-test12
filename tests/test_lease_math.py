"""Tests for the core lease formula against hand-worked examples."""

import math

import pytest

from leasefinder.lease_math import (
    apr_to_mf,
    compute_lease,
    mf_to_apr,
)


def test_mf_apr_roundtrip():
    assert mf_to_apr(0.00125) == pytest.approx(3.0)
    assert apr_to_mf(3.0) == pytest.approx(0.00125)


def test_worked_example_no_down_no_tax():
    # MSRP 50,000; sell 47,000; residual 60% -> 30,000; MF 0.00125; 36 mo;
    # acquisition fee 895 capitalized; no down, no tax.
    q = compute_lease(
        msrp=50000,
        selling_price=47000,
        residual_percent=0.60,
        money_factor=0.00125,
        term=36,
        capitalized_fees=895,
    )
    assert q.residual_value == pytest.approx(30000)
    assert q.adjusted_cap_cost == pytest.approx(47895)
    # depreciation = (47895 - 30000) / 36
    assert q.monthly_depreciation == pytest.approx(17895 / 36)
    # rent = (47895 + 30000) * 0.00125
    assert q.monthly_rent_charge == pytest.approx(77895 * 0.00125)
    assert q.base_payment == pytest.approx(17895 / 36 + 77895 * 0.00125)
    assert q.monthly_tax == 0
    assert q.monthly_payment == pytest.approx(q.base_payment)
    assert q.apr == pytest.approx(3.0)


def test_cap_cost_reduction_lowers_payment():
    base = compute_lease(
        msrp=40000, selling_price=38000, residual_percent=0.55,
        money_factor=0.0015, term=36,
    )
    with_down = compute_lease(
        msrp=40000, selling_price=38000, residual_percent=0.55,
        money_factor=0.0015, term=36, cap_cost_reduction=3000,
    )
    assert with_down.base_payment < base.base_payment
    # But due-at-signing is higher because of the cash down.
    assert with_down.due_at_signing > base.due_at_signing


def test_effective_monthly_amortizes_down_payment():
    # A big down payment lowers the monthly but should NOT make the effective
    # monthly dramatically better — that's the whole point of the metric.
    no_down = compute_lease(
        msrp=40000, selling_price=38000, residual_percent=0.55,
        money_factor=0.0015, term=36,
    )
    big_down = compute_lease(
        msrp=40000, selling_price=38000, residual_percent=0.55,
        money_factor=0.0015, term=36, cap_cost_reduction=5000,
    )
    assert big_down.effective_monthly == pytest.approx(
        no_down.effective_monthly, abs=15.0
    )


def test_rebate_lowers_payment_but_not_due_at_signing():
    # Manufacturer rebate reduces the monthly payment (it lowers the cap cost)
    # but is NOT customer cash, so it must not inflate due-at-signing or the
    # effective monthly the way a cash down payment would.
    no_rebate = compute_lease(
        msrp=43000, selling_price=41000, residual_percent=0.55,
        money_factor=0.0015, term=36,
    )
    rebate = compute_lease(
        msrp=43000, selling_price=41000, residual_percent=0.55,
        money_factor=0.0015, term=36, rebates=7500,
    )
    assert rebate.base_payment < no_rebate.base_payment
    # Due-at-signing only moves by the (now smaller) first payment, not by $7,500.
    assert rebate.due_at_signing < no_rebate.due_at_signing
    assert rebate.effective_monthly < no_rebate.effective_monthly


def test_rebate_vs_cash_down_differ_at_signing():
    # Same cap-cost reduction amount: as a rebate it costs nothing up front; as
    # cash down it's all out of pocket.
    as_rebate = compute_lease(
        msrp=40000, selling_price=38000, residual_percent=0.55,
        money_factor=0.0015, term=36, rebates=3000,
    )
    as_cash = compute_lease(
        msrp=40000, selling_price=38000, residual_percent=0.55,
        money_factor=0.0015, term=36, cap_cost_reduction=3000,
    )
    assert as_rebate.base_payment == pytest.approx(as_cash.base_payment)
    assert as_rebate.due_at_signing < as_cash.due_at_signing
    assert as_rebate.effective_monthly < as_cash.effective_monthly


def test_tax_on_payment_applied():
    q = compute_lease(
        msrp=30000, selling_price=29000, residual_percent=0.6,
        money_factor=0.001, term=36, tax_rate=0.10,
    )
    assert q.monthly_tax == pytest.approx(q.base_payment * 0.10)
    assert q.monthly_payment == pytest.approx(q.base_payment * 1.10)


def test_total_cost_consistency_first_payment_at_signing():
    q = compute_lease(
        msrp=30000, selling_price=29000, residual_percent=0.6,
        money_factor=0.001, term=36,
    )
    # total = due_at_signing + (term - 1) further payments
    expected = q.due_at_signing + q.monthly_payment * (36 - 1)
    assert q.total_cost == pytest.approx(expected)
    assert q.effective_monthly == pytest.approx(q.total_cost / 36)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"term": 0},
        {"msrp": 0},
        {"residual_percent": 0},
        {"residual_percent": 1.5},
        {"selling_price": -1},
        {"money_factor": -0.001},
    ],
)
def test_invalid_inputs_raise(kwargs):
    base = dict(
        msrp=30000, selling_price=29000, residual_percent=0.6,
        money_factor=0.001, term=36,
    )
    base.update(kwargs)
    with pytest.raises(ValueError):
        compute_lease(**base)
