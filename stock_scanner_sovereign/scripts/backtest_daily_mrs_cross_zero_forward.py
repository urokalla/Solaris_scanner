#!/usr/bin/env python3
"""
Event study: **Mansfield-style daily mRS** crosses **above 0**.

Definition matches ``scripts/backtest_rising_wrsi2_atr3._daily_mrs_components`` (daily line):
  ratio[t] = stock_close / bench_close
  sma[t] = mean(ratio[t-52], …, ratio[t-1])   # **52** prior sessions, **excluding** today
  d_mrs[t] = ((ratio[t] / sma[t]) - 1) * 10

(The live grid **D_mRS** uses a longer scanner window via ``MRS_DAILY_LOOKBACK``; use
``--scanner-daily`` to back test that instead.)

Signal: ``d_mrs[t-1] <= 0`` and ``d_mrs[t] > 0``.

Forward: holding return from signal **close** to close **N** trading sessions later
(default N=5 ≈ one week).

Usage:
  PIPELINE_DATA_DIR=/path/to/historical python3 scripts/backtest_daily_mrs_cross_zero_forward.py
  python3 scripts/backtest_daily_mrs_cross_zero_forward.py --universe "Nifty 500" --forward-days 5
  python3 scripts/backtest_daily_mrs_cross_zero_forward.py --scanner-daily   # grid parity (55 priors if LOOKBACK=56)
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


def daily_mrs_sma_prior_excl_today(stock: pd.Series, bench: pd.Series, prior_days: int) -> pd.Series:
    """SMA of (stock/bench) ratio over the previous `prior_days` bars only — today excluded."""
    b = bench.reindex(stock.index).astype(float).replace(0, np.nan)
    ratio = stock.astype(float) / b
    ratio = ratio.replace(0, np.nan)
    sma = ratio.shift(1).rolling(prior_days, min_periods=prior_days).mean()
    return ((ratio / sma) - 1.0) * 10.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--forward-days", type=int, default=5, help="Trading sessions after signal (5 ≈ 1 week)")
    ap.add_argument(
        "--prior-days",
        type=int,
        default=0,
        help="Prior sessions in ratio SMA (0 = use Mansfield default 52, or scanner mode)",
    )
    ap.add_argument(
        "--scanner-daily",
        action="store_true",
        help="Use grid parity: prior count = MRS_DAILY_LOOKBACK - 1 (default 55 when LOOKBACK=56)",
    )
    ap.add_argument("--data-dir", default=os.getenv("PIPELINE_DATA_DIR", "/app/data/historical"))
    ap.add_argument("--min-history", type=int, default=120)
    ap.add_argument("--limit-symbols", type=int, default=0, help="0 = all resolved symbols")
    ap.add_argument("--signal-after", default="", help="YYYY-MM-DD UTC optional")
    args = ap.parse_args()

    mansfield_prior = 52
    if args.scanner_daily:
        look = max(5, int(os.getenv("MRS_DAILY_LOOKBACK", "56")))
        prior_days = look - 1
        label = f"scanner D_mRS priors={prior_days} (MRS_DAILY_LOOKBACK={look})"
    elif args.prior_days and args.prior_days > 0:
        prior_days = int(args.prior_days)
        label = f"custom priors={prior_days}"
    else:
        prior_days = mansfield_prior
        label = f"Mansfield daily mRS priors={prior_days}"

    bench_sym = BENCHMARK_MAP.get(args.universe, "NSE:NIFTY500-INDEX")
    bench_path = resolve_parquet_path(bench_sym, args.data_dir)
    if not bench_path:
        print("Bench parquet not found:", bench_sym, args.data_dir)
        return 1
    bench = _load_close(bench_path)
    if bench is None or len(bench) < args.min_history + args.forward_days + 10:
        print("Bench history too short")
        return 1

    syms = sorted(expected_symbols_for_universe(args.universe))
    if args.limit_symbols and args.limit_symbols > 0:
        syms = syms[: args.limit_symbols]

    fw = max(1, int(args.forward_days))
    sma_d = max(3, prior_days)
    after = pd.Timestamp(args.signal_after, tz="UTC") if str(args.signal_after).strip() else None

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
        if stock is None or len(stock) < args.min_history:
            skipped += 1
            continue
        common = stock.index.intersection(bench.index)
        if len(common) < args.min_history + fw + 5:
            skipped += 1
            continue
        s = stock.reindex(common).dropna()
        b = bench.reindex(common).dropna()
        common2 = s.index.intersection(b.index)
        s = s.reindex(common2).astype(float)
        b = b.reindex(common2).astype(float)
        if len(s) < args.min_history + fw + 5:
            skipped += 1
            continue

        dm = daily_mrs_sma_prior_excl_today(s, b, sma_d)
        prev = dm.shift(1)
        cross = (prev <= 0.0) & (dm > 0.0) & np.isfinite(dm) & np.isfinite(prev)
        close = s

        # forward return: close[t+fw]/close[t] - 1
        fwd = close.shift(-fw) / close - 1.0

        sel = cross & fwd.notna()
        if after is not None:
            sel = sel & (sel.index >= after)

        r = fwd[sel].astype(float)
        rets.extend(r.dropna().tolist())

    if not rets:
        print("No events (check data_dir / universe). skipped_symbols=", skipped)
        return 1

    a = np.asarray(rets, dtype=np.float64)
    print(
        f"Daily mRS cross >0 | {label} | universe={args.universe} bench={bench_sym} | "
        f"forward={fw} sessions | events={len(a)}"
    )
    print(f"  mean 1w ret: {100*a.mean():.2f}%")
    print(f"  median:      {100*np.median(a):.2f}%")
    print(f"  win rate:    {100*(a>0).mean():.1f}%")
    print(f"  p25 / p75:   {100*np.percentile(a,25):.2f}% / {100*np.percentile(a,75):.2f}%")
    print(f"  skipped symbols (no data): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
