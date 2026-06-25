"""Core lease math.

This is the same depreciation + rent-charge formula used by the Leasehackr
calculator and every other standard lease calculator. It is pure (no I/O, no
external state) and fully covered by tests against hand-worked examples.

Glossary
--------
MSRP                Manufacturer's suggested retail price (sticker).
selling_price       The negotiated price of the car ("cap cost" before fees).
residual_percent    Fraction of MSRP the car is worth at lease end (e.g. 0.60).
money_factor        The lease's finance rate in MF form. APR = MF * 2400.
term                Lease length in months.
cap_cost_reduction  Cash + rebates applied up front to lower the cap cost.
capitalized_fees    Fees rolled into the loan (e.g. acquisition fee).
upfront_fees        Fees paid at signing but NOT financed (e.g. doc, first reg).
tax_rate            Sales-tax rate applied to the monthly payment (most states).
"""

from __future__ import annotations

from dataclasses import dataclass

# Conventional constant: money factor * 2400 == APR percentage.
MF_TO_APR = 2400.0


def mf_to_apr(money_factor: float) -> float:
    """Convert a money factor to an APR percentage (0.00125 -> 3.0)."""
    return money_factor * MF_TO_APR


def apr_to_mf(apr_percent: float) -> float:
    """Convert an APR percentage to a money factor (3.0 -> 0.00125)."""
    return apr_percent / MF_TO_APR


@dataclass(frozen=True)
class LeaseQuote:
    """The fully computed economics of a single lease."""

    msrp: float
    selling_price: float
    residual_value: float
    residual_percent: float
    money_factor: float
    apr: float
    term: int

    adjusted_cap_cost: float
    monthly_depreciation: float
    monthly_rent_charge: float
    base_payment: float          # pre-tax monthly payment
    monthly_tax: float
    monthly_payment: float       # base_payment + monthly_tax

    due_at_signing: float        # cash needed on day one
    total_cost: float            # everything you pay over the whole lease
    effective_monthly: float     # total_cost / term (the apples-to-apples number)


def compute_lease(
    *,
    msrp: float,
    selling_price: float,
    residual_percent: float,
    money_factor: float,
    term: int,
    cap_cost_reduction: float = 0.0,
    rebates: float = 0.0,
    capitalized_fees: float = 0.0,
    upfront_fees: float = 0.0,
    tax_rate: float = 0.0,
    first_payment_due_at_signing: bool = True,
) -> LeaseQuote:
    """Compute the full economics of a lease.

    ``cap_cost_reduction`` is the customer's own cash down, while ``rebates`` is
    manufacturer lease cash / incentives. Both lower the cap cost (and therefore
    the monthly payment), but only the customer's cash counts toward
    due-at-signing and the effective monthly cost — a $7,500 rebate is not money
    out of your pocket.

    The tax model here is the common "tax on the monthly payment" method used by
    most US states. States that tax the full selling price or the cap-cost
    reduction differ; those can be modeled by folding the tax into
    ``upfront_fees`` or ``capitalized_fees``.

    Raises
    ------
    ValueError
        If inputs are economically nonsensical (non-positive term/MSRP, negative
        prices, residual percent outside (0, 1]).
    """
    if term <= 0:
        raise ValueError(f"term must be positive, got {term}")
    if msrp <= 0:
        raise ValueError(f"msrp must be positive, got {msrp}")
    if selling_price < 0:
        raise ValueError(f"selling_price must be non-negative, got {selling_price}")
    if not 0 < residual_percent <= 1:
        raise ValueError(
            f"residual_percent must be in (0, 1], got {residual_percent}"
        )
    if money_factor < 0:
        raise ValueError(f"money_factor must be non-negative, got {money_factor}")
    if cap_cost_reduction < 0:
        raise ValueError(
            f"cap_cost_reduction must be non-negative, got {cap_cost_reduction}"
        )
    if rebates < 0:
        raise ValueError(f"rebates must be non-negative, got {rebates}")

    residual_value = msrp * residual_percent

    # Gross cap cost is the price plus financed fees; both the customer's cash
    # down and the manufacturer rebates lower it.
    adjusted_cap_cost = (
        selling_price + capitalized_fees - cap_cost_reduction - rebates
    )

    monthly_depreciation = (adjusted_cap_cost - residual_value) / term
    monthly_rent_charge = (adjusted_cap_cost + residual_value) * money_factor
    base_payment = monthly_depreciation + monthly_rent_charge

    monthly_tax = base_payment * tax_rate
    monthly_payment = base_payment + monthly_tax

    # Cash on day one: the up-front reduction, non-financed fees, and (usually)
    # the first month's payment.
    due_at_signing = cap_cost_reduction + upfront_fees
    if first_payment_due_at_signing:
        due_at_signing += monthly_payment

    # Total cost over the lease. The first payment, if collected at signing, is
    # already inside `due_at_signing`, so only (term - 1) further payments remain
    # to avoid double counting.
    remaining_payments = term - 1 if first_payment_due_at_signing else term
    total_cost = due_at_signing + monthly_payment * remaining_payments

    effective_monthly = total_cost / term

    return LeaseQuote(
        msrp=msrp,
        selling_price=selling_price,
        residual_value=residual_value,
        residual_percent=residual_percent,
        money_factor=money_factor,
        apr=mf_to_apr(money_factor),
        term=term,
        adjusted_cap_cost=adjusted_cap_cost,
        monthly_depreciation=monthly_depreciation,
        monthly_rent_charge=monthly_rent_charge,
        base_payment=base_payment,
        monthly_tax=monthly_tax,
        monthly_payment=monthly_payment,
        due_at_signing=due_at_signing,
        total_cost=total_cost,
        effective_monthly=effective_monthly,
    )
