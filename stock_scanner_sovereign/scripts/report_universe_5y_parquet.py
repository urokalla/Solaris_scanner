#!/usr/bin/env python3
"""
For one universe: list each symbol with calendar span in Parquet vs ~5y threshold.
Uses same rule as utils/universe_history_audit (PIPELINE_DATA_DIR).

  python scripts/report_universe_5y_parquet.py --universe "Nifty Midcap 100"
"""
from __future__ import annotations

import argparse
import os
import sys

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.universe_history_audit import MIN_YEARS_DEFAULT, audit_symbol_parquet  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", required=True, help='e.g. "Nifty Midcap 100"')
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--min-years", type=float, default=MIN_YEARS_DEFAULT)
    args = ap.parse_args()

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    syms = sorted(expected_symbols_for_universe(args.universe))
    if not syms:
        print(f"No symbols for universe {args.universe!r} (missing CSV?)", file=sys.stderr)
        sys.exit(2)

    yes = no = bad = 0
    print("symbol\tspan_days\trows\tok_5y\tstatus")
    for s in syms:
        r = audit_symbol_parquet(s, data_dir, min_years=args.min_years)
        st = r.get("status", "?")
        sd = r.get("span_days")
        rows = r.get("rows", 0)
        ok = r.get("ok", False)
        if ok:
            yes += 1
        elif st in ("missing_file", "empty_or_unreadable"):
            bad += 1
        else:
            no += 1
        print(f"{s}\t{sd}\t{rows}\t{ok}\t{st}")

    print("---")
    print(f"universe={args.universe}\tdata_dir={data_dir}")
    print(f"total={len(syms)}\tmeet_5y={yes}\tshort_span={no}\tmissing_or_bad={bad}")


if __name__ == "__main__":
    main()
