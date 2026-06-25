"""Offline sample data sources.

These read the hand-seeded JSON in ``data/`` so the whole app runs end-to-end
with no network and no API keys. The numbers are realistic but illustrative —
swap in a real source (see ``leasehackr.py`` / ``cargurus.py``) for live data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from ..models import LeaseProgram, PriceQuote, Vehicle
from .base import PriceSource, ResidualSource

# repo_root/data/
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


class SampleResidualSource(ResidualSource):
    """Vehicles + lease programs loaded from ``data/sample_residuals.json``."""

    def __init__(self, path: Path | None = None):
        self._path = path or (DATA_DIR / "sample_residuals.json")
        raw = _load_json(self._path)
        self._vehicles: List[Vehicle] = []
        self._programs: Dict[str, List[LeaseProgram]] = {}

        for entry in raw["vehicles"]:
            vehicle = Vehicle(
                make=entry["make"],
                model=entry["model"],
                year=entry["year"],
                trim=entry.get("trim", ""),
                body_style=entry.get("body_style", ""),
                msrp=entry["msrp"],
            )
            self._vehicles.append(vehicle)
            programs = [
                LeaseProgram(
                    vehicle_id=vehicle.vehicle_id,
                    term=p["term"],
                    annual_mileage=p["annual_mileage"],
                    residual_percent=p["residual_percent"],
                    money_factor=p["money_factor"],
                    incentives=p.get("incentives", 0.0),
                    acquisition_fee=p.get("acquisition_fee", 0.0),
                    source="sample",
                )
                for p in entry.get("programs", [])
            ]
            self._programs[vehicle.vehicle_id] = programs

    def vehicles(self) -> List[Vehicle]:
        return list(self._vehicles)

    def programs_for(self, vehicle: Vehicle) -> List[LeaseProgram]:
        return list(self._programs.get(vehicle.vehicle_id, []))


class SamplePriceSource(PriceSource):
    """Selling prices loaded from ``data/sample_prices.json``."""

    def __init__(self, path: Path | None = None):
        self._path = path or (DATA_DIR / "sample_prices.json")
        raw = _load_json(self._path)
        self._prices: Dict[str, List[PriceQuote]] = {}
        for entry in raw["prices"]:
            quote = PriceQuote(
                vehicle_id=entry["vehicle_id"],
                selling_price=entry["selling_price"],
                dealer=entry.get("dealer", ""),
                location=entry.get("location", ""),
                source="sample",
                url=entry.get("url", ""),
                vin=entry.get("vin", ""),
            )
            self._prices.setdefault(quote.vehicle_id, []).append(quote)

    def prices_for(self, vehicle: Vehicle) -> List[PriceQuote]:
        return list(self._prices.get(vehicle.vehicle_id, []))
