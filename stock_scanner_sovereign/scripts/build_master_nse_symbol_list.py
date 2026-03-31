#!/usr/bin/env python3
"""
Build a clean master NSE symbol list for "All NSE Stocks".

Sources:
1) local canonical list: stock_scanner_sovereign/data/available_symbols.txt
2) NSE shareholding master API symbols

Output:
- stock_scanner_sovereign/data/NSE_EQ.csv  (Symbol column, deduped, sorted)
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import requests


NSE_BASE = "https://www.nseindia.com"
SHAREHOLDING_API = f"{NSE_BASE}/api/corporate-share-holdings-master?index=equities"


def _norm_symbol(s: str) -> str:
    x = (s or "").strip().upper()
    if not x:
        return ""
    if x.startswith("NSE:"):
        x = x.split(":", 1)[1]
    if x.endswith("-EQ"):
        x = x[:-3]
    return x.strip()


def load_local_symbols(path: Path) -> set[str]:
    out: set[str] = set()
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        s = _norm_symbol(line)
        if s:
            out.add(s)
    return out


def fetch_shareholding_symbols(timeout_s: int) -> set[str]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
    }
    s = requests.Session()
    s.get(NSE_BASE, headers=headers, timeout=timeout_s)
    r = s.get(SHAREHOLDING_API, headers=headers, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    out: set[str] = set()
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            sym = _norm_symbol(str(row.get("symbol") or ""))
            if sym:
                out.add(sym)
    return out


def write_nse_eq_csv(path: Path, symbols: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Symbol"])
        for s in sorted(symbols):
            w.writerow([s])


def main() -> int:
    p = argparse.ArgumentParser(description="Build master NSE_EQ.csv symbol list.")
    p.add_argument(
        "--available-symbols-path",
        default="stock_scanner_sovereign/data/available_symbols.txt",
        help="Path to local available symbols text file.",
    )
    p.add_argument(
        "--out",
        default="stock_scanner_sovereign/data/NSE_EQ.csv",
        help="Output CSV path.",
    )
    p.add_argument("--timeout-s", type=int, default=30, help="HTTP timeout in seconds.")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    local_path = (repo_root / args.available_symbols_path).resolve()
    out_path = (repo_root / args.out).resolve()

    local = load_local_symbols(local_path)
    remote = fetch_shareholding_symbols(timeout_s=args.timeout_s)
    merged = local | remote

    write_nse_eq_csv(out_path, merged)

    print(f"local_symbols={len(local)}")
    print(f"shareholding_symbols={len(remote)}")
    print(f"merged_symbols={len(merged)}")
    print(f"wrote={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

