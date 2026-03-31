#!/usr/bin/env python3
"""
Event study: weekly Wilder RSI(period=2) **strictly below** a threshold, optional **weekly mRS** floor.

Weekly mRS (when ``--min-weekly-mrs`` is set): same formula as ``RSMathEngine`` — ratio of
(stock/bench) on Friday IST week-closes vs trailing 52-week SMA of that ratio (shifted),
then ``((ratio/sma) - 1) * 10``.

Universe: Nifty 500 (from canonical CSV). Uses Friday-week closes in **Asia/Kolkata**
(same as ``week_end_close`` / dashboard W_RSI2).

Signal: each **completed** week with WRSI2 < threshold; if ``--min-weekly-mrs`` set, also require
weekly mRS **strictly greater** than that value (needs ``--bench`` Parquet).

Forward: **N forward weeks** on **weekly closes**:
  return = close(week t+N) / close(week t) - 1

Success rate: fraction of events with return > 0.

Examples:
  python scripts/backtest_wrsi2_below_forward_weeks.py
  python scripts/backtest_wrsi2_below_forward_weeks.py --threshold 2 --forward-weeks 3
  python scripts/backtest_wrsi2_below_forward_weeks.py --threshold 2 --min-weekly-mrs 3 --forward-weeks 3
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.monthly_rsi2_trade_rules import rsi_wilder, week_end_close  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


def _load_close(symbol: str, data_dir: str) -> pd.Series | None:
    path = resolve_parquet_path(symbol, data_dir)
    if not path:
        return None
    try:
        df = pd.read_parquet(path)
    except Exception:
        return None
    cm = {c.lower(): c for c in df.columns}
    ts_col = cm.get("timestamp") or cm.get("ts")
    c_col = cm.get("close")
    if not ts_col or not c_col:
        return None
    out = df[[ts_col, c_col]].copy()
    out.columns = ["ts", "close"]
    out["ts"] = pd.to_datetime(out["ts"], errors="coerce", utc=True)
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out = out.dropna().sort_values("ts").drop_duplicates(subset=["ts"], keep="last")
    if out.empty:
        return None
    return out.set_index("ts")["close"]


def _weekly_mrs_aligned(stock_close: pd.Series, bench_close: pd.Series) -> tuple[pd.Series, pd.Series] | None:
    """
    Weekly closes (stock) and weekly mRS on same index (intersection with bench weeks).
    Returns (w_close_stock, weekly_mrs) or None if insufficient overlap.
    """
    bc = bench_close.reindex(stock_close.index).ffill()
    w_s = week_end_close(stock_close.astype(float))
    w_b = week_end_close(bc.astype(float))
    idx = w_s.index.intersection(w_b.index)
    if len(idx) < 60:
        return None
    w_s = w_s.reindex(idx).astype(float)
    w_b = w_b.reindex(idx).astype(float)
    ratio = w_s / w_b.replace(0, np.nan)
    sma = ratio.shift(1).rolling(52, min_periods=52).mean()
    wmrs = ((ratio / sma) - 1.0) * 10.0
    return w_s, wmrs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--threshold", type=float, default=2.0, help="Signal when WRSI2 **strictly below** this")
    ap.add_argument("--forward-weeks", type=int, default=3, help="Forward horizon in weekly closes")
    ap.add_argument("--rsi-period", type=int, default=2)
    ap.add_argument("--min-weekly-bars", type=int, default=8)
    ap.add_argument("--max-symbols", type=int, default=0, help="0 = all")
    ap.add_argument(
        "--min-weekly-mrs",
        type=float,
        default=None,
        help="If set, require weekly mRS **>** this (e.g. 3). Loads --bench for ratio.",
    )
    ap.add_argument("--bench", default="NSE:NIFTY500-INDEX", help="Benchmark for weekly mRS")
    args = ap.parse_args()

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    fw = max(1, int(args.forward_weeks))
    use_mrs = args.min_weekly_mrs is not None

    bench_series: pd.Series | None = None
    if use_mrs:
        bench_series = _load_close(args.bench, data_dir)
        if bench_series is None or bench_series.empty:
            print(f"Missing benchmark closes for weekly mRS: {args.bench}")
            sys.exit(1)

    syms = sorted(expected_symbols_for_universe(args.universe))
    if args.max_symbols > 0:
        syms = syms[: args.max_symbols]

    rets: list[float] = []
    meta: list[tuple[str, pd.Timestamp, float, float, float]] = []  # sym, week_end, wrsi2, wmrs, ret

    n_loaded = 0
    for k, sym in enumerate(syms):
        if k % 75 == 0:
            print(f"Scanning {k}/{len(syms)}…", flush=True)
        sc = _load_close(sym, data_dir)
        if sc is None or len(sc) < 200:
            continue
        if use_mrs:
            assert bench_series is not None
            aligned = _weekly_mrs_aligned(sc, bench_series)
            if aligned is None:
                continue
            w, wmrs = aligned
        else:
            w = week_end_close(sc.astype(float))
            wmrs = None
        if len(w) < args.min_weekly_bars + fw:
            continue
        r = rsi_wilder(w, period=args.rsi_period)
        n_loaded += 1
        thr_m = float(args.min_weekly_mrs) if use_mrs else None
        for i in range(0, len(w) - fw):
            rv = float(r.iloc[i])
            if not np.isfinite(rv) or rv >= args.threshold:
                continue
            if use_mrs and wmrs is not None:
                mv = float(wmrs.iloc[i])
                if not np.isfinite(mv) or mv <= thr_m:
                    continue
            else:
                mv = float("nan")
            c0 = float(w.iloc[i])
            c1 = float(w.iloc[i + fw])
            if c0 <= 0 or not np.isfinite(c0) or not np.isfinite(c1):
                continue
            ret = c1 / c0 - 1.0
            rets.append(ret)
            meta.append((sym, w.index[i], rv, mv, ret))

    arr = np.array(rets, dtype=float)
    print(f"\nUniverse: {args.universe} | symbols with enough weekly history: {n_loaded}")
    mrs_line = (
        f" AND weekly mRS > {args.min_weekly_mrs} vs {args.bench}"
        if use_mrs
        else " (no mRS filter)"
    )
    print(f"Signal: weekly RSI({args.rsi_period}) < {args.threshold}{mrs_line}")
    print(f"Forward: {fw} weekly closes")
    print(f"Events: {len(arr)}")
    if len(arr) == 0:
        return

    wins = (arr > 0).mean() * 100.0
    print(f"Success rate (ret > 0): {wins:.2f}%")
    print(f"Mean return:   {arr.mean() * 100:.3f}%")
    print(f"Median return: {np.median(arr) * 100:.3f}%")
    print(f"Std return:    {arr.std() * 100:.3f}%")
    print(f"Worst / Best:  {arr.min() * 100:.2f}% / {arr.max() * 100:.2f}%")

    meta.sort(key=lambda x: x[1])
    print("\nLast 10 events:")
    for row in meta[-10:]:
        sym, ts, wr, mv, rt = row
        mpart = f" W_mRS={mv:.2f}" if use_mrs and np.isfinite(mv) else ""
        print(f"  {ts.date()} {sym} WRSI2={wr:.2f}{mpart}  {fw}w_ret={rt*100:.2f}%")


if __name__ == "__main__":
    main()
