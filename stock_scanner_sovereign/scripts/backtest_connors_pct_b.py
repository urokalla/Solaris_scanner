#!/usr/bin/env python3
"""
Larry Connors %b (Bollinger) mean-reversion backtest on local daily Parquet.

Rules (commonly cited from Connors' %b material):
  - BB: SMA(5), k=2 stdev on close
  - %b = (close - lower) / (upper - lower)
  - Long only: close > SMA(200)
  - Entry: buy at close when %b < 0.2 for 3 consecutive days (incl. today)
  - Exit: sell at close first day %b > 0.8 (or last bar if still open)

Examples:
  python scripts/backtest_connors_pct_b.py --universe "Nifty 500"
  python scripts/backtest_connors_pct_b.py --nifty50-index
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


@dataclass
class Trade:
    symbol: str
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    entry: float
    exit: float
    ret: float
    bars_held: int


def _load_daily_ohlcv(symbol: str, data_dir: str) -> pd.DataFrame | None:
    path = resolve_parquet_path(symbol, data_dir)
    if not path:
        return None
    try:
        df = pd.read_parquet(path)
    except Exception:
        return None
    cols = {c.lower(): c for c in df.columns}
    ts_col = cols.get("timestamp") or cols.get("ts")
    c_col = cols.get("close")
    if not all([ts_col, c_col]):
        return None
    out = df[[ts_col, c_col]].copy()
    out.columns = ["timestamp", "close"]
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    out = out.dropna(subset=["timestamp", "close"])
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    if out.empty:
        return None
    return out.set_index("timestamp")


def _indicators(close: pd.Series, bb_len: int, bb_k: float, sma_len: int) -> pd.DataFrame:
    mid = close.rolling(bb_len, min_periods=bb_len).mean()
    std = close.rolling(bb_len, min_periods=bb_len).std(ddof=0)
    upper = mid + bb_k * std
    lower = mid - bb_k * std
    width = upper - lower
    pct_b = (close - lower) / width.replace(0, np.nan)
    sma = close.rolling(sma_len, min_periods=sma_len).mean()
    low_band = (pct_b < 0.2).astype(np.int8)
    three_low = low_band.rolling(3, min_periods=3).sum() == 3
    entry = three_low & (close > sma)
    return pd.DataFrame({"pct_b": pct_b, "sma200": sma, "entry": entry})


def _simulate_trades(symbol: str, df: pd.DataFrame, fee_per_side: float) -> list[Trade]:
    close = df["close"].astype(float)
    ind = _indicators(close, bb_len=5, bb_k=2.0, sma_len=200)
    pct_b = ind["pct_b"]
    entry_sig = ind["entry"].fillna(False)

    trades: list[Trade] = []
    n = len(df)
    idx = df.index
    in_pos = False
    entry_price = 0.0
    entry_i = -1

    for i in range(n):
        if not in_pos:
            if i < 199:
                continue
            if bool(entry_sig.iloc[i]):
                entry_price = float(close.iloc[i]) * (1.0 + fee_per_side)
                if not np.isfinite(entry_price) or entry_price <= 0:
                    continue
                entry_i = i
                in_pos = True
        else:
            at_end = i == n - 1
            pb = pct_b.iloc[i]
            exit_sig = (np.isfinite(pb) and pb > 0.8) or at_end
            if exit_sig:
                raw_exit = float(close.iloc[i])
                exit_price = raw_exit * (1.0 - fee_per_side)
                if not np.isfinite(exit_price) or exit_price <= 0:
                    in_pos = False
                    continue
                ret = exit_price / entry_price - 1.0
                trades.append(
                    Trade(
                        symbol=symbol,
                        entry_ts=idx[entry_i],
                        exit_ts=idx[i],
                        entry=entry_price / (1.0 + fee_per_side),
                        exit=exit_price / (1.0 - fee_per_side),
                        ret=ret,
                        bars_held=i - entry_i,
                    )
                )
                in_pos = False
    return trades


def _summarize(trades: list[Trade]) -> dict[str, float | int]:
    if not trades:
        return {
            "n_trades": 0,
            "win_rate": float("nan"),
            "avg_ret": float("nan"),
            "median_ret": float("nan"),
            "avg_win": float("nan"),
            "avg_loss": float("nan"),
            "profit_factor": float("nan"),
            "avg_bars_held": float("nan"),
        }
    r = np.array([t.ret for t in trades], dtype=float)
    wins = r[r > 0]
    losses = r[r <= 0]
    gross_win = float(wins.sum()) if wins.size else 0.0
    gross_loss = float(losses.sum()) if losses.size else 0.0
    pf = gross_win / abs(gross_loss) if gross_loss < 0 else float("inf")
    return {
        "n_trades": len(trades),
        "win_rate": float((r > 0).mean()),
        "avg_ret": float(np.mean(r)),
        "median_ret": float(np.median(r)),
        "avg_win": float(np.mean(wins)) if wins.size else float("nan"),
        "avg_loss": float(np.mean(losses)) if losses.size else float("nan"),
        "profit_factor": float(pf),
        "avg_bars_held": float(np.mean([t.bars_held for t in trades])),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--nifty50-index",
        action="store_true",
        help="Backtest only daily NIFTY 50 spot data (NSE:NIFTY50-INDEX parquet). Ignores --universe.",
    )
    ap.add_argument(
        "--symbols",
        default=None,
        help='Comma-separated symbols (e.g. "NSE:NIFTY50-INDEX"). If set, --universe is ignored. '
        "Overridden by --nifty50-index.",
    )
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--fee-bps", type=float, default=0.0, help="Per-side cost as fraction (5 = 0.05%)")
    ap.add_argument("--max-symbols", type=int, default=0, help="0 = all")
    ap.add_argument("--start-date", default=None)
    ap.add_argument("--end-date", default=None)
    args = ap.parse_args()

    fee = max(0.0, args.fee_bps) / 10_000.0
    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    if args.nifty50_index:
        syms = ["NSE:NIFTY50-INDEX"]
        label = "NSE:NIFTY50-INDEX (Nifty 50 index daily)"
    elif args.symbols:
        syms = sorted({s.strip() for s in args.symbols.split(",") if s.strip()})
        label = f"symbols={args.symbols!r}"
    else:
        syms = sorted(expected_symbols_for_universe(args.universe))
        label = f"universe={args.universe!r}"
    if not syms:
        print(f"No symbols (use --symbols or --universe)")
        raise SystemExit(2)
    if args.max_symbols > 0:
        syms = syms[: args.max_symbols]

    sd = pd.Timestamp(args.start_date, tz="UTC") if args.start_date else None
    ed = pd.Timestamp(args.end_date, tz="UTC") if args.end_date else None

    all_trades: list[Trade] = []
    missing = 0
    too_short = 0

    for sym in syms:
        raw = _load_daily_ohlcv(sym, data_dir)
        if raw is None or raw.empty:
            missing += 1
            continue
        if sd is not None:
            raw = raw.loc[raw.index >= sd]
        if ed is not None:
            raw = raw.loc[raw.index <= ed]
        if raw.empty or len(raw) < 220:
            too_short += 1
            continue
        allTrades = _simulate_trades(sym, raw, fee_per_side=fee)
        all_trades.extend(allTrades)

    st = _summarize(all_trades)
    print(f"Connors %b backtest — {label}")
    print(f"Data dir: {data_dir}")
    print(f"Symbols requested: {len(syms)} | parquet missing: {missing} | history <220d after filter: {too_short}")
    if args.start_date or args.end_date:
        print(f"Date filter: {args.start_date!r} .. {args.end_date!r}")
    print(f"Fee per side: {args.fee_bps} bps")
    print("---")
    print(f"Total trades: {st['n_trades']}")
    if st["n_trades"]:
        print(f"Win rate:      {st['win_rate']:.2%}")
        print(f"Avg return:    {st['avg_ret']*100:.3f}% per trade (simple)")
        print(f"Median return: {st['median_ret']*100:.3f}%")
        print(f"Avg win:       {st['avg_win']*100:.3f}% | Avg loss: {st['avg_loss']*100:.3f}%")
        print(f"Profit factor: {st['profit_factor']:.2f}")
        print(f"Avg bars held: {st['avg_bars_held']:.1f}")
    print("---")
    if len(syms) <= 1:
        print("Note: Single series — stats are for this instrument only (not a stock universe).")
    else:
        print("Note: Pool is all trades across symbols (overlap in calendar not modeled as one portfolio).")


if __name__ == "__main__":
    main()
