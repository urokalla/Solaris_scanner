#!/usr/bin/env python3
"""
Download one Screener.in **market** table to CSV (company slugs from /company/ links).

Examples::

  Power (canonical Explore path): /market/IN11/IN1101/IN110101/
  Aerospace & Defense: /market/IN07/IN0702/IN070201/

For all sectors use: scripts/sync_screener_sector_csvs.py

Usage::
  cd stock_scanner_sovereign && PYTHONPATH=. python3 scripts/fetch_screener_market_sector.py \\
    --path /market/IN07/IN0702/IN070201/ --out-code IN070201
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.screener_market_csv import MARKET_DIR, download_market_sector_csv  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="", help="Full https URL (optional if --path set)")
    ap.add_argument(
        "--path",
        default="",
        help="Market path e.g. /market/IN11/IN1101/IN110101/",
    )
    ap.add_argument(
        "--out-code",
        default="",
        help="Output filename stem (e.g. IN110101); default: last segment of path",
    )
    ap.add_argument("--out-slug", default="", help="Deprecated alias for --out-code")
    ap.add_argument("--timeout", type=int, default=45)
    args = ap.parse_args()

    path = (args.path or "").strip()
    url = (args.url or "").strip()
    if not path and url:
        # extract path from origin URL
        from urllib.parse import urlparse

        p = urlparse(url)
        path = p.path or ""
    if not path:
        path = "/market/IN11/IN1101/IN110101/"

    code = (args.out_code or args.out_slug or "").strip()
    if not code:
        code = path.rstrip("/").rsplit("/", 1)[-1]

    MARKET_DIR.mkdir(parents=True, exist_ok=True)
    out = MARKET_DIR / f"{code}.csv"
    n = download_market_sector_csv(market_path=path, out_csv=out, timeout=args.timeout)
    print(f"Wrote {out} ({n} rows)")


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
