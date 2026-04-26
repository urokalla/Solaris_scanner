#!/usr/bin/env python3
"""
Weekly long-only backtest:
- Entry: close > Donchian high of prior N weeks (default 10), with EMA9 > EMA21
- Exit: ATR trailing stop only (default ATR period 9, multiplier 2.0)

Universe defaults to Nifty Total Market CSV.
Reads daily parquet from fyers_data_pipeline/data/historical and resamples to W-FRI.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HIST = os.path.join(ROOT, "fyers_data_pipeline", "data", "historical")


@dataclass
class Trade:
    symbol: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    exit: float
    ret_pct: float
    bars_held: int


def _load_symbols(csv_path: str) -> list[str]:
    df = pd.read_csv(csv_path)
    sym_col = "Symbol" if "Symbol" in df.columns else df.columns[2]
    return [str(s).strip().upper() for s in df[sym_col].dropna().tolist()]


def _parquet_path(symbol: str) -> str:
    fsym = f"NSE:{symbol}-EQ".replace(":", "_").replace("-", "_")
    return os.path.join(HIST, f"{fsym}.parquet")


def _weekly_ohlc(symbol: str) -> pd.DataFrame | None:
    p = _parquet_path(symbol)
    if not os.path.exists(p):
        return None
    d = pd.read_parquet(p)
    if d.empty or "timestamp" not in d.columns:
        return None
    d = d.sort_values("timestamp")
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True).dt.tz_localize(None)
    d = d.set_index("timestamp")
    w = d.resample("W-FRI").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    w = w.dropna(subset=["close"])
    if len(w) < 40:
        return None
    return w


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    pc = close.shift(1)
    tr = pd.concat([(high - low), (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def backtest_symbol(
    symbol: str, w: pd.DataFrame, donchian_n: int, atr_n: int, atr_mult: float
) -> list[Trade]:
    h, l, c = w["high"], w["low"], w["close"]
    ema9 = c.ewm(span=9, adjust=False).mean()
    ema21 = c.ewm(span=21, adjust=False).mean()
    brk = h.shift(1).rolling(donchian_n, min_periods=donchian_n).max()
    atr = _atr(h, l, c, atr_n)

    trades: list[Trade] = []
    in_pos = False
    entry_px = 0.0
    entry_i = -1
    trail = np.nan

    for i in range(len(w)):
        if np.isnan(brk.iloc[i]) or np.isnan(atr.iloc[i]) or np.isnan(ema9.iloc[i]) or np.isnan(ema21.iloc[i]):
            continue

        # Update trailing stop while in position.
        if in_pos:
            current_stop = float(c.iloc[i]) - atr_mult * float(atr.iloc[i])
            trail = max(trail, current_stop) if np.isfinite(trail) else current_stop
            if float(c.iloc[i]) < trail:
                exit_px = float(c.iloc[i])
                trades.append(
                    Trade(
                        symbol=symbol,
                        entry_time=w.index[entry_i],
                        exit_time=w.index[i],
                        entry=entry_px,
                        exit=exit_px,
                        ret_pct=(exit_px / entry_px - 1.0) * 100.0,
                        bars_held=i - entry_i,
                    )
                )
                in_pos = False
                trail = np.nan
                continue

        # Entry at weekly close when breakout + trend.
        if (not in_pos) and float(c.iloc[i]) > float(brk.iloc[i]) and float(ema9.iloc[i]) > float(ema21.iloc[i]):
            in_pos = True
            entry_px = float(c.iloc[i])
            entry_i = i
            trail = entry_px - atr_mult * float(atr.iloc[i])

    # Open position left unclosed is ignored for PF.
    return trades


def summarize(trades: Iterable[Trade]) -> dict[str, float]:
    t = list(trades)
    if not t:
        return {}
    rets = np.array([x.ret_pct for x in t], dtype=float)
    wins = rets[rets > 0]
    losses = rets[rets < 0]
    gp = wins.sum()
    gl = -losses.sum()
    pf = gp / gl if gl > 0 else np.inf
    return {
        "trades": int(len(t)),
        "win_rate_pct": float((rets > 0).mean() * 100.0),
        "avg_ret_pct": float(rets.mean()),
        "median_ret_pct": float(np.median(rets)),
        "profit_factor": float(pf),
        "gross_profit_pct_sum": float(gp),
        "gross_loss_pct_sum": float(gl),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Weekly Donchian(10)+EMA9>21 with ATR exit backtest")
    ap.add_argument(
        "--universe-csv",
        default=os.path.join(ROOT, "stock_scanner_sovereign", "data", "nifty_total_market.csv"),
    )
    ap.add_argument("--donchian", type=int, default=10)
    ap.add_argument("--atr-period", type=int, default=9)
    ap.add_argument("--atr-mult", type=float, default=2.0)
    ap.add_argument(
        "--out-csv",
        default=os.path.join(
            ROOT, "stock_scanner_sovereign", "data", "backtest_weekly_breakout10_atr_exit_trades.csv"
        ),
    )
    args = ap.parse_args()

    symbols = _load_symbols(args.universe_csv)
    all_trades: list[Trade] = []
    checked = 0
    for s in symbols:
        w = _weekly_ohlc(s)
        if w is None:
            continue
        checked += 1
        all_trades.extend(backtest_symbol(s, w, args.donchian, args.atr_period, args.atr_mult))

    stats = summarize(all_trades)
    print("=== Weekly backtest: Donchian breakout + EMA9>21, ATR exit only ===")
    print(f"Universe csv: {args.universe_csv}")
    print(f"Symbols with data: {checked}")
    if not stats:
        print("No trades found.")
        return
    for k, v in stats.items():
        print(f"{k}: {v}")

    out = pd.DataFrame([t.__dict__ for t in all_trades])
    out.to_csv(args.out_csv, index=False)
    print(f"Trades csv: {args.out_csv} rows={len(out)}")


if __name__ == "__main__":
    main()

