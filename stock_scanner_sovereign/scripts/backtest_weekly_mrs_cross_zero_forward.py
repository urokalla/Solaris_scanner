#!/usr/bin/env python3
"""
Event study: **weekly Mansfield mRS** crosses **above 0** → forward ~1y return.

Weekly bars: last daily close per ISO week (``week_end_close``, Asia/Kolkata), same as
``RSMathEngine.calculate_rs`` / ``utils/mrs_weekly_dynamics.weekly_mrs_asof_batch``:

  ratio_w = stock_wk_close / bench_wk_close
  sma = mean(ratio over **52 prior weeks**, current week excluded)
  w_mrs = ((ratio_w / sma) - 1) * 10

Signal: prior week ``w_mrs <= 0`` and this week ``w_mrs > 0``.

Entry: **close** of the **last daily session in the signal week** (aligned to week bucket end).
Exit: close **N** trading days later (default **252** ≈ 1 US year; Indian markets ~similar).

Usage:
  PIPELINE_DATA_DIR=... python3 scripts/backtest_weekly_mrs_cross_zero_forward.py
  python3 scripts/backtest_weekly_mrs_cross_zero_forward.py --forward-days 252 --prior-weeks 52
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from utils.constants import BENCHMARK_MAP  # noqa: E402
from utils.monthly_rsi2_trade_rules import week_end_close  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


def _load_close(path: str) -> pd.Series | None:
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
    return out.set_index("ts")["close"].sort_index()


def weekly_mrs_mansfield(stock_daily: pd.Series, bench_daily: pd.Series, prior_weeks: int) -> pd.Series:
    """Weekly mRS on week-end closes; ``prior_weeks`` prior ratios only (current week excluded)."""
    common = stock_daily.index.intersection(bench_daily.index)
    s = stock_daily.reindex(common).astype(float)
    b = bench_daily.reindex(common).astype(float).replace(0, np.nan)
    m = s.notna() & b.notna()
    s, b = s[m], b[m]
    w_s = week_end_close(s)
    w_b = week_end_close(b)
    common_w = w_s.index.intersection(w_b.index)
    w_s = w_s.reindex(common_w).dropna()
    w_b = w_b.reindex(common_w).astype(float).replace(0, np.nan)
    ratio = w_s / w_b
    ratio = ratio.replace(0, np.nan)
    sma = ratio.shift(1).rolling(prior_weeks, min_periods=prior_weeks).mean()
    return ((ratio / sma) - 1.0) * 10.0


def _iloc_at_or_before(s: pd.Series, ts: pd.Timestamp) -> int | None:
    """Last integer position with ``s.index[i] <= ts``."""
    if s.empty:
        return None
    idx = s.index.searchsorted(ts, side="right") - 1
    if idx < 0:
        return None
    return int(idx)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument(
        "--forward-days",
        type=int,
        default=252,
        help="Trading sessions after entry (252 ≈ 1 year)",
    )
    ap.add_argument("--prior-weeks", type=int, default=52, help="Prior weeks in ratio SMA (scanner weekly)")
    ap.add_argument("--data-dir", default=os.getenv("PIPELINE_DATA_DIR", "/app/data/historical"))
    ap.add_argument("--min-weeks", type=int, default=60, help="Min aligned weekly bars before counting crosses")
    ap.add_argument("--limit-symbols", type=int, default=0)
    ap.add_argument("--signal-after", default="", help="YYYY-MM-DD optional (matches signal week end >= this)")
    args = ap.parse_args()

    bench_sym = BENCHMARK_MAP.get(args.universe, "NSE:NIFTY500-INDEX")
    bench_path = resolve_parquet_path(bench_sym, args.data_dir)
    if not bench_path:
        print("Bench parquet not found:", bench_sym, args.data_dir)
        return 1
    bench = _load_close(bench_path)
    if bench is None:
        print("Bench load failed")
        return 1

    fw = max(1, int(args.forward_days))
    p_w = max(3, int(args.prior_weeks))
    # Need enough daily history: ~5*p_w weeks + fw days
    min_daily = max(400, p_w * 7 + fw + 80)

    after = None
    if str(args.signal_after).strip():
        after = pd.Timestamp(args.signal_after, tz="UTC")

    syms = sorted(expected_symbols_for_universe(args.universe))
    if args.limit_symbols and args.limit_symbols > 0:
        syms = syms[: args.limit_symbols]

    rets: list[float] = []
    skipped = 0
    for sym in syms:
        sym_full = f"NSE:{sym}-EQ" if ":" not in sym else sym
        if "-EQ" not in sym_full.upper():
            sym_full = f"NSE:{sym}-EQ"
        path = resolve_parquet_path(sym_full, args.data_dir)
        if not path:
            skipped += 1
            continue
        stock = _load_close(path)
        if stock is None or len(stock) < min_daily:
            skipped += 1
            continue
        common = stock.index.intersection(bench.index)
        s = stock.reindex(common).dropna().astype(float)
        b = bench.reindex(s.index).astype(float)
        if len(s) < min_daily:
            skipped += 1
            continue

        w_mrs = weekly_mrs_mansfield(s, b, p_w)
        if len(w_mrs) < args.min_weeks:
            skipped += 1
            continue

        prev = w_mrs.shift(1)
        cross = (prev <= 0.0) & (w_mrs > 0.0) & np.isfinite(w_mrs) & np.isfinite(prev)

        for tw in w_mrs.index[cross.fillna(False)]:
            if after is not None:
                tw_u = tw.tz_convert("UTC") if getattr(tw, "tzinfo", None) else tw.tz_localize("UTC")
                au = after if getattr(after, "tzinfo", None) else after.tz_localize("UTC")
                if tw_u < au:
                    continue

            ent_i = _iloc_at_or_before(s, tw)
            if ent_i is None:
                continue
            if ent_i + fw >= len(s):
                continue
            entry = float(s.iloc[ent_i])
            exit_ = float(s.iloc[ent_i + fw])
            if not np.isfinite(entry) or entry <= 0 or not np.isfinite(exit_):
                continue
            rets.append(exit_ / entry - 1.0)

    if not rets:
        print("No events. skipped_symbols=", skipped)
        return 1

    a = np.asarray(rets, dtype=np.float64)
    print(
        f"Weekly mRS cross >0 | priors={p_w} weeks | forward={fw} sessions (~1y) | "
        f"universe={args.universe} bench={bench_sym} | events={len(a)}"
    )
    print(f"  mean 1y ret: {100*a.mean():.2f}%")
    print(f"  median:      {100*np.median(a):.2f}%")
    print(f"  win rate:    {100*(a>0).mean():.1f}%")
    print(f"  p25 / p75:   {100*np.percentile(a,25):.2f}% / {100*np.percentile(a,75):.2f}%")
    print(f"  skipped symbols: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
