"""Domain models shared across the app.

These dataclasses are the common language between data sources, the lease engine,
and the scoring/ranking layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .lease_math import LeaseQuote


@dataclass(frozen=True)
class Vehicle:
    """A specific car trim that can be leased."""

    make: str
    model: str
    year: int
    trim: str = ""
    body_style: str = ""   # e.g. "Sedan", "SUV", "Truck", "EV"
    msrp: float = 0.0

    @property
    def vehicle_id(self) -> str:
        parts = [str(self.year), self.make, self.model, self.trim]
        return " ".join(p for p in parts if p).strip()

    def __str__(self) -> str:
        return self.vehicle_id


@dataclass(frozen=True)
class LeaseProgram:
    """Manufacturer lease terms for a vehicle — the Leasehackr-style inputs.

    A single vehicle usually has several programs (different terms / mileages).
    """

    vehicle_id: str
    term: int                 # months
    annual_mileage: int       # e.g. 10000, 12000, 15000
    residual_percent: float   # fraction of MSRP, e.g. 0.60
    money_factor: float
    incentives: float = 0.0   # manufacturer rebates / lease cash (cap reduction)
    acquisition_fee: float = 0.0
    source: str = "unknown"   # provenance, e.g. "leasehackr", "sample"


@dataclass(frozen=True)
class PriceQuote:
    """A current selling price for a vehicle — the CarGurus-style input.

    A ``vin`` identifies one *specific physical car* on a lot, so it is only
    known for real-inventory sources (Marketcheck, a maintained quote file).
    Modeled/archetype rows leave it blank.
    """

    vehicle_id: str
    selling_price: float
    dealer: str = ""
    location: str = ""
    source: str = "unknown"   # provenance, e.g. "cargurus", "sample"
    url: str = ""
    vin: str = ""


@dataclass
class LeaseDeal:
    """A fully evaluated lease: vehicle + program + price + computed economics."""

    vehicle: Vehicle
    program: LeaseProgram
    price: PriceQuote
    quote: LeaseQuote
    metrics: dict = field(default_factory=dict)

    @property
    def deal_score(self) -> float:
        return float(self.metrics.get("deal_score", 0.0))

    def summary(self) -> str:
        q = self.quote
        return (
            f"{self.vehicle}  |  ${q.base_payment:,.0f}/mo "
            f"(${self.quote.effective_monthly:,.0f} effective)  "
            f"| {q.term}mo / {self.program.annual_mileage // 1000}k  "
            f"| 1%={self.metrics.get('one_percent', 0):.2f}%  "
            f"| score {self.deal_score:.0f}"
        )
