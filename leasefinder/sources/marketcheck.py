"""Real selling-price source backed by the Marketcheck API.

Marketcheck (https://www.marketcheck.com/apis) aggregates live dealer
inventory from thousands of sites and offers a **free tier with a signup API
key** — a clean, structured, ToS-friendly alternative to scraping CarGurus.

Usage::

    from leasefinder.sources.marketcheck import MarketcheckPriceSource
    prices = MarketcheckPriceSource(api_key="YOUR_KEY")

This is a real implementation (stdlib HTTP, no extra deps). It needs network
access and a key, so it cannot run inside a sandbox with blocked egress — but it
works anywhere with internet. Without a key it raises a clear error.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import List, Optional

from ..models import PriceQuote, Vehicle
from .base import PriceSource

API_URL = "https://mc-api.marketcheck.com/v2/search/car/active"


class MarketcheckPriceSource(PriceSource):
    """Fetch current selling prices for a vehicle from Marketcheck.

    Parameters
    ----------
    api_key:
        Your Marketcheck API key (free tier available).
    rows:
        Max listings to request per vehicle.
    new_only:
        Restrict to new inventory (lease shopping is usually new cars).
    timeout:
        Per-request timeout in seconds.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        rows: int = 10,
        new_only: bool = True,
        timeout: float = 15.0,
    ):
        if not api_key:
            raise ValueError(
                "MarketcheckPriceSource requires an api_key. Get a free key at "
                "https://www.marketcheck.com/apis"
            )
        self._api_key = api_key
        self._rows = rows
        self._new_only = new_only
        self._timeout = timeout

    def prices_for(self, vehicle: Vehicle) -> List[PriceQuote]:
        params = {
            "api_key": self._api_key,
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "rows": self._rows,
            "sort_by": "price",
            "sort_order": "asc",
        }
        if self._new_only:
            params["car_type"] = "new"

        url = f"{API_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        quotes: List[PriceQuote] = []
        for listing in payload.get("listings", []):
            price = listing.get("price")
            if not price:
                continue
            dealer = (listing.get("dealer") or {})
            quotes.append(
                PriceQuote(
                    vehicle_id=vehicle.vehicle_id,
                    selling_price=float(price),
                    dealer=dealer.get("name", ""),
                    location=dealer.get("city", ""),
                    source="marketcheck",
                    url=listing.get("vdp_url", ""),
                )
            )
        return quotes
