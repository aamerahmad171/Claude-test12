"""Residual / money-factor adapter for Leasehackr-style data.

──────────────────────────────────────────────────────────────────────────────
WHY THIS IS A DOCUMENTED STUB, NOT A SCRAPER
──────────────────────────────────────────────────────────────────────────────
Leasehackr's calculator (https://leasehackr.com/calculator) is a front end you
feed residual %, money factor, MSRP, etc. into — those underlying numbers come
from manufacturer lease programs that update monthly. Leasehackr does not expose
a public API, and scraping the site is unreliable and against its Terms of
Service.

So this adapter defines the *shape* of a real integration and leaves the actual
data acquisition to you, done compliantly. Good options:

  1. A licensed lease-program data feed (several B2B vendors sell these).
  2. A CSV/JSON you maintain by hand from dealer "lease program" sheets or the
     manufacturer's monthly residual & money-factor bulletins.
  3. Numbers you personally pulled from the Leasehackr calculator for cars you
     care about, saved locally.

Any of these can populate ``programs_for``. The rest of the app won't change.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..models import LeaseProgram, Vehicle
from .base import ResidualSource
from .sample import SampleResidualSource


class LeasehackrResidualSource(ResidualSource):
    """Skeleton for a real Leasehackr-derived residual/money-factor source.

    Parameters
    ----------
    data_path:
        Optional path to a local JSON/CSV you maintain (recommended approach).
        If given, this behaves like the sample source but pointed at your file.
    """

    def __init__(self, data_path: Path | None = None):
        self._data_path = data_path
        self._delegate = (
            SampleResidualSource(path=data_path) if data_path is not None else None
        )

    def vehicles(self) -> List[Vehicle]:
        if self._delegate is not None:
            return self._delegate.vehicles()
        raise NotImplementedError(
            "Provide a `data_path` to a maintained residual/MF file, or implement "
            "vehicles()/programs_for() against your licensed data feed. See the "
            "module docstring for compliant options."
        )

    def programs_for(self, vehicle: Vehicle) -> List[LeaseProgram]:
        if self._delegate is not None:
            return self._delegate.programs_for(vehicle)
        # A real implementation would map manufacturer program data into
        # LeaseProgram objects, e.g.:
        #
        #     return [
        #         LeaseProgram(
        #             vehicle_id=vehicle.vehicle_id,
        #             term=program["term"],
        #             annual_mileage=program["miles"],
        #             residual_percent=program["residual"],
        #             money_factor=program["mf"],
        #             incentives=program.get("lease_cash", 0.0),
        #             acquisition_fee=program.get("acq_fee", 0.0),
        #             source="leasehackr",
        #         )
        #         for program in self._fetch_programs(vehicle)
        #     ]
        raise NotImplementedError(
            "Wire programs_for() to your compliant Leasehackr-derived data."
        )
