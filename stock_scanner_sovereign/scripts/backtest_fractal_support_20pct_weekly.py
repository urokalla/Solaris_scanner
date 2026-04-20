#!/usr/bin/env python3
"""
Weekly backtest: Williams-style down fractal (5 bars = 2+1+2) as *support*,
then measure (1) weeks until +20% from fractal low (forward high vs that low),
(2) whether support (fractal low) was broken before that 20% move.

5-bar down fractal at index i (middle bar):
  low[i] < low[i-1], low[i-2], low[i+1], low[i+2]
Confirmed after bar i+2 closes (uses two bars to the right of pivot).

Support = low[i]. Broken = any later week with low < support before 20% is hit
(or anytime before 20% if we stop at first break — we record first break week).

Output: aggregate stats + CSV per fractal event.

Not trading advice.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.isdir(os.path.join(_ROOT, "fyers_data_pipeline", "data", "historical")):
    HIST = os.path.join(_ROOT, "fyers_data_pipeline", "data", "historical")
else:
    HIST = os.environ.get("PIPELINE_DATA_DIR", os.path.join(_ROOT, "data", "historical"))

NIFTY500_CSV = os.path.join(_ROOT, "stock_scanner_sovereign", "data", "nifty500.csv")
TARGET_RETURN = 0.20
MAX_FORWARD_WEEKS = 260  # cap ~5y


def load_weekly(symbol_fyers: str) -> pd.DataFrame | None:
    clean = symbol_fyers.replace(":", "_").replace("-", "_")
    path = os.path.join(HIST, f"{clean}.parquet")
    if not os.path.isfile(path):
        return None
    df = pd.read_parquet(path)
    if df.empty or "timestamp" not in df.columns:
        return None
    df = df.sort_values("timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
    df = df.set_index("timestamp")
    w = df.resample("W-FRI").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    w = w.dropna(subset=["close"])
    if len(w) < 10:
        return None
    return w


def down_fractal_indices(low: pd.Series) -> list[int]:
    """Middle bar index i of each confirmed 5-bar down fractal (strict <)."""
    n = len(low)
    lv = low.values
    out: list[int] = []
    for i in range(2, n - 2):
        if lv[i] < lv[i - 1] and lv[i] < lv[i - 2] and lv[i] < lv[i + 1] and lv[i] < lv[i + 2]:
            out.append(i)
    return out


def analyze_fractal(
    weekly: pd.DataFrame,
    pivot_i: int,
) -> dict:
    """
    pivot_i = middle bar of 5-bar down fractal. Support = low there.
    Scan from bar pivot_i + 2 (first bar after full confirmation) forward.
    """
    high = weekly["high"].values
    low = weekly["low"].values
    idx = weekly.index
    n = len(weekly)
    support = float(low[pivot_i])
    start = pivot_i + 2  # first week we "know" fractal; could start from pivot_i+1 per taste

    weeks_to_20: int | None = None
    broken = False
    weeks_to_break: int | None = None
    max_run = 0.0

    for j in range(start, min(n, pivot_i + 2 + MAX_FORWARD_WEEKS)):
        # max high from start of forward scan to j (path to profit)
        mx = float(max(high[pivot_i : j + 1]))
        ret = mx / support - 1.0
        if ret > max_run:
            max_run = ret
        if low[j] < support and not broken:
            broken = True
            weeks_to_break = j - pivot_i
        if weeks_to_20 is None and ret >= TARGET_RETURN:
            weeks_to_20 = j - pivot_i

    # Break before first +20% week (same week as +20% counts as not broken-before if break after high made 20% — we use week index order).
    broken_before_20 = weeks_to_break is not None and (
        weeks_to_20 is None or weeks_to_break < weeks_to_20
    )

    return {
        "pivot_week": idx[pivot_i],
        "support": support,
        "weeks_to_20pct_from_pivot": weeks_to_20,
        "hit_20pct": weeks_to_20 is not None,
        "support_broken_before_20": broken_before_20,
        "first_break_weeks_from_pivot": weeks_to_break,
        "max_forward_return": max_run,
    }


def main() -> None:
    if not os.path.isfile(NIFTY500_CSV):
        print("Missing nifty500.csv", file=sys.stderr)
        sys.exit(1)
    uni = pd.read_csv(NIFTY500_CSV)
    sym_col = "Symbol" if "Symbol" in uni.columns else uni.columns[2]
    symbols = uni[sym_col].astype(str).str.strip().tolist()

    rows: list[dict] = []
    for sym in symbols:
        fy = f"NSE:{sym}-EQ"
        w = load_weekly(fy)
        if w is None:
            continue
        low = w["low"]
        for pivot_i in down_fractal_indices(low):
            r = analyze_fractal(w, pivot_i)
            r["symbol"] = sym
            rows.append(r)

    if not rows:
        print("No fractal events found.")
        sys.exit(0)

    df = pd.DataFrame(rows)
    hit = df["hit_20pct"]
    n = len(df)
    print("=== Weekly 5-bar down fractal (support) → +20% from fractal LOW ===\n")
    print(f"Total down-fractal events (Nifty 500 universe, all history): {n}")
    print(f"Reached +{int(TARGET_RETURN * 100)}% (max high vs support low, any time forward): {int(hit.sum())} ({100 * hit.mean():.1f}%)")
    brk = df["support_broken_before_20"].astype(bool)
    print(f"Support broken before that +20% move: {int(brk.sum())} ({100 * brk.mean():.1f}% of all fractals)")
    sub = df[hit]
    if len(sub):
        wk = sub["weeks_to_20pct_from_pivot"].astype(float)
        print(f"\nAmong those that hit +20%, weeks from pivot week to first +20% week:")
        print(f"  median: {wk.median():.0f}  mean: {wk.mean():.1f}  min: {wk.min():.0f}  max: {wk.max():.0f}")
    print("\n(‘Broken support’ = first week with weekly low < fractal low, before first +20% week if any.)\n")

    out_csv = os.path.join(_ROOT, "stock_scanner_sovereign", "data", "backtest_fractal_support_20pct_weekly.csv")
    df.to_csv(out_csv, index=False)
    print(f"Per-fractal CSV: {out_csv}")


if __name__ == "__main__":
    main()
