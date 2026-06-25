"""Data-source interfaces.

The rest of the app only ever talks to these two abstract interfaces, so any
provider — the bundled offline sample data, a licensed feed, a CSV export, or
your own compliant fetcher — is a drop-in replacement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from ..models import LeaseProgram, PriceQuote, Vehicle


class ResidualSource(ABC):
    """Provides vehicles and their lease programs (residual % + money factor).

    This is the "Leasehackr calculator inputs" side of the app: the residual
    value and money factor are exactly what that calculator needs to turn an
    MSRP into a payment.
    """

    @abstractmethod
    def vehicles(self) -> List[Vehicle]:
        """All vehicles this source knows about."""

    @abstractmethod
    def programs_for(self, vehicle: Vehicle) -> List[LeaseProgram]:
        """Available lease programs (term / mileage variants) for a vehicle."""


class PriceSource(ABC):
    """Provides current selling prices for vehicles (the CarGurus side)."""

    @abstractmethod
    def prices_for(self, vehicle: Vehicle) -> List[PriceQuote]:
        """Current market selling prices for a vehicle (possibly several dealers)."""

    def best_price_for(self, vehicle: Vehicle) -> PriceQuote | None:
        """Lowest available selling price for a vehicle, or ``None`` if unknown."""
        quotes: Iterable[PriceQuote] = self.prices_for(vehicle)
        quotes = list(quotes)
        if not quotes:
            return None
        return min(quotes, key=lambda q: q.selling_price)
