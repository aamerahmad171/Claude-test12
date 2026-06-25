"""Residual-value and money-factor estimation from published depreciation patterns.

Manufacturer residuals aren't random — they track well-documented depreciation
curves. This module turns those public patterns into estimated residual
percentages and a rate-environment money factor, so the app can produce
defensible lease numbers **without** Leasehackr, scraping, or a paid feed.

These are transparent *estimates*, not a specific manufacturer's program. They
won't match a real lease program to the dollar, but they're grounded in real
depreciation behavior rather than invented.

Model
-----
* **Term:** residuals fall roughly linearly with lease length. Anchored at
  ~68% of MSRP for 24 months and ~48% for 48 months (≈ -10 points per year),
  which reproduces the familiar ~58% for a 36-month lease.
* **Segment:** body-on-frame trucks/SUVs hold value better; most EVs and luxury
  sedans depreciate faster. Applied as an additive adjustment.
* **Mileage:** lower annual mileage raises the residual (less wear), centered on
  a 12k/yr baseline.
* **Money factor:** derived from the prevailing new-car APR environment
  (MF = APR / 2400).
"""

from __future__ import annotations

from .lease_math import apr_to_mf

# Residual (fraction of MSRP) as a linear function of term, at a 12k/yr baseline.
RESIDUAL_AT_24_MONTHS = 0.68
RESIDUAL_DROP_PER_MONTH = (0.68 - 0.48) / (48 - 24)  # ≈ 0.00833 (-10 pts/year)

# Additive residual adjustment by body style (value retention by segment).
SEGMENT_ADJUSTMENT = {
    "truck": 0.05,
    "suv": 0.02,
    "minivan": -0.01,
    "hatchback": -0.01,
    "sedan": 0.00,
    "coupe": 0.01,
    "sports": 0.02,
    "ev": -0.05,
    "luxury": -0.03,
}

# Annual-mileage baseline; residual rises/falls around it.
MILEAGE_BASELINE = 12000
# Each 1,000 miles/yr away from baseline shifts the residual ~1 point.
MILEAGE_SENSITIVITY_PER_MILE = 1.0 / 100000.0

# Default rate environment (annual percentage rate) used for the money factor.
DEFAULT_BASE_APR = 6.0

# Keep estimates in a sane band.
MIN_RESIDUAL = 0.20
MAX_RESIDUAL = 0.80


def base_residual_percent(term: int) -> float:
    """Residual fraction for a term at the 12k/yr, average-segment baseline."""
    return RESIDUAL_AT_24_MONTHS - RESIDUAL_DROP_PER_MONTH * (term - 24)


def segment_adjustment(body_style: str) -> float:
    """Additive residual adjustment for a body style (0 if unknown)."""
    return SEGMENT_ADJUSTMENT.get((body_style or "").strip().lower(), 0.0)


def mileage_adjustment(annual_mileage: int) -> float:
    """Additive residual adjustment for annual mileage vs the 12k/yr baseline."""
    return (MILEAGE_BASELINE - annual_mileage) * MILEAGE_SENSITIVITY_PER_MILE


def estimate_residual_percent(
    body_style: str, term: int, annual_mileage: int
) -> float:
    """Estimated residual as a fraction of MSRP, clamped to a realistic band."""
    raw = (
        base_residual_percent(term)
        + segment_adjustment(body_style)
        + mileage_adjustment(annual_mileage)
    )
    return max(MIN_RESIDUAL, min(MAX_RESIDUAL, round(raw, 4)))


def estimate_money_factor(base_apr_percent: float = DEFAULT_BASE_APR) -> float:
    """Money factor derived from the prevailing new-car APR environment."""
    return round(apr_to_mf(base_apr_percent), 6)
