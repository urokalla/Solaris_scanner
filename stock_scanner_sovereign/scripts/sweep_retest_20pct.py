#!/usr/bin/env python3
"""
Find higher-probability 20% patterns from retest backtest events CSV.

Input CSV is expected from:
  scripts/backtest_breakout_retest_preset.py --dump-csv ...
"""
from __future__ import annotations

import argparse
import itertools
import os

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to events CSV")
    ap.add_argument("--min-events", type=int, default=150)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    path = os.path.abspath(args.csv)
    df = pd.read_csv(path)
    need = {"status", "mrs", "pct_vs_brk", "max_ret_20", "max_ret_40"}
    miss = need - set(df.columns)
    if miss:
        raise SystemExit(f"Missing columns in CSV: {sorted(miss)}")
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["mrs", "pct_vs_brk", "max_ret_20", "max_ret_40"])
    if df.empty:
        raise SystemExit("No valid rows in CSV.")

    status_modes = {
        "BUY_ONLY": ["BUY NOW"],
        "TREND_ONLY": ["TRENDING"],
        "BUY_OR_TREND": ["BUY NOW", "TRENDING"],
    }
    mrs_mins = [0.0, 0.5, 1.0, 2.0, 4.0, 6.0]
    mrs_maxs = [2.0, 4.0, 6.0, 10.0, 20.0, 50.0, 100.0]
    pct_lows = [-2.0, -1.5, -1.0, -0.5, 0.0]
    pct_highs = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

    rows = []
    for status_name, statuses in status_modes.items():
        d0 = df[df["status"].isin(statuses)]
        for mn, mx, pl, ph in itertools.product(mrs_mins, mrs_maxs, pct_lows, pct_highs):
            if mx <= mn or ph <= pl:
                continue
            d = d0[(d0["mrs"] >= mn) & (d0["mrs"] <= mx) & (d0["pct_vs_brk"] >= pl) & (d0["pct_vs_brk"] <= ph)]
            n = len(d)
            if n < int(args.min_events):
                continue
            hit20_20 = float((d["max_ret_20"] >= 0.20).mean() * 100.0)
            hit20_40 = float((d["max_ret_40"] >= 0.20).mean() * 100.0)
            med20 = float(d["max_ret_20"].median() * 100.0)
            dd20 = float(d["dd_20"].median() * 100.0) if "dd_20" in d.columns else float("nan")
            rows.append(
                {
                    "status_mode": status_name,
                    "mrs_min": mn,
                    "mrs_max": mx,
                    "pct_low": pl,
                    "pct_high": ph,
                    "events": n,
                    "hit20_20d_pct": hit20_20,
                    "hit20_40d_pct": hit20_40,
                    "median_maxret20_pct": med20,
                    "median_dd20_pct": dd20,
                    # balanced score avoids tiny-sample overfit while preferring 20d 20% hit-rate
                    "score": hit20_20 * np.log10(n),
                }
            )

    if not rows:
        print("No parameter sets matched min-events threshold.")
        return

    out = pd.DataFrame(rows).sort_values(["score", "hit20_20d_pct", "events"], ascending=[False, False, False])
    print(f"rows_tested={len(rows)}")
    print("--- top patterns ---")
    print(out.head(int(args.top)).to_string(index=False))


if __name__ == "__main__":
    main()

