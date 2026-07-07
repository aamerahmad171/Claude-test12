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
their Terms of Service. (Residuals & money factors originate from ALG/J.D. Power
and manufacturers' private dealer bulletins — there is no free or self-serve
public feed for them anywhere.) So this project is built around a **pluggable
data-source interface** with several providers:

- **`EstimatedResidualSource` / `EstimatedPriceSource`** — *the default.* Instead
  of needing Leasehackr's proprietary numbers, these **model** the residual %,
  money factor, and price from published depreciation patterns (term, segment,
  mileage) and MSRP. Transparent estimates grounded in real depreciation
  behavior — not a specific manufacturer's program, but defensible and 100%
  offline. See [`residual_model.py`](leasefinder/residual_model.py).
- **`MarketcheckPriceSource`** — a **real** live-price adapter (stdlib HTTP, no
  scraping) backed by the [Marketcheck API](https://www.marketcheck.com/apis),
  which has a free tier. Activate it with a key: `--prices marketcheck
  --marketcheck-key YOUR_KEY`.
- **`SampleResidualSource` / `SamplePriceSource`** — hand-seeded data in
  [`data/`](data/) for a fixed, reproducible demo (`--residuals sample`).
- **`leasehackr.py` / `cargurus.py`** — documented adapter stubs showing where to
  plug in a maintained data file or licensed feed (the way to get *exact*
  program numbers, e.g. copied from a real dealer quote).

All providers implement the same interface, so the math, scoring, CLI, web UI,
and report work unchanged regardless of which you pick.

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

# rank the best deals (default: modeled residuals + estimated prices)
python -m leasefinder.cli --top 10

# only SUVs, 36-month terms, payment under $500/mo, sorted by the 1% rule
python -m leasefinder.cli --body SUV --term 36 --max-payment 500 --sort one_percent

# use real live prices from Marketcheck (free-tier key)
python -m leasefinder.cli --prices marketcheck --marketcheck-key YOUR_KEY

# use the fixed hand-seeded sample dataset instead of the model
python -m leasefinder.cli --residuals sample --prices sample

# launch the web UI at http://localhost:5000
python -m leasefinder.web.app
```

### Standalone lease calculator

If you already have your own numbers (MSRP, selling price, residual %, money
factor, total incentives) and just want the Leasehackr-style breakdown — no
data sources, no ranking — open **`/calculator`** in the web UI
(`http://localhost:5000/calculator`). Every field updates the result live via
`/api/calculate`, which is a thin JSON wrapper around the same
[`compute_lease`](leasefinder/lease_math.py) function described below, so the
numbers are identical to (and tested against) the CLI and deals finder.

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
  residual_model.py  # depreciation-based residual/money-factor estimator
  models.py          # Vehicle, LeaseProgram, PriceQuote, LeaseDeal dataclasses
  scoring.py         # 1% rule, effective cost, composite deal score
  finder.py          # orchestration: sources -> deals -> ranked results
  cli.py             # command-line interface
  sources/
    base.py          # ResidualSource / PriceSource interfaces
    estimated.py     # modeled residuals + estimated prices (default)
    marketcheck.py   # real live-price adapter (free-tier API key)
    sample.py        # fixed hand-seeded providers
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
