"""Minimal Flask web UI + JSON API for the lease deals finder.

Run:
    python -m leasefinder.web.app
then open http://localhost:5000
"""

from __future__ import annotations

from dataclasses import asdict

from flask import Flask, jsonify, render_template, request

from ..finder import (
    SORT_KEYS,
    DealFilter,
    LeaseFinder,
    build_price_source,
    build_residual_source,
)
from ..lease_math import apr_to_mf, compute_lease
from ..models import LeaseDeal


def create_app() -> Flask:
    app = Flask(__name__)

    def _query_deals() -> list[LeaseDeal]:
        args = request.args
        tax_rate = _as_float(args.get("tax_rate"), 0.0)
        residuals = args.get("residuals", "estimated")
        finder = LeaseFinder(
            residual_source=build_residual_source(
                residuals if residuals in ("estimated", "sample") else "estimated"
            ),
            price_source=build_price_source(
                "sample" if residuals == "sample" else "estimated"
            ),
            tax_rate=tax_rate,
        )
        deal_filter = DealFilter(
            make=args.get("make") or None,
            body_style=args.get("body") or None,
            term=_as_int(args.get("term")),
            max_payment=_as_float(args.get("max_payment"), None),
            max_msrp=_as_float(args.get("max_msrp"), None),
        )
        sort = args.get("sort", "deal_score")
        if sort not in SORT_KEYS:
            sort = "deal_score"
        top = _as_int(args.get("top")) or 25
        return finder.find_best_deals(top=top, sort=sort, deal_filter=deal_filter)

    @app.route("/")
    def index():
        deals = _query_deals()
        return render_template(
            "index.html",
            deals=deals,
            args=request.args,
            sort_keys=sorted(SORT_KEYS),
        )

    @app.route("/api/deals")
    def api_deals():
        deals = _query_deals()
        return jsonify([_deal_to_dict(d) for d in deals])

    @app.route("/calculator")
    def calculator():
        return render_template("calculator.html")

    @app.route("/api/calculate")
    def api_calculate():
        args = request.args
        try:
            msrp = _require_float(args, "msrp")
            selling_price = _require_float(args, "selling_price")
            term = _require_int(args, "term")
            residual_percent = _require_float(args, "residual_percent")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        money_factor = _as_float(args.get("money_factor"), None)
        apr = _as_float(args.get("apr"), None)
        if money_factor is None:
            money_factor = apr_to_mf(apr) if apr is not None else 0.0

        down_payment = _as_float(args.get("down_payment"), 0.0)
        trade_in = _as_float(args.get("trade_in"), 0.0)
        incentives = _as_float(args.get("incentives"), 0.0)
        acquisition_fee = _as_float(args.get("acquisition_fee"), 0.0)
        upfront_fees = _as_float(args.get("upfront_fees"), 0.0)
        tax_rate = _as_float(args.get("tax_rate"), 0.0)
        first_payment_at_signing = args.get("first_payment_at_signing", "true") != "false"

        try:
            quote = compute_lease(
                msrp=msrp,
                selling_price=selling_price,
                residual_percent=residual_percent,
                money_factor=money_factor,
                term=term,
                cap_cost_reduction=down_payment + trade_in,
                rebates=incentives,
                capitalized_fees=acquisition_fee,
                upfront_fees=upfront_fees,
                tax_rate=tax_rate,
                first_payment_due_at_signing=first_payment_at_signing,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        result = asdict(quote)
        result["one_percent"] = quote.base_payment / quote.msrp * 100
        result["effective_one_percent"] = quote.effective_monthly / quote.msrp * 100
        result["due_at_signing_breakdown"] = {
            "down_payment": down_payment,
            "trade_in": trade_in,
            "upfront_fees": upfront_fees,
            "first_month_payment": quote.monthly_payment if first_payment_at_signing else 0.0,
        }
        return jsonify(result)

    return app


def _deal_to_dict(deal: LeaseDeal) -> dict:
    return {
        "vehicle": deal.vehicle.vehicle_id,
        "body_style": deal.vehicle.body_style,
        "msrp": deal.vehicle.msrp,
        "selling_price": deal.price.selling_price,
        "dealer": deal.price.dealer,
        "term": deal.program.term,
        "annual_mileage": deal.program.annual_mileage,
        **deal.metrics,
    }


def _as_int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _as_float(value, default):
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _require_float(args, name: str) -> float:
    value = args.get(name)
    if value in (None, ""):
        raise ValueError(f"missing required field: {name}")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {value!r}")


def _require_int(args, name: str) -> int:
    value = args.get(name)
    if value in (None, ""):
        raise ValueError(f"missing required field: {name}")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer, got {value!r}")


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
