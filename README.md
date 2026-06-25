# Lease Deals Finder

Finds and ranks the best car-lease deals by combining two kinds of data:

1. **Residual values & money factors** — the numbers a tool like the
   [Leasehackr calculator](https://leasehackr.com/calculator) uses to turn an
   MSRP into a monthly payment (residual % of MSRP + the lease money factor).
2. **Current selling prices** — what cars are actually transacting for, from
   marketplaces like [CarGurus](https://www.cargurus.com/).

It then computes the real lease cost for every car/term/mileage combination and
ranks them using transparent, well-known lease metrics (the **1% rule**, the
**effective monthly cost**, and a composite **deal score**).

---

## ⚠️ About the data sources (read this first)

Neither Leasehackr nor CarGurus offers a public API, and both use anti-bot
protection. Scraping them programmatically is unreliable and generally against
their Terms of Service. So this project is built around a **pluggable data-source
interface** rather than a brittle scraper:

- **`SampleResidualSource` / `SamplePriceSource`** — realistic, hand-seeded data
  in [`data/`](data/) so the whole app runs **end-to-end offline**, today, with
  no API keys. This is the default.
- **`leasehackr.py` / `cargurus.py`** — documented adapter stubs that show
  *exactly* where to plug in real data: a licensed data feed, a manually exported
  CSV, a dealer's lease program sheet, or your own compliant fetcher. They
  implement the same interface, so the rest of the app doesn't change.

The **lease math itself is exact** — it's the same depreciation + rent-charge
formula the Leasehackr calculator uses, and it's covered by tests against
hand-worked examples.

---

## Quick start

```bash
# (optional) create a virtualenv
python3 -m venv .venv && source .venv/bin/activate

# install (web UI needs Flask; the core + CLI have no dependencies)
pip install -r requirements.txt

# rank the best deals from the bundled sample data
python -m leasefinder.cli --top 10

# only SUVs, 36-month terms, payment under $500/mo, sorted by the 1% rule
python -m leasefinder.cli --body SUV --term 36 --max-payment 500 --sort one_percent

# launch the web UI at http://localhost:5000
python -m leasefinder.web.app
```

Run the tests:

```bash
pip install pytest
pytest
```

---

## Hosted results page

A static, self-contained results page is generated from the data:

```bash
python scripts/build_report.py   # writes docs/index.html
```

- It works with **no server** — open `docs/index.html` directly, or host it.
- The table is rendered at build time (so it shows even with JavaScript off);
  clicking a column header re-sorts it when JS is available.
- A GitHub Actions workflow (`.github/workflows/pages.yml`) rebuilds and
  publishes it to **GitHub Pages** on merge to `main`. One-time setup:
  *Settings → Pages → Source: GitHub Actions*. The site then lives at
  `https://<owner>.github.io/<repo>/`.

## How a deal is scored

For each candidate (a vehicle + a lease program + a price quote) the engine
computes a full lease using standard math:

```
residual_value    = MSRP * residual_percent
adjusted_cap_cost = selling_price + capitalized_fees - cash_down - rebates
depreciation/mo   = (adjusted_cap_cost - residual_value) / term
rent_charge/mo    = (adjusted_cap_cost + residual_value) * money_factor
base_payment/mo   = depreciation + rent_charge
```

Manufacturer **rebates** (lease cash) lower the cap cost just like cash down,
but they are *not* money out of your pocket — so they reduce the payment without
inflating the due-at-signing or effective-monthly figures. This is why a heavily
incentivized car (e.g. an EV with $7,500 lease cash) can dominate the rankings.

(`APR ≈ money_factor * 2400`.) It then derives the metrics deals are actually
compared on:

| Metric | Meaning | Lower is better? |
| --- | --- | --- |
| `base_payment` | Pre-tax monthly payment | ✅ |
| `effective_monthly` | Total cost (incl. all due-at-signing cash) ÷ term — the apples-to-apples number | ✅ |
| `one_percent` | `base_payment / MSRP` — the famous **1% rule**; ≤ 1.0% is a strong deal | ✅ |
| `effective_one_percent` | `effective_monthly / MSRP` | ✅ |
| `deal_score` | Composite 0–100 (higher = better); rewards low effective %, short cash-out, incentives | ❌ higher better |

> **Note:** `deal_score` is *our own transparent metric* (see
> [`scoring.py`](leasefinder/scoring.py)). It is **not** the proprietary
> "Leasehackr Score." The **1% rule** and the lease formula, however, are
> industry-standard.

---

## Project layout

```
leasefinder/
  lease_math.py      # the core lease formula (pure, fully tested)
  models.py          # Vehicle, LeaseProgram, PriceQuote, LeaseDeal dataclasses
  scoring.py         # 1% rule, effective cost, composite deal score
  finder.py          # orchestration: sources -> deals -> ranked results
  cli.py             # command-line interface
  sources/
    base.py          # ResidualSource / PriceSource interfaces
    sample.py        # offline sample providers (default)
    leasehackr.py    # residual + money-factor adapter stub (documented)
    cargurus.py      # selling-price adapter stub (documented)
  web/
    app.py           # Flask web UI
    templates/index.html
data/
  sample_residuals.json
  sample_prices.json
tests/
```

## Wiring in real data

Implement the two interfaces in `sources/base.py` and pass them to `LeaseFinder`:

```python
from leasefinder.finder import LeaseFinder
from myproject.my_sources import MyResidualSource, MyCarGurusSource

finder = LeaseFinder(
    residual_source=MyResidualSource(),   # provides residual % + money factor
    price_source=MyCarGurusSource(api_key=...),  # provides current selling prices
)
deals = finder.find_best_deals(top=20)
```

Everything downstream — math, scoring, CLI, web UI — works unchanged.
