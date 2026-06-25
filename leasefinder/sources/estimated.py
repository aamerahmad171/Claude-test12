"""A residual source that estimates lease programs from a depreciation model.

This is the headline alternative to Leasehackr: instead of needing the
proprietary residual % and money factor for every car, it reads a public
vehicle catalog (make/model/MSRP/body) and *generates* lease programs across a
grid of terms and mileages using ``leasefinder.residual_model``.

No network, no scraping, no licensed feed — just transparent estimates grounded
in published depreciation patterns. Numbers are clearly modeled, not real
manufacturer programs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

from ..models import LeaseProgram, PriceQuote, Vehicle
from ..residual_model import (
    DEFAULT_BASE_APR,
    estimate_money_factor,
    estimate_residual_percent,
)
from .base import PriceSource, ResidualSource

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

DEFAULT_TERMS: Sequence[int] = (24, 36, 48)
DEFAULT_MILEAGES: Sequence[int] = (10000, 12000, 15000)
DEFAULT_ACQUISITION_FEE = 695.0


class EstimatedResidualSource(ResidualSource):
    """Generate lease programs for a vehicle catalog via the depreciation model.

    Parameters
    ----------
    catalog_path:
        JSON catalog of vehicles (defaults to ``data/vehicle_catalog.json``).
    terms / mileages:
        The grid of lease programs to generate for each vehicle.
    base_apr:
        Rate-environment APR used to derive the money factor (MF = APR / 2400).
    acquisition_fee:
        Flat acquisition fee applied to every generated program.
    """

    def __init__(
        self,
        catalog_path: Path | None = None,
        *,
        terms: Sequence[int] = DEFAULT_TERMS,
        mileages: Sequence[int] = DEFAULT_MILEAGES,
        base_apr: float = DEFAULT_BASE_APR,
        acquisition_fee: float = DEFAULT_ACQUISITION_FEE,
    ):
        self._path = catalog_path or (DATA_DIR / "vehicle_catalog.json")
        self._terms = tuple(terms)
        self._mileages = tuple(mileages)
        self._base_apr = base_apr
        self._acquisition_fee = acquisition_fee

        with self._path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._vehicles = [
            Vehicle(
                make=v["make"],
                model=v["model"],
                year=v["year"],
                trim=v.get("trim", ""),
                body_style=v.get("body_style", ""),
                msrp=v["msrp"],
            )
            for v in raw["vehicles"]
        ]

    def vehicles(self) -> List[Vehicle]:
        return list(self._vehicles)

    def programs_for(self, vehicle: Vehicle) -> List[LeaseProgram]:
        money_factor = estimate_money_factor(self._base_apr)
        programs: List[LeaseProgram] = []
        for term in self._terms:
            for miles in self._mileages:
                residual = estimate_residual_percent(
                    vehicle.body_style, term, miles
                )
                programs.append(
                    LeaseProgram(
                        vehicle_id=vehicle.vehicle_id,
                        term=term,
                        annual_mileage=miles,
                        residual_percent=residual,
                        money_factor=money_factor,
                        incentives=0.0,
                        acquisition_fee=self._acquisition_fee,
                        source="estimated",
                    )
                )
        return programs


# Typical negotiated discount off MSRP by segment (a rough, public rule of thumb).
DISCOUNT_BY_SEGMENT = {
    "luxury": 0.07,
    "truck": 0.06,
    "sedan": 0.05,
    "suv": 0.05,
    "minivan": 0.05,
    "hatchback": 0.05,
    "coupe": 0.05,
    "sports": 0.04,
    "ev": 0.03,
}
DEFAULT_DISCOUNT = 0.05


class EstimatedPriceSource(PriceSource):
    """Estimate a selling price as MSRP minus a typical segment discount.

    Pairs with :class:`EstimatedResidualSource` so the app runs end-to-end with
    no price feed. Clearly modeled, not a real market quote — swap in
    :class:`~leasefinder.sources.marketcheck.MarketcheckPriceSource` (or a
    maintained file) for real prices.
    """

    def __init__(self, discount_by_segment: dict | None = None):
        self._discounts = discount_by_segment or DISCOUNT_BY_SEGMENT

    def prices_for(self, vehicle: Vehicle) -> List[PriceQuote]:
        if vehicle.msrp <= 0:
            return []
        discount = self._discounts.get(
            (vehicle.body_style or "").strip().lower(), DEFAULT_DISCOUNT
        )
        selling_price = round(vehicle.msrp * (1 - discount), 2)
        return [
            PriceQuote(
                vehicle_id=vehicle.vehicle_id,
                selling_price=selling_price,
                dealer="(estimated)",
                source="estimated",
            )
        ]
