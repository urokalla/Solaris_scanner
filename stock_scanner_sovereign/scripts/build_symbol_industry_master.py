#!/usr/bin/env python3
"""
Merge ``Industry`` / company / ISIN from all Nifty-style constituent CSVs into
``data/symbol_industry_master.csv``, then emit a long join from Screener browse
sectors → symbols (via ``data/screener_sector_to_nifty_industry.csv``).

Symbols without a row (e.g. only listed in ``NSE_EQ.csv``) appear in
``data/symbol_industry_gaps_nse_eq.csv`` for a later backfill / pull.

Run from ``stock_scanner_sovereign``::

    PYTHONPATH=. python3 scripts/build_symbol_industry_master.py
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from utils.screener_sector_bridge import (  # noqa: E402
    DEFAULT_MASTER_FILE,
    SCREENER_SECTORS_FILE,
    SCREENER_TO_NIFTY_FILE,
    load_screener_sectors,
    load_screener_to_nifty,
)

# Higher index = lower priority (only fills symbols not yet seen).
_CSV_PRIORITY = [
    "data/nifty500.csv",
    "data/nifty_total_market.csv",
    "data/nifty500_healthcare.csv",
    "data/nifty100.csv",
    "data/nifty50.csv",
    "data/nifty_midcap150.csv",
    "data/nifty_midcap100.csv",
    "data/nifty_smallcap250.csv",
    "data/nifty_smallcap100.csv",
    "data/banknifty.csv",
]


def _to_nse_eq(sym: str, series: str | None) -> str:
    s = str(sym or "").strip().upper()
    if not s:
        return ""
    if s.startswith("NSE:"):
        return s if s.endswith(("-EQ", "-BE", "-SM", "-ST")) else f"{s}-EQ"
    if "INDEX" in s:
        return f"NSE:{s}" if s.startswith("NSE:") else f"NSE:{s}"
    suf = (str(series or "EQ").strip().upper() or "EQ")
    if suf not in {"EQ", "BE", "SM", "ST"}:
        suf = "EQ"
    return f"NSE:{s}-{suf}"


def _rows_from_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        fn = [h for h in (r.fieldnames or []) if h]
        low = {h.lower(): h for h in fn}
        if "symbol" not in low:
            return []
        c_sym = low["symbol"]
        c_ind = low.get("industry")
        if not c_ind:
            return []
        c_co = low.get("company name") or low.get("company_name") or low.get("security name")
        c_isin = low.get("isin code") or low.get("isin")
        c_series = low.get("series")
        out: list[dict[str, str]] = []
        for row in r:
            sym = _to_nse_eq(row.get(c_sym), row.get(c_series) if c_series else None)
            if not sym:
                continue
            out.append(
                {
                    "symbol_nse": sym,
                    "company_name": (row.get(c_co) or "").strip() if c_co else "",
                    "industry": (row.get(c_ind) or "").strip(),
                    "isin": (row.get(c_isin) or "").strip() if c_isin else "",
                    "source_csv": path.name,
                }
            )
        return out


def build_master() -> list[dict[str, str]]:
    acc: dict[str, dict[str, str]] = {}
    for rel in _CSV_PRIORITY:
        p = _ROOT / rel
        if not p.is_file():
            continue
        for row in _rows_from_csv(p):
            k = row["symbol_nse"]
            if k not in acc:
                acc[k] = row
    return list(acc.values())


def _nse_eq_symbols() -> set[str]:
    p = _ROOT / "data" / "NSE_EQ.csv"
    if not p.is_file():
        return set()
    with p.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        c = next((h for h in (r.fieldnames or []) if h.lower() == "symbol"), (r.fieldnames or ["Symbol"])[0])
        return {_to_nse_eq(row.get(c), "EQ") for row in r if row.get(c)}


def main() -> None:
    os.chdir(_ROOT)
    master = build_master()
    master.sort(key=lambda x: x["symbol_nse"])
    DEFAULT_MASTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_MASTER_FILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["symbol_nse", "company_name", "industry", "isin", "source_csv"],
        )
        w.writeheader()
        w.writerows(master)

    nse = _nse_eq_symbols()
    mset = {r["symbol_nse"] for r in master}
    gaps = sorted(nse - mset)
    gap_path = _ROOT / "data" / "symbol_industry_gaps_nse_eq.csv"
    with gap_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol_nse", "note"])
        for s in gaps:
            w.writerow([s, "no Industry in merged Nifty CSVs; backfill from disclosures / Screener / vendor"])

    sectors = load_screener_sectors()
    mp = load_screener_to_nifty()
    long_path = _ROOT / "data" / "screener_sector_symbols_long.csv"
    with long_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "screener_sector",
                "nifty_industry",
                "symbol_nse",
                "company_name",
                "industry",
                "in_nse_eq",
            ],
        )
        w.writeheader()
        for sec in sectors:
            nifty = mp.get(sec, "")
            for row in master:
                if nifty and row.get("industry") == nifty:
                    sym = row["symbol_nse"]
                    w.writerow(
                        {
                            "screener_sector": sec,
                            "nifty_industry": nifty,
                            "symbol_nse": sym,
                            "company_name": row.get("company_name", ""),
                            "industry": row.get("industry", ""),
                            "in_nse_eq": str(sym in nse).lower(),
                        }
                    )

    print(f"Wrote {DEFAULT_MASTER_FILE} ({len(master)} symbols)")
    print(f"Wrote {gap_path} ({len(gaps)} NSE_EQ symbols lacking industry merge)")
    print(f"Wrote {long_path} (Screener sector × symbol long table)")

    warn = [s for s in sectors if s not in mp]
    if warn:
        print("WARN: Screener sectors missing bridge row:", len(warn))
        for s in warn[:10]:
            print(" ", repr(s))
        if len(warn) > 10:
            print("  ...")


if __name__ == "__main__":
    main()
