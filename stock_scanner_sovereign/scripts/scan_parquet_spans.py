#!/usr/bin/env python3
"""
List every `*.parquet` under PIPELINE_DATA_DIR and report calendar-day span vs ~5 years.

Usage (repo root or stock_scanner_sovereign on PYTHONPATH):
  python scripts/scan_parquet_spans.py
  python scripts/scan_parquet_spans.py --data-dir /path/to/historical
  python scripts/scan_parquet_spans.py --json
  python scripts/scan_parquet_spans.py --only-short
"""
from __future__ import annotations

import argparse
import json
import os
import sys

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.universe_history_audit import MIN_YEARS_DEFAULT, audit_parquet_file  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify which Parquet files span ~5 years of daily history.")
    ap.add_argument("--data-dir", default=None, help="Override PIPELINE_DATA_DIR")
    ap.add_argument("--min-years", type=float, default=MIN_YEARS_DEFAULT, help="Target years (calendar)")
    ap.add_argument("--json", action="store_true", help="Print JSON summary")
    ap.add_argument("--only-short", action="store_true", help="Only files below min-years")
    ap.add_argument("--limit", type=int, default=0, help="Max files to scan (0=all)")
    args = ap.parse_args()

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    if not os.path.isdir(data_dir):
        print(f"Not a directory: {data_dir}", file=sys.stderr)
        sys.exit(2)

    files = sorted(f for f in os.listdir(data_dir) if f.endswith(".parquet"))
    if args.limit > 0:
        files = files[: args.limit]

    rows_out: list[dict] = []
    ok_n = short_n = bad_n = 0

    for name in files:
        path = os.path.join(data_dir, name)
        r = audit_parquet_file(path, min_years=args.min_years)
        r["basename"] = name
        rows_out.append(r)
        if r.get("ok") is True:
            ok_n += 1
        elif r.get("status") in ("empty_or_unreadable", "missing"):
            bad_n += 1
        else:
            short_n += 1

    summary = {
        "data_dir": data_dir,
        "min_years": args.min_years,
        "files_scanned": len(files),
        "meet_5y_span": ok_n,
        "short_or_insufficient": short_n,
        "empty_or_unreadable": bad_n,
        "per_file": [x for x in rows_out if not args.only_short or not x.get("ok")],
    }

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
        sys.exit(0)

    print(f"Directory: {data_dir}")
    print(f"Threshold: ~{args.min_years} calendar years (same slack as universe audit)")
    print(f"Scanned: {len(files)} parquet files")
    print(f"Meet span: {ok_n} | Short: {short_n} | Bad/empty: {bad_n}")
    print("-" * 72)

    for r in rows_out:
        if args.only_short and r.get("ok"):
            continue
        base = r.get("basename", os.path.basename(r["file"]))
        if r.get("ok"):
            tag = "OK_5Y"
        elif r.get("status") == "short_span":
            tag = "SHORT"
        else:
            tag = r.get("status", "?").upper()
        sd = r.get("span_days")
        span_s = f"{sd}d" if sd is not None else "n/a"
        rows_c = r.get("rows", 0)
        print(f"{tag:12} {span_s:>8} rows={rows_c:<7} {base}")

    sys.exit(0)


if __name__ == "__main__":
    main()
