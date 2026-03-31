#!/usr/bin/env python3
"""
Discover all **Browse sectors** on Screener Explore, refresh ``sector_index.json``,
and download each market listing to ``data/screener_market/<CODE>.csv``.

Run from ``stock_scanner_sovereign``::

    PYTHONPATH=. python3 scripts/sync_screener_sector_csvs.py
    PYTHONPATH=. python3 scripts/sync_screener_sector_csvs.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOV not in sys.path:
    sys.path.insert(0, SOV)

from pathlib import Path

from utils.screener_market_csv import (  # noqa: E402
    MARKET_DIR,
    discover_browse_sectors_from_explore,
    download_market_sector_csv,
    write_sector_index,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Only refresh sector_index.json, no CSV fetch")
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between sector downloads (avoids Screener 429). Default 2",
    )
    ap.add_argument(
        "--only-missing",
        action="store_true",
        help="Skip sectors that already have a CSV file",
    )
    args = ap.parse_args()

    sectors = discover_browse_sectors_from_explore(timeout=args.timeout)
    write_sector_index(sectors)
    print(f"Wrote sector index ({len(sectors)} sectors) -> {MARKET_DIR / 'sector_index.json'}")
    if args.dry_run:
        return

    import time as _time

    for i, s in enumerate(sectors):
        code = s["code"]
        path = MARKET_DIR / f"{code}.csv"
        if args.only_missing and path.is_file() and path.stat().st_size > 50:
            continue
        if i > 0 and args.delay > 0:
            _time.sleep(args.delay)
        try:
            n = download_market_sector_csv(
                market_path=s["market_path"],
                out_csv=path,
                timeout=args.timeout,
            )
            print(f"  OK {code}: {s['label'][:40]:40} ({n} tickers)")
        except Exception as e:
            print(f"  ERR {code} {s['label']}: {e}", file=sys.stderr)


if __name__ == "__main__":
    os.chdir(SOV)
    main()
