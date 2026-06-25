"""Orchestration: combine sources, evaluate every candidate, rank the results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from .lease_math import compute_lease
from .models import LeaseDeal, Vehicle
from .scoring import compute_metrics
from .sources.base import PriceSource, ResidualSource
from .sources.sample import SamplePriceSource, SampleResidualSource

# How each sort key orders deals. ``True`` means "smaller is better".
SORT_KEYS = {
    "deal_score": ("deal_score", False),
    "effective_monthly": ("effective_monthly", True),
    "base_payment": ("base_payment", True),
    "one_percent": ("one_percent", True),
    "effective_one_percent": ("effective_one_percent", True),
    "due_at_signing": ("due_at_signing", True),
    "total_cost": ("total_cost", True),
}


@dataclass
class DealFilter:
    """Optional constraints applied before ranking."""

    make: Optional[str] = None
    body_style: Optional[str] = None
    term: Optional[int] = None
    annual_mileage: Optional[int] = None
    max_payment: Optional[float] = None        # on base monthly payment
    max_due_at_signing: Optional[float] = None
    max_msrp: Optional[float] = None

    def matches(self, deal: LeaseDeal) -> bool:
        v, p, q = deal.vehicle, deal.program, deal.quote
        if self.make and v.make.lower() != self.make.lower():
            return False
        if self.body_style and v.body_style.lower() != self.body_style.lower():
            return False
        if self.term is not None and p.term != self.term:
            return False
        if self.annual_mileage is not None and p.annual_mileage != self.annual_mileage:
            return False
        if self.max_payment is not None and q.base_payment > self.max_payment:
            return False
        if self.max_due_at_signing is not None and q.due_at_signing > self.max_due_at_signing:
            return False
        if self.max_msrp is not None and v.msrp > self.max_msrp:
            return False
        return True


class LeaseFinder:
    """Evaluates and ranks lease deals across all known vehicles/programs/prices.

    Parameters
    ----------
    residual_source:
        Supplies vehicles and their lease programs (residual % + money factor).
        Defaults to the bundled offline sample data.
    price_source:
        Supplies current selling prices. Defaults to the bundled sample data.
    tax_rate:
        Sales-tax rate applied to the monthly payment (e.g. 0.0625). The lease
        math defaults to 0 so payments are comparable across states unless you
        opt in.
    upfront_fees:
        Non-financed fees paid at signing (doc fee, first registration, etc.).
    """

    def __init__(
        self,
        residual_source: Optional[ResidualSource] = None,
        price_source: Optional[PriceSource] = None,
        *,
        tax_rate: float = 0.0,
        upfront_fees: float = 0.0,
    ):
        self.residual_source = residual_source or SampleResidualSource()
        self.price_source = price_source or SamplePriceSource()
        self.tax_rate = tax_rate
        self.upfront_fees = upfront_fees

    def evaluate_all(self) -> List[LeaseDeal]:
        """Build a LeaseDeal for every (vehicle, program, best price) combo."""
        deals: List[LeaseDeal] = []
        for vehicle in self.residual_source.vehicles():
            best_price = self.price_source.best_price_for(vehicle)
            if best_price is None:
                # No current selling price -> can't compute a real deal.
                continue
            for program in self.residual_source.programs_for(vehicle):
                deal = self._build_deal(vehicle, program, best_price)
                deals.append(deal)
        return deals

    def find_best_deals(
        self,
        *,
        top: Optional[int] = None,
        sort: str = "deal_score",
        deal_filter: Optional[DealFilter] = None,
        predicate: Optional[Callable[[LeaseDeal], bool]] = None,
    ) -> List[LeaseDeal]:
        """Return ranked deals, optionally filtered and truncated to ``top``."""
        if sort not in SORT_KEYS:
            raise ValueError(
                f"unknown sort key {sort!r}; choose from {sorted(SORT_KEYS)}"
            )

        deals = self.evaluate_all()
        if deal_filter is not None:
            deals = [d for d in deals if deal_filter.matches(d)]
        if predicate is not None:
            deals = [d for d in deals if predicate(d)]

        metric_key, ascending = SORT_KEYS[sort]
        deals.sort(key=lambda d: d.metrics[metric_key], reverse=not ascending)

        if top is not None:
            deals = deals[:top]
        return deals

    def _build_deal(self, vehicle: Vehicle, program, price) -> LeaseDeal:
        quote = compute_lease(
            msrp=vehicle.msrp,
            selling_price=price.selling_price,
            residual_percent=program.residual_percent,
            money_factor=program.money_factor,
            term=program.term,
            rebates=program.incentives,
            capitalized_fees=program.acquisition_fee,
            upfront_fees=self.upfront_fees,
            tax_rate=self.tax_rate,
        )
        return LeaseDeal(
            vehicle=vehicle,
            program=program,
            price=price,
            quote=quote,
            metrics=compute_metrics(quote),
        )
