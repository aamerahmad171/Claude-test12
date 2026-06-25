"""Command-line interface for the lease deals finder.

Examples
--------
    python -m leasefinder.cli --top 10
    python -m leasefinder.cli --body SUV --term 36 --max-payment 500
    python -m leasefinder.cli --sort one_percent --make Honda
    python -m leasefinder.cli --json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from .finder import (
    PRICE_SOURCES,
    RESIDUAL_SOURCES,
    SORT_KEYS,
    DealFilter,
    LeaseFinder,
    build_price_source,
    build_residual_source,
)
from .models import LeaseDeal


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="leasefinder",
        description="Find and rank the best car-lease deals.",
    )
    p.add_argument("--top", type=int, default=10, help="show N best deals (default 10)")
    p.add_argument(
        "--sort",
        choices=sorted(SORT_KEYS),
        default="deal_score",
        help="ranking metric (default: deal_score)",
    )
    p.add_argument("--make", help="filter by make, e.g. Honda")
    p.add_argument("--body", dest="body_style", help="filter by body style, e.g. SUV")
    p.add_argument("--term", type=int, help="filter by term in months, e.g. 36")
    p.add_argument(
        "--miles", type=int, dest="annual_mileage", help="filter by annual mileage"
    )
    p.add_argument(
        "--max-payment", type=float, help="max base monthly payment, e.g. 500"
    )
    p.add_argument("--max-das", type=float, help="max due-at-signing cash")
    p.add_argument("--max-msrp", type=float, help="max MSRP")
    p.add_argument(
        "--tax-rate", type=float, default=0.0, help="sales tax rate, e.g. 0.0625"
    )
    p.add_argument(
        "--upfront-fees",
        type=float,
        default=0.0,
        help="non-financed fees due at signing (doc, registration, ...)",
    )
    p.add_argument(
        "--residuals",
        choices=RESIDUAL_SOURCES,
        default="estimated",
        help="residual/money-factor source (default: estimated depreciation model)",
    )
    p.add_argument(
        "--prices",
        choices=PRICE_SOURCES,
        default="estimated",
        help="selling-price source (default: estimated from MSRP)",
    )
    p.add_argument(
        "--marketcheck-key",
        help="API key for --prices marketcheck (free tier at marketcheck.com/apis)",
    )
    p.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    return p


def _deal_to_dict(deal: LeaseDeal) -> dict:
    return {
        "vehicle": deal.vehicle.vehicle_id,
        "body_style": deal.vehicle.body_style,
        "msrp": deal.vehicle.msrp,
        "selling_price": deal.price.selling_price,
        "dealer": deal.price.dealer,
        "term": deal.program.term,
        "annual_mileage": deal.program.annual_mileage,
        "residual_percent": deal.program.residual_percent,
        "money_factor": deal.program.money_factor,
        **deal.metrics,
    }


def _print_table(deals: List[LeaseDeal]) -> None:
    if not deals:
        print("No deals matched your filters.")
        return

    header = (
        f"{'#':>2}  {'Vehicle':<34}{'Pay/mo':>8}{'Eff/mo':>8}"
        f"{'1%':>7}{'DAS':>9}{'Term':>6}{'Mi':>5}{'Score':>7}"
    )
    print(header)
    print("-" * len(header))
    for i, d in enumerate(deals, 1):
        m = d.metrics
        print(
            f"{i:>2}  {str(d.vehicle):<34}"
            f"{m['base_payment']:>8,.0f}"
            f"{m['effective_monthly']:>8,.0f}"
            f"{m['one_percent']:>6.2f}%"
            f"{m['due_at_signing']:>9,.0f}"
            f"{d.program.term:>6}"
            f"{d.program.annual_mileage // 1000:>4}k"
            f"{m['deal_score']:>7.0f}"
        )
    print()
    print(
        "1% = base payment as % of MSRP (<=1.0% is strong).  "
        "Eff/mo folds in all due-at-signing cash.  "
        "Score is a 0-100 composite (higher = better)."
    )


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    finder = LeaseFinder(
        residual_source=build_residual_source(args.residuals),
        price_source=build_price_source(
            args.prices, marketcheck_key=args.marketcheck_key
        ),
        tax_rate=args.tax_rate,
        upfront_fees=args.upfront_fees,
    )
    deal_filter = DealFilter(
        make=args.make,
        body_style=args.body_style,
        term=args.term,
        annual_mileage=args.annual_mileage,
        max_payment=args.max_payment,
        max_due_at_signing=args.max_das,
        max_msrp=args.max_msrp,
    )

    deals = finder.find_best_deals(
        top=args.top, sort=args.sort, deal_filter=deal_filter
    )

    if args.json:
        json.dump([_deal_to_dict(d) for d in deals], sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        _print_table(deals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
