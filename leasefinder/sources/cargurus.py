"""Selling-price adapter for CarGurus-style data.

──────────────────────────────────────────────────────────────────────────────
WHY THIS IS A DOCUMENTED STUB, NOT A SCRAPER
──────────────────────────────────────────────────────────────────────────────
CarGurus (https://www.cargurus.com/) shows current listing/transaction prices,
but it has no public API and uses anti-bot protection; scraping it is brittle
and against its Terms of Service.

This adapter defines the interface for a real price source and leaves data
acquisition to you, done compliantly. Reasonable options:

  1. A licensed automotive market-data / inventory feed (CarGurus and several
     vendors offer B2B data products).
  2. A dealer inventory feed you have permission to use.
  3. Prices you export/maintain yourself in a local CSV/JSON.

Populate ``prices_for`` from whichever you choose; the rest of the app is
unaffected.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..models import PriceQuote, Vehicle
from .base import PriceSource
from .sample import SamplePriceSource


class CarGurusPriceSource(PriceSource):
    """Skeleton for a real CarGurus-derived selling-price source.

    Parameters
    ----------
    data_path:
        Optional path to a local JSON/CSV of prices you maintain. If given, this
        behaves like the sample price source pointed at your file.
    api_key:
        Placeholder for a licensed feed's credential.
    """

    def __init__(self, data_path: Path | None = None, api_key: Optional[str] = None):
        self._api_key = api_key
        self._delegate = (
            SamplePriceSource(path=data_path) if data_path is not None else None
        )

    def prices_for(self, vehicle: Vehicle) -> List[PriceQuote]:
        if self._delegate is not None:
            return self._delegate.prices_for(vehicle)
        # A real implementation would query your licensed feed and map results:
        #
        #     listings = self._client.search(
        #         make=vehicle.make, model=vehicle.model, year=vehicle.year,
        #     )
        #     return [
        #         PriceQuote(
        #             vehicle_id=vehicle.vehicle_id,
        #             selling_price=listing["price"],
        #             dealer=listing["dealer_name"],
        #             location=listing["zip"],
        #             source="cargurus",
        #             url=listing["url"],
        #         )
        #         for listing in listings
        #     ]
        raise NotImplementedError(
            "Provide a `data_path` to a maintained price file, or implement "
            "prices_for() against your licensed market-data feed. See the module "
            "docstring for compliant options."
        )
