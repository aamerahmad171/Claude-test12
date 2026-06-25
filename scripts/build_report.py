"""Generate a self-contained static HTML report of the best lease deals.

Writes ``docs/index.html`` — a single file with inline CSS + a little vanilla JS
for client-side sorting, so it can be hosted on GitHub Pages (or opened directly
/ via htmlpreview) with no server and no external requests.

Usage:
    python scripts/build_report.py
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))  # allow running as `python scripts/build_report.py`

from leasefinder.finder import (  # noqa: E402
    LeaseFinder,
    build_price_source,
    build_residual_source,
)

OUT = REPO_ROOT / "docs" / "index.html"
TOP_N = 40  # the model generates many (term x mileage) combos; show the best


def _deal_rows() -> list[dict]:
    finder = LeaseFinder(
        residual_source=build_residual_source("estimated"),
        price_source=build_price_source("estimated"),
    )
    deals = finder.find_best_deals(top=TOP_N, sort="deal_score")
    rows = []
    for d in deals:
        m = d.metrics
        rows.append(
            {
                "vehicle": d.vehicle.vehicle_id,
                "body": d.vehicle.body_style,
                "dealer": d.price.dealer,
                "msrp": d.vehicle.msrp,
                "price": d.price.selling_price,
                "pay": m["base_payment"],
                "eff": m["effective_monthly"],
                "one_percent": m["one_percent"],
                "das": m["due_at_signing"],
                "term": d.program.term,
                "miles": d.program.annual_mileage // 1000,
                "apr": m["apr"],
                "score": m["deal_score"],
            }
        )
    return rows


def _money(n: float) -> str:
    return "$" + f"{round(n):,}"


def _rows_html(rows: list[dict]) -> str:
    """Pre-render the table body so the report works with JavaScript disabled."""
    out = []
    for i, r in enumerate(rows, 1):
        good = " good1" if r["one_percent"] <= 1.0 else ""
        out.append(
            f'<tr>'
            f'<td class="l rank">{i}</td>'
            f'<td class="l">{r["vehicle"]}<br><span class="pill">{r["dealer"]}</span></td>'
            f'<td class="l">{r["body"]}</td>'
            f'<td>{_money(r["msrp"])}</td>'
            f'<td>{_money(r["price"])}</td>'
            f'<td>{_money(r["pay"])}</td>'
            f'<td>{_money(r["eff"])}</td>'
            f'<td class="{good.strip()}">{r["one_percent"]:.2f}%</td>'
            f'<td>{_money(r["das"])}</td>'
            f'<td>{r["term"]}</td>'
            f'<td>{r["miles"]}k</td>'
            f'<td>{r["apr"]:.1f}%</td>'
            f'<td class="score">{round(r["score"])}</td>'
            f'</tr>'
        )
    return "\n".join(out)


def build_html() -> str:
    rows = _deal_rows()
    generated = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        _TEMPLATE
        .replace("/*DATA*/", json.dumps(rows))
        .replace("<!--ROWS-->", _rows_html(rows))
        .replace("__GENERATED__", generated)
    )


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO_ROOT)} ({OUT.stat().st_size:,} bytes)")
    return 0


_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Lease Deals Finder — Results</title>
<style>
:root{--bg:#0f1115;--card:#181b22;--line:#262b35;--txt:#e6e9ef;--muted:#8b93a3;--good:#4ad295;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}
header{padding:30px 24px 6px;max-width:1100px;margin:0 auto;}
h1{margin:0;font-size:26px;}
.sub{color:var(--muted);margin-top:6px;}
.note{color:var(--muted);font-size:12.5px;max-width:820px;margin-top:10px;border-left:3px solid #c9a23a;padding-left:10px;}
.wrap{max-width:1100px;margin:0 auto;padding:14px 24px 60px;}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:10px;overflow:hidden;}
th,td{text-align:right;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap;}
th:first-child,td:first-child,th.l,td.l{text-align:left;}
th{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.03em;cursor:pointer;user-select:none;}
th:hover{color:var(--txt);}
tbody tr:hover{background:#1e2230;}
.score{font-weight:700;color:var(--good);}
.pill{font-size:11px;color:var(--muted);border:1px solid var(--line);padding:1px 7px;border-radius:999px;}
.good1{color:var(--good);font-weight:600;}
.rank{color:var(--muted);}
footer{color:var(--muted);font-size:12px;max-width:1100px;margin:0 auto;padding:0 24px 40px;}
a{color:#7fb6ff;}
</style>
</head>
<body>
<header>
  <h1>🚗 Lease Deals Finder — Results</h1>
  <div class="sub">Ranked by combining residual values &amp; money factors (Leasehackr-style) with current selling prices (CarGurus-style). Click any column header to re-sort.</div>
  <div class="note">
    <strong>Heads up:</strong> residuals &amp; money factors here are <strong>modeled</strong> from
    published depreciation patterns (term, segment, mileage), and prices are estimated from MSRP —
    no Leasehackr / CarGurus feed (neither offers a public API). The lease math is exact; the inputs
    are transparent estimates, not a specific manufacturer's program. Drop in a maintained data file
    or a Marketcheck key for real prices. Generated <strong>__GENERATED__</strong>.
  </div>
</header>
<div class="wrap">
  <table id="t">
    <thead>
      <tr>
        <th class="l" data-k="rank">#</th>
        <th class="l" data-k="vehicle">Vehicle</th>
        <th class="l" data-k="body">Body</th>
        <th data-k="msrp">MSRP</th>
        <th data-k="price">Price</th>
        <th data-k="pay">Pay/mo</th>
        <th data-k="eff">Eff/mo</th>
        <th data-k="one_percent">1%</th>
        <th data-k="das">Due@sign</th>
        <th data-k="term">Term</th>
        <th data-k="miles">Mi/yr</th>
        <th data-k="apr">APR</th>
        <th data-k="score">Score</th>
      </tr>
    </thead>
    <tbody id="b"><!--ROWS--></tbody>
  </table>
</div>
<footer>
  1% = base payment as % of MSRP (≤1.0% is strong). Eff/mo folds in all due-at-signing cash.
  Score is a transparent 0–100 composite (higher = better), not the proprietary Leasehackr Score.
</footer>
<script>
const DATA = /*DATA*/;
const money = n => "$" + Math.round(n).toLocaleString();
let sortKey = "score", asc = false;
function render(){
  const rows = [...DATA].sort((a,b)=>{
    const x=a[sortKey], y=b[sortKey];
    const c = (typeof x==="number") ? x-y : String(x).localeCompare(String(y));
    return asc ? c : -c;
  });
  const tb = document.getElementById("b");
  tb.innerHTML = rows.map((r,i)=>`
    <tr>
      <td class="l rank">${i+1}</td>
      <td class="l">${r.vehicle}<br><span class="pill">${r.dealer}</span></td>
      <td class="l">${r.body}</td>
      <td>${money(r.msrp)}</td>
      <td>${money(r.price)}</td>
      <td>${money(r.pay)}</td>
      <td>${money(r.eff)}</td>
      <td class="${r.one_percent<=1.0?'good1':''}">${r.one_percent.toFixed(2)}%</td>
      <td>${money(r.das)}</td>
      <td>${r.term}</td>
      <td>${r.miles}k</td>
      <td>${r.apr.toFixed(1)}%</td>
      <td class="score">${Math.round(r.score)}</td>
    </tr>`).join("");
}
document.querySelectorAll("th[data-k]").forEach(th=>{
  th.addEventListener("click",()=>{
    const k=th.dataset.k;
    if(k==="rank") return;
    if(sortKey===k) asc=!asc; else { sortKey=k; asc=(k==="vehicle"||k==="body"); }
    render();
  });
});
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
