"""Minimal Flask web UI + JSON API for the lease deals finder.

Run:
    python -m leasefinder.web.app
then open http://localhost:5000
"""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from ..finder import SORT_KEYS, DealFilter, LeaseFinder
from ..models import LeaseDeal


def create_app() -> Flask:
    app = Flask(__name__)

    def _query_deals() -> list[LeaseDeal]:
        args = request.args
        tax_rate = _as_float(args.get("tax_rate"), 0.0)
        finder = LeaseFinder(tax_rate=tax_rate)
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


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
