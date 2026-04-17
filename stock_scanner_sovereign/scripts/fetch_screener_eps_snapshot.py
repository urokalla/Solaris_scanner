#!/usr/bin/env python3
"""
Fetch EPS snapshot for a universe CSV (default: Nifty Total Market) from Screener pages.

Output CSV is intended for downstream C/A calculations:
  - C: latest quarterly EPS YoY (latest vs 4 quarters ago)
  - A: latest annual EPS YoY (latest FY vs previous FY; ignores TTM column)

Example:
  python3 scripts/fetch_screener_eps_snapshot.py --universe-csv data/nifty_total_market.csv --limit 50
"""

from __future__ import annotations

import argparse
import csv
import html as ihtml
import random
import re
import time
from io import StringIO
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


def _norm_symbol(raw: str) -> str:
    s = str(raw or "").strip().upper()
    if not s:
        return ""
    if ":" in s:
        s = s.split(":", 1)[1]
    if s.endswith("-INDEX"):
        return ""
    if "-" in s:
        s = s.rsplit("-", 1)[0]
    return s.strip()


def _slug_for_screener(symbol: str) -> str:
    return symbol.replace("_", "-").upper()


def _safe_float(x) -> float | None:
    if x is None:
        return None
    t = str(x).strip().replace(",", "")
    if not t or t in ("—", "-", "NA", "N/A", "nan"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _eps_row_from_table(df: pd.DataFrame) -> tuple[list[str], list[float | None]] | None:
    if df is None or df.empty:
        return None
    cols = [str(c).strip() for c in df.columns]
    first_col = cols[0] if cols else ""
    if not first_col:
        return None

    # Find row where first column is EPS line.
    candidate_idx = None
    for i in range(len(df)):
        k = str(df.iloc[i, 0]).strip().lower()
        if k == "eps in rs":
            candidate_idx = i
            break
    if candidate_idx is None:
        return None

    labels = [str(c).strip() for c in cols[1:]]
    values = [_safe_float(v) for v in list(df.iloc[candidate_idx, 1:])]
    return labels, values


def _extract_eps_series(html: str) -> tuple[list[str], list[float | None], list[str], list[float | None]]:
    """
    Returns:
      quarterly_labels, quarterly_eps, annual_labels, annual_eps
    """
    q_labels: list[str] = []
    q_vals: list[float | None] = []
    a_labels: list[str] = []
    a_vals: list[float | None] = []

    def _strip_tags(x: str) -> str:
        return re.sub(r"<[^>]+>", "", ihtml.unescape(x or "")).strip()

    def _eps_from_section(raw: str) -> tuple[list[str], list[float | None]] | None:
        m = re.search(r"EPS in Rs\s*</t[dh]>\s*(.*?)</tr>", raw, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        row_chunk = m.group(1)
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_chunk, flags=re.IGNORECASE | re.DOTALL)
        vals = [_safe_float(_strip_tags(c)) for c in cells]
        labels = [f"X{i+1}" for i in range(len(vals))]
        return labels, vals

    # Fast HTML regex route (works even when lxml/html5lib unavailable).
    q_idx = html.find("Quarterly Results")
    a_idx = html.find("Profit & Loss")
    if q_idx >= 0:
        q_end = a_idx if a_idx > q_idx else min(len(html), q_idx + 120000)
        q_sec = html[q_idx:q_end]
        q = _eps_from_section(q_sec)
        if q is not None:
            q_labels, q_vals = q
    if a_idx >= 0:
        a_end = min(len(html), a_idx + 160000)
        a_sec = html[a_idx:a_end]
        a = _eps_from_section(a_sec)
        if a is not None:
            a_labels, a_vals = a
    if q_vals or a_vals:
        return q_labels, q_vals, a_labels, a_vals

    tables: list[pd.DataFrame] = []
    for kwargs in ({}, {"flavor": "bs4"}, {"flavor": "html5lib"}):
        try:
            tables = pd.read_html(StringIO(html), **kwargs)
            if tables:
                break
        except Exception:
            continue
    if not tables:
        # Fallback when HTML parser deps are unavailable: parse pipe-style EPS rows.
        eps_lines = re.findall(r"\|\s*EPS in Rs\s*\|([^\n\r]+)", html, flags=re.IGNORECASE)
        if eps_lines:
            def _vals(s: str) -> list[float | None]:
                parts = [p.strip() for p in s.split("|")]
                return [_safe_float(p) for p in parts if p.strip()]
            if len(eps_lines) >= 1:
                q_vals = _vals(eps_lines[0])
                q_labels = [f"Q{i+1}" for i in range(len(q_vals))]
            if len(eps_lines) >= 2:
                a_vals = _vals(eps_lines[1])
                a_labels = [f"A{i+1}" for i in range(len(a_vals))]
        return q_labels, q_vals, a_labels, a_vals

    # Identify tables by nearby markers in flattened text.
    # Screener structure usually includes Quarterly first and P&L second.
    quarter_idx = None
    annual_idx = None
    for idx, t in enumerate(tables):
        txt = " ".join(str(x) for x in t.head(3).astype(str).values.flatten())
        if quarter_idx is None and re.search(r"Dec|Mar|Jun|Sep", txt):
            row_names = " ".join(str(x) for x in t.iloc[:, 0].astype(str).head(20).tolist())
            if "EPS in Rs" in row_names:
                quarter_idx = idx
        if annual_idx is None:
            row_names = " ".join(str(x) for x in t.iloc[:, 0].astype(str).head(30).tolist())
            if "EPS in Rs" in row_names:
                # Annual table usually has long FY history and may include TTM.
                if t.shape[1] >= 8:
                    annual_idx = idx
        if quarter_idx is not None and annual_idx is not None:
            break

    # Fallback: pick first two EPS tables if detection ambiguous.
    eps_tables: list[tuple[list[str], list[float | None]]] = []
    for t in tables:
        got = _eps_row_from_table(t)
        if got is not None:
            eps_tables.append(got)
    if quarter_idx is None or annual_idx is None:
        if eps_tables:
            q_labels, q_vals = eps_tables[0]
        if len(eps_tables) > 1:
            a_labels, a_vals = eps_tables[1]
        return q_labels, q_vals, a_labels, a_vals

    q_got = _eps_row_from_table(tables[quarter_idx])
    a_got = _eps_row_from_table(tables[annual_idx])
    if q_got is not None:
        q_labels, q_vals = q_got
    if a_got is not None:
        a_labels, a_vals = a_got
    return q_labels, q_vals, a_labels, a_vals


def _calc_qtr_yoy(vals: list[float | None]) -> tuple[float | None, float | None, float | None]:
    clean = [v for v in vals if v is not None]
    if len(clean) < 5:
        return None, None, None
    latest = clean[-1]
    base = clean[-5]
    if base == 0:
        return latest, base, None
    yoy = ((latest - base) / abs(base)) * 100.0
    return latest, base, yoy


def _calc_ann_yoy(labels: list[str], vals: list[float | None]) -> tuple[float | None, float | None, float | None]:
    if not vals:
        return None, None, None
    pairs = [(str(labels[i]).strip() if i < len(labels) else "", vals[i]) for i in range(len(vals))]
    # Remove missing and TTM from annual comparison.
    clean = [(lab, v) for lab, v in pairs if v is not None and "TTM" not in lab.upper()]
    if len(clean) < 2:
        return None, None, None
    latest = clean[-1][1]
    prev = clean[-2][1]
    if latest is None or prev in (None, 0):
        return latest, prev, None
    yoy = ((latest - prev) / abs(prev)) * 100.0
    return latest, prev, yoy


def _iter_symbols_from_csv(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        fields = [str(c).strip() for c in (r.fieldnames or [])]
        symbol_col = next((c for c in fields if c.lower() == "symbol"), fields[0] if fields else "symbol")
        seen = set()
        for row in r:
            s = _norm_symbol(row.get(symbol_col, ""))
            if not s or s in seen:
                continue
            seen.add(s)
            yield s


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Screener EPS snapshot for universe CSV.")
    ap.add_argument("--universe-csv", default="data/nifty_total_market.csv", help="Universe CSV relative to stock_scanner_sovereign.")
    ap.add_argument("--out", default="data/screener_eps_snapshot.csv", help="Output CSV path relative to stock_scanner_sovereign.")
    ap.add_argument("--limit", type=int, default=0, help="Optional max symbols to process.")
    ap.add_argument("--symbols", default="", help="Optional comma-separated symbols/slugs to override universe CSV (e.g. RELIANCE,TCS).")
    ap.add_argument("--timeout", type=int, default=20, help="HTTP timeout per symbol.")
    ap.add_argument("--sleep-sec", type=float, default=1.0, help="Base sleep between symbol fetches.")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    in_csv = (root / args.universe_csv).resolve()
    out_csv = (root / args.out).resolve()
    if not in_csv.exists():
        raise SystemExit(f"Universe CSV not found: {in_csv}")
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    if args.symbols.strip():
        symbols = []
        for raw in args.symbols.split(","):
            s = _norm_symbol(raw)
            if s:
                symbols.append(s)
    else:
        symbols = list(_iter_symbols_from_csv(in_csv))
    if args.limit and args.limit > 0:
        symbols = symbols[: args.limit]

    s = requests.Session()
    # Avoid inheriting system proxy env vars that can cause 403 tunnel failures.
    s.trust_env = False
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.screener.in/",
        }
    )

    rows: list[dict] = []
    ok = 0
    fail = 0
    for idx, sym in enumerate(symbols, start=1):
        slug = _slug_for_screener(sym)
        url = f"https://www.screener.in/company/{slug}/"
        status = "ok"
        err = ""
        q_latest = q_base = q_yoy = None
        a_latest = a_prev = a_yoy = None
        try:
            r = s.get(url, timeout=args.timeout)
            if r.status_code != 200:
                raise RuntimeError(f"http_{r.status_code}")
            q_labels, q_vals, a_labels, a_vals = _extract_eps_series(r.text)
            q_latest, q_base, q_yoy = _calc_qtr_yoy(q_vals)
            a_latest, a_prev, a_yoy = _calc_ann_yoy(a_labels, a_vals)
            if q_latest is None and a_latest is None:
                status = "no_eps_rows"
                fail += 1
            else:
                ok += 1
        except Exception as ex:
            status = "error"
            err = str(ex)[:180]
            fail += 1

        rows.append(
            {
                "symbol": sym,
                "screener_slug": slug,
                "q_eps_latest": "" if q_latest is None else f"{q_latest:.4f}",
                "q_eps_yoy_base": "" if q_base is None else f"{q_base:.4f}",
                "q_eps_yoy_pct": "" if q_yoy is None else f"{q_yoy:.4f}",
                "a_eps_latest": "" if a_latest is None else f"{a_latest:.4f}",
                "a_eps_prev": "" if a_prev is None else f"{a_prev:.4f}",
                "a_eps_yoy_pct": "" if a_yoy is None else f"{a_yoy:.4f}",
                "fetch_status": status,
                "error": err,
            }
        )

        if idx % 25 == 0 or idx == len(symbols):
            print(f"[{idx}/{len(symbols)}] ok={ok} fail={fail}")
        time.sleep(max(0.0, args.sleep_sec) + random.uniform(0.05, 0.25))

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "symbol",
                "screener_slug",
                "q_eps_latest",
                "q_eps_yoy_base",
                "q_eps_yoy_pct",
                "a_eps_latest",
                "a_eps_prev",
                "a_eps_yoy_pct",
                "fetch_status",
                "error",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_csv}")
    print(f"Success: {ok}  Fail: {fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

