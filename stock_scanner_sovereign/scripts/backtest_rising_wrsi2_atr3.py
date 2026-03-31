#!/usr/bin/env python3
"""
Event study: RISING profile + weekly RSI(2) < 5 + "price above ATR×3" (configurable).

RISING (matches ``utils/scanner_analysis.compute_trading_profile`` priority):
  ELITE r>=95, LEADER r>=82, FADING m<0 & d<0, LAGGARD r<=22 | m<-1.5,
  then RISING if m>0 & d>0 else BASELINE.

mRS / RS rating:
  Same construction as ``RSMathEngine.calculate_rs`` (52d / 52w ratio vs NIFTY500,
  d_mrs = (ratio/sma-1)*10, rs_rating = cross-sectional percentile of weekly mRS).

Weekly RSI(2):
  Wilder period 2 on Friday-week closes (Asia/Kolkata), aligned to each calendar day.

ATR rules (``--atr-mode``):
  chandelier  (default): close > rolling_max(high, n) - mult * ATR(14)  [still "above" trail]
  extension:             close > SMA(50) + mult * ATR(14)
  none:                  skip ATR filter (only RISING + WRSI2<5)

Signals are evaluated on the **last trading day of each ISO week** (weekday == Friday in IST).

Forward horizons: trading days ahead from **next** session close after signal (enter signal close
or next close via ``--entry``).

Examples:
  python scripts/backtest_rising_wrsi2_atr3.py --universe "Nifty 500"
  python scripts/backtest_rising_wrsi2_atr3.py --atr-mode extension --wrsi2-max 5 --horizons 5,10,20,40
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
from utils.monthly_rsi2_trade_rules import rsi_wilder, week_end_close  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


def _load_ohlcv(symbol: str, data_dir: str) -> pd.DataFrame | None:
    path = resolve_parquet_path(symbol, data_dir)
    if not path:
        return None
    try:
        df = pd.read_parquet(path)
    except Exception:
        return None
    cm = {c.lower(): c for c in df.columns}
    need = ["timestamp", "open", "high", "low", "close"]
    cols = []
    for k in need:
        c = cm.get(k) or cm.get("ts" if k == "timestamp" else None)
        if not c:
            return None
        cols.append(c)
    out = df[cols].copy()
    out.columns = ["timestamp", "open", "high", "low", "close"]
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    for c in ["open", "high", "low", "close"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["timestamp", "close"])
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    if out.empty:
        return None
    return out.set_index("timestamp")


def _atr_wilder(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    h, l, c = high.astype(float), low.astype(float), close.astype(float)
    tr = pd.concat(
        [
            (h - l).abs(),
            (h - c.shift(1)).abs(),
            (l - c.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def _daily_mrs_components(
    stock_close: pd.Series, bench_close: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """Weekly and daily mRS series (same scaling as scanner). Index = daily."""
    ratio_d = stock_close / bench_close.replace(0, np.nan)
    sma_d = ratio_d.shift(1).rolling(52, min_periods=52).mean()
    d_mrs = ((ratio_d / sma_d) - 1.0) * 10.0

    sc = stock_close.dropna()
    bc = bench_close.reindex(sc.index).dropna()
    common = sc.index.intersection(bc.index)
    if len(common) < 10:
        return pd.Series(index=stock_close.index, dtype=float), d_mrs
    w_s = week_end_close(sc.reindex(common).dropna())
    w_b = week_end_close(bc.reindex(common).dropna())
    common_w = w_s.index.intersection(w_b.index)
    w_s = w_s.reindex(common_w).ffill()
    w_b = w_b.reindex(common_w).ffill()
    ratio_w = w_s / w_b.replace(0, np.nan)
    sma_w = ratio_w.shift(1).rolling(52, min_periods=52).mean()
    w_mrs_w = ((ratio_w / sma_w) - 1.0) * 10.0
    # Vector map weekly → daily (last completed week, forward-filled)
    w_mrs_d = w_mrs_w.reindex(stock_close.index).ffill()
    w_mrs_d = w_mrs_d.reindex(stock_close.index)
    return w_mrs_d, d_mrs


def _weekly_rsi2_series(daily_close: pd.Series) -> pd.Series:
    sc = daily_close.dropna()
    if len(sc) < 30:
        return pd.Series(index=daily_close.index, dtype=float)
    w = week_end_close(sc)
    if len(w) < 4:
        return pd.Series(index=daily_close.index, dtype=float)
    r = rsi_wilder(w, period=2)
    out = r.reindex(daily_close.index).ffill()
    return out.reindex(daily_close.index)


def _rising_mask_numpy(r: np.ndarray, m: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Boolean RISING profile; NaNs in m/d treated as not rising."""
    r = np.clip(np.nan_to_num(r, nan=0.0).astype(int), 0, 100)
    m = np.nan_to_num(m, nan=0.0)
    d = np.nan_to_num(d, nan=0.0)
    is_elite = r >= 95
    is_leader = (r >= 82) & ~is_elite
    is_fading = (m < 0) & (d < 0) & ~is_elite & ~is_leader
    is_lagg = ((r <= 22) | (m < -1.5)) & ~is_elite & ~is_leader & ~is_fading
    is_rising = (m > 0) & (d > 0) & ~is_elite & ~is_leader & ~is_fading & ~is_lagg
    return is_rising


