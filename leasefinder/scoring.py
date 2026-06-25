"""Deal scoring and ranking.

Three layers of metric, from most standard to most opinionated:

1. ``one_percent`` — the industry-standard **1% rule**: a lease whose pre-tax
   monthly payment is <= 1% of MSRP is considered a strong deal.
2. ``effective_one_percent`` — the same idea but using the effective monthly
   (which folds in all due-at-signing cash), so big down payments can't hide a
   weak deal.
3. ``deal_score`` — OUR OWN transparent composite (0–100, higher is better). It
   is **not** the proprietary Leasehackr Score; it's defined entirely below so
   you can tune or replace it.
"""

from __future__ import annotations

from .lease_math import LeaseQuote


def one_percent_ratio(quote: LeaseQuote) -> float:
    """Pre-tax monthly payment as a percentage of MSRP (the 1% rule)."""
    return quote.base_payment / quote.msrp * 100.0


def effective_one_percent_ratio(quote: LeaseQuote) -> float:
    """Effective monthly payment as a percentage of MSRP."""
    return quote.effective_monthly / quote.msrp * 100.0


def discount_percent(quote: LeaseQuote) -> float:
    """How far below MSRP the car was bought (a proxy for negotiation)."""
    if quote.msrp <= 0:
        return 0.0
    return (quote.msrp - quote.selling_price) / quote.msrp * 100.0


def deal_score(quote: LeaseQuote) -> float:
    """A transparent 0–100 composite score (higher = better deal).

    Built from three normalized components:

    * **Effective cost (60%)** — the heart of it. We map the effective 1%
      ratio onto a 0–100 band where 0.7% (excellent) -> 100 and 1.6% (poor)
      -> 0.
    * **Up-front cash (20%)** — rewards low money-down deals. Due-at-signing of
      $0 -> full credit; a full one-payment-equivalent or more -> no credit.
    * **Discount off MSRP (20%)** — rewards a well-negotiated selling price.
      0% off -> 0; >=15% off -> full credit.

    These weights and bands are deliberately simple and easy to change.
    """
    eff_pct = effective_one_percent_ratio(quote)
    # 0.7% -> 1.0, 1.6% -> 0.0, clamped.
    cost_component = _clamp((1.6 - eff_pct) / (1.6 - 0.7))

    # Express due-at-signing in "months of payment" so it's MSRP-independent.
    months_down = (
        quote.due_at_signing / quote.base_payment if quote.base_payment > 0 else 0.0
    )
    # 0 months down -> 1.0, 3+ months down -> 0.0.
    cash_component = _clamp((3.0 - months_down) / 3.0)

    disc = discount_percent(quote)
    discount_component = _clamp(disc / 15.0)

    score = (
        0.60 * cost_component
        + 0.20 * cash_component
        + 0.20 * discount_component
    ) * 100.0
    return round(score, 1)


def compute_metrics(quote: LeaseQuote) -> dict:
    """Bundle all the comparison metrics for a quote into one dict."""
    return {
        "base_payment": round(quote.base_payment, 2),
        "monthly_payment": round(quote.monthly_payment, 2),
        "effective_monthly": round(quote.effective_monthly, 2),
        "due_at_signing": round(quote.due_at_signing, 2),
        "total_cost": round(quote.total_cost, 2),
        "apr": round(quote.apr, 2),
        "one_percent": round(one_percent_ratio(quote), 3),
        "effective_one_percent": round(effective_one_percent_ratio(quote), 3),
        "discount_percent": round(discount_percent(quote), 2),
        "deal_score": deal_score(quote),
    }


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))
