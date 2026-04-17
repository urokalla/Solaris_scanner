#!/usr/bin/env python3
"""
One-shot fetch of NSE equity corporate announcements (same JSON API as the old Events sidecar).
Run manually or from cron — keeps the dashboard off NSE when Events reads the CSV only.

  python scripts/fetch_nse_corporate_announcements.py --days 7

Writes: stock_scanner_sovereign/data/nse_corporate_announcements.csv

Optional: scripts/nse_announcement_summarize.py can build
data/nse_corporate_announcement_summaries.json (disabled in docker by default).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from pathlib import Path

import requests

NSE_HOME = "https://www.nseindia.com"
OUT_COLS = ("symbol", "desc", "an_dt", "attchmntFile")


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch NSE corporate announcements JSON → CSV snapshot.")
    p.add_argument("--days", type=int, default=7, help="Lookback calendar days (inclusive of today).")
    p.add_argument(
        "--out",
        default="",
        help="Output CSV path relative to stock_scanner_sovereign (default: data/nse_corporate_announcements.csv).",
    )
    p.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds.")
    args = p.parse_args()

    repo = Path(__file__).resolve().parents[1]
    out_rel = (args.out or "data/nse_corporate_announcements.csv").strip()
    out_path = (repo / out_rel).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    to_d = dt.date.today()
    from_d = to_d - dt.timedelta(days=max(args.days, 1) - 1)
    params = {
        "index": "equities",
        "from_date": from_d.strftime("%d-%m-%Y"),
        "to_date": to_d.strftime("%d-%m-%Y"),
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{NSE_HOME}/companies-listing/corporate-filings-announcements",
    }
    s = requests.Session()
    s.headers.update(headers)
    s.get(NSE_HOME, timeout=args.timeout)
    r = s.get(f"{NSE_HOME}/api/corporate-announcements", params=params, timeout=args.timeout)
    r.raise_for_status()
    data = r.json()
    rows_in = data if isinstance(data, list) else []

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(OUT_COLS), extrasaction="ignore")
        w.writeheader()
        for x in rows_in:
            if not isinstance(x, dict):
                continue
            w.writerow(
                {
                    "symbol": str(x.get("symbol") or ""),
                    "desc": str(x.get("desc") or ""),
                    "an_dt": str(x.get("an_dt") or ""),
                    "attchmntFile": str(x.get("attchmntFile") or ""),
                }
            )

    print(f"Wrote {len(rows_in):,} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