def trading_profile(r: float, m: float, d: float) -> str:
    r = int(np.clip(int(r), 0, 100))
    m, d = float(m), float(d)
    if not np.isfinite(m):
        m = 0.0
    if not np.isfinite(d):
        d = 0.0
    if r >= 95:
        return "ELITE"
    if r >= 82:
        return "LEADER"
    if m < 0 and d < 0:
        return "FADING"
    if r <= 22 or m < -1.5:
        return "LAGGARD"
    if m > 0 and d > 0:
        return "RISING"
    return "BASELINE"


def _chandelier_ok(
    high: pd.Series, low: pd.Series, close: pd.Series, lookback: int, atr_len: int, mult: float
) -> pd.Series:
    atr = _atr_wilder(high, low, close, atr_len)
    hh = high.rolling(lookback, min_periods=lookback).max()
    trail = hh - mult * atr
    return close > trail


def _extension_ok_hlc(
    high: pd.Series, low: pd.Series, close: pd.Series, atr_len: int, mult: float, sma_len: int
) -> pd.Series:
    atr = _atr_wilder(high, low, close, atr_len)
    sma = close.rolling(sma_len, min_periods=sma_len).mean()
    return close > (sma + mult * atr)


@dataclass
class Event:
    symbol: str
    ts: pd.Timestamp
    close: float
    wrsi2: float
    m_week: float
    d_day: float
    rs_rating: int


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest RISING + WRSI2<k + ATR rule")
    ap.add_argument("--universe", default="Nifty 500", help="Universe display name")
    ap.add_argument("--data-dir", default=None, help="Parquet root (default: settings.PIPELINE_DATA_DIR)")
    ap.add_argument("--bench", default="NSE:NIFTY500-INDEX", help="Benchmark symbol")
    ap.add_argument("--wrsi2-max", type=float, default=5.0, help="Weekly RSI(2) strictly below this")
    ap.add_argument("--atr-mode", choices=("chandelier", "extension", "none"), default="chandelier")
    ap.add_argument("--atr-mult", type=float, default=3.0)
    ap.add_argument("--atr-len", type=int, default=14)
    ap.add_argument("--chandelier-lookback", type=int, default=22)
    ap.add_argument("--ext-sma", type=int, default=50)
    ap.add_argument("--horizons", default="5,10,20,40", help="Comma-separated forward trading days")
    ap.add_argument("--entry", choices=("signal_close", "next_close"), default="next_close")
    ap.add_argument("--min-history-weeks", type=int, default=60)
    ap.add_argument("--max-symbols", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    horizons = [int(x.strip()) for x in args.horizons.split(",") if x.strip()]

    bench_df = _load_ohlcv(args.bench, data_dir)
    if bench_df is None or bench_df.empty:
        print(f"Missing benchmark parquet: {args.bench} in {data_dir}")
        sys.exit(1)
    bench_close = bench_df["close"].sort_index()

    syms = sorted(expected_symbols_for_universe(args.universe))
    if args.max_symbols > 0:
        syms = syms[: args.max_symbols]
    if not syms:
        print("No symbols for universe")
        sys.exit(1)

    # Load all closes aligned to benchmark index
    master_idx = bench_close.index.sort_values()
    close_mat: dict[str, pd.Series] = {}
    high_mat: dict[str, pd.Series] = {}
    low_mat: dict[str, pd.Series] = {}
    for sym in syms:
        df = _load_ohlcv(sym, data_dir)
        if df is None or len(df) < args.min_history_weeks * 5:
            continue
        c = df["close"].reindex(master_idx)
        if c.notna().sum() < args.min_history_weeks * 5:
            continue
        close_mat[sym] = c
        high_mat[sym] = df["high"].reindex(master_idx)
        low_mat[sym] = df["low"].reindex(master_idx)

    usable = sorted(close_mat.keys())
    if len(usable) < 10:
        print(f"Too few symbols with history ({len(usable)})")
        sys.exit(1)

    b = bench_close.reindex(master_idx).ffill()

    # Panel of weekly mRS for cross-sectional rank (per date)
    w_mrs_panel = pd.DataFrame(index=master_idx, columns=usable, dtype=float)
    d_mrs_panel = pd.DataFrame(index=master_idx, columns=usable, dtype=float)
    wrsi2_panel = pd.DataFrame(index=master_idx, columns=usable, dtype=float)
    atr_ok_panel = pd.DataFrame(index=master_idx, columns=usable, dtype=bool)

    n_sym = len(usable)
    for k, sym in enumerate(usable):
        if k % 50 == 0 or k == n_sym - 1:
            print(f"  Building panels {k + 1}/{n_sym} {sym}…", flush=True)
        sc = close_mat[sym]
        valid = sc.notna() & b.notna()
        sc2 = sc.where(valid)
        b2 = b.where(valid)
        w_mrs, d_mrs = _daily_mrs_components(sc2, b2)
        w_mrs_panel[sym] = w_mrs
        d_mrs_panel[sym] = d_mrs
        wrsi2_panel[sym] = _weekly_rsi2_series(sc2)

        hi, lo = high_mat[sym], low_mat[sym]
        if args.atr_mode == "chandelier":
            atr_ok_panel[sym] = _chandelier_ok(hi, lo, sc, args.chandelier_lookback, args.atr_len, args.atr_mult)
        elif args.atr_mode == "extension":
            atr_ok_panel[sym] = _extension_ok_hlc(hi, lo, sc, args.atr_len, args.atr_mult, args.ext_sma)
        else:
            atr_ok_panel[sym] = True

    print("  Ranking RS% (cross-section)…", flush=True)
    rs_panel = (w_mrs_panel.rank(axis=1, pct=True, method="average") * 100.0).round().clip(0, 100).astype(int)

    # IST Friday mask (last bar of Indian week for weekly WRSI2 alignment)
    ix = pd.DatetimeIndex(master_idx)
    if ix.tz is None:
        ix = ix.tz_localize("UTC")
    is_fri = pd.Series(ix.tz_convert("Asia/Kolkata").weekday == 4, index=master_idx)

    events: list[Event] = []
    # Precompute rs_rating row-wise (expensive but clear)
    for i, ts in enumerate(master_idx):
        if not bool(is_fri.loc[ts]):
            continue
        row = w_mrs_panel.loc[ts]
        rowv = row.dropna()
        if len(rowv) < 20:
            continue
        ranks = rowv.rank(pct=True, method="average")
        rs_series = (ranks * 100.0).astype(int).clip(0, 100)
        for sym in usable:
            if sym not in rowv.index or pd.isna(w_mrs_panel.at[ts, sym]):
                continue
            m = float(w_mrs_panel.at[ts, sym])
            d = float(d_mrs_panel.at[ts, sym]) if pd.notna(d_mrs_panel.at[ts, sym]) else np.nan
            wr = float(wrsi2_panel.at[ts, sym]) if pd.notna(wrsi2_panel.at[ts, sym]) else np.nan
            if not np.isfinite(d) or not np.isfinite(wr):
                continue
            r = int(rs_series.get(sym, 0))
            prof = trading_profile(r, m, d)
            if prof != "RISING":
                continue
            if wr >= args.wrsi2_max:
                continue
            if not bool(atr_ok_panel.at[ts, sym]):
                continue
            c = close_mat[sym].get(ts)
            if c is None or not np.isfinite(float(c)):
                continue
            events.append(Event(sym, ts, float(c), wr, m, d, r))

    print(f"Universe: {args.universe} | symbols with data: {len(usable)}")
    print(f"Bench: {args.bench} | ATR mode: {args.atr_mode} (mult={args.atr_mult})")
    print(f"Rules: profile=RISING, WRSI2 < {args.wrsi2_max}, Friday IST bar")
    print(f"Events: {len(events)}")
    if not events:
        return

    # Forward returns from entry bar
    idx_list = list(master_idx)
    ix_map = {ts: j for j, ts in enumerate(idx_list)}

    rets: dict[int, list[float]] = {h: [] for h in horizons}
    for ev in events:
        j = ix_map.get(ev.ts)
        if j is None:
            continue
        j0 = j + (1 if args.entry == "next_close" else 0)
        if j0 >= len(idx_list):
            continue
        entry_ts = idx_list[j0]
        entry_px = close_mat[ev.symbol].get(entry_ts)
        if entry_px is None or not np.isfinite(float(entry_px)) or float(entry_px) <= 0:
            continue
        entry_px = float(entry_px)
        for h in horizons:
            j1 = j0 + h
            if j1 >= len(idx_list):
                continue
            exit_ts = idx_list[j1]
            ex = close_mat[ev.symbol].get(exit_ts)
            if ex is None or not np.isfinite(float(ex)):
                continue
            rets[h].append(float(ex) / entry_px - 1.0)

    print("\nForward returns (fraction) from", args.entry, "(non-overlapping event count varies by horizon):")
    for h in horizons:
        xs = rets[h]
        if not xs:
            print(f"  {h:3d}d: n=0")
            continue
        arr = np.array(xs, dtype=float)
        print(
            f"  {h:3d}d: n={len(xs):5d}  mean={arr.mean()*100:6.2f}%  "
            f"median={np.median(arr)*100:6.2f}%  win%={(arr>0).mean()*100:5.1f}%"
        )

    # Sample of last few events
    print("\nLast 8 events:")
    for ev in sorted(events, key=lambda e: e.ts)[-8:]:
        print(
            f"  {ev.ts.date()} {ev.symbol} WRSI2={ev.wrsi2:.2f} mRS={ev.m_week:.2f} "
            f"d_mRS={ev.d_day:.2f} RS%={ev.rs_rating} close={ev.close:.2f}"
        )


if __name__ == "__main__":
    main()
