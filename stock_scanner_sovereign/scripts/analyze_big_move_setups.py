#!/usr/bin/env python3
"""
Analyze "big move day" setups on local daily Parquet history.

Core question this answers:
  "When a stock moves >= X% today, what was it doing yesterday?"

Default behavior:
  - Scan a universe (default: Nifty 500)
  - Find symbols whose *latest* daily close-to-close change >= threshold
  - Print t-1 setup features for each hit

Optional:
  - --full-history: compute how often each feature is present on t-1 before big-move days,
    plus forward returns from the event day.

Examples:
  cd stock_scanner_sovereign
  python3 scripts/analyze_big_move_setups.py --universe "Nifty 500" --threshold 10
  python3 scripts/analyze_big_move_setups.py --universe "Nifty 500" --threshold 10 --full-history
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
    o_col = cols.get("open")
    h_col = cols.get("high")
    l_col = cols.get("low")
    c_col = cols.get("close")
    v_col = cols.get("volume")
    if not all([ts_col, o_col, h_col, l_col, c_col]):
        return None
    keep = [ts_col, o_col, h_col, l_col, c_col] + ([v_col] if v_col else [])
    out = df[keep].copy()
    out.columns = ["timestamp", "open", "high", "low", "close"] + (["volume"] if v_col else [])
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"])
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    if out.empty:
        return None
    return out.set_index("timestamp")


def _atr14(df: pd.DataFrame) -> pd.Series:
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    c = df["close"].astype(float)
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(14, min_periods=14).mean()


def _rolling_std(x: np.ndarray) -> float:
    if x.size == 0:
        return float("nan")
    return float(np.std(x, ddof=0))


@dataclass
class YesterdaySetup:
    symbol: str
    event_day: pd.Timestamp
    event_chg_pct: float
    y_chg_pct: float
    event_gap_pct: float
    y_vol_x20: float | None
    y_rng_x_atr14: float | None
    y_near_20d_high: bool
    y_compress_10d: bool
    y_compress_20d: bool


def _pct(a: bool) -> str:
    return "YES" if a else "NO"


def _yesterday_setup(df: pd.DataFrame, symbol: str, i_event: int) -> YesterdaySetup | None:
    if i_event < 25 or i_event >= len(df):
        return None
    o = df["open"].astype(float).to_numpy()
    h = df["high"].astype(float).to_numpy()
    l = df["low"].astype(float).to_numpy()
    c = df["close"].astype(float).to_numpy()
    v = df["volume"].astype(float).to_numpy() if "volume" in df.columns else None
    idx = df.index

    prev_c = c[i_event - 1]
    if not np.isfinite(prev_c) or prev_c <= 0:
        return None
    event_chg = (c[i_event] - prev_c) / prev_c * 100.0

    prev2_c = c[i_event - 2]
    y_chg = ((prev_c - prev2_c) / prev2_c * 100.0) if np.isfinite(prev2_c) and prev2_c > 0 else 0.0

    event_gap = ((o[i_event] - prev_c) / prev_c * 100.0) if np.isfinite(o[i_event]) else 0.0

    y_vol_x20 = None
    if v is not None and i_event >= 21:
        base = v[i_event - 21 : i_event - 1]
        denom = float(np.mean(base)) if base.size else 0.0
        if np.isfinite(denom) and denom > 0 and np.isfinite(v[i_event - 1]):
            y_vol_x20 = float(v[i_event - 1] / denom)

    y_rng_x_atr14 = None
    if i_event >= 16:
        atr = _atr14(df).to_numpy()
        if np.isfinite(atr[i_event - 1]) and atr[i_event - 1] > 0:
            y_rng = float(h[i_event - 1] - l[i_event - 1])
            y_rng_x_atr14 = float(y_rng / float(atr[i_event - 1]))

    # yesterday near 20D high (using highs up to yesterday)
    y_near_20d_high = False
    if i_event >= 21:
        hh20 = float(np.nanmax(h[i_event - 21 : i_event - 1]))
        if np.isfinite(hh20) and hh20 > 0:
            y_near_20d_high = float(c[i_event - 1]) >= 0.98 * hh20

    # compression: 10d / 20d std of returns is low vs prior window
    rets = np.zeros_like(c)
    rets[1:] = np.where(c[:-1] > 0, (c[1:] / c[:-1] - 1.0), 0.0)
    y_compress_10d = False
    y_compress_20d = False
    if i_event >= 41:
        r10 = rets[i_event - 11 : i_event - 1]
        r10_prev = rets[i_event - 21 : i_event - 11]
        s10 = _rolling_std(r10)
        s10p = _rolling_std(r10_prev)
        if np.isfinite(s10) and np.isfinite(s10p) and s10p > 0:
            y_compress_10d = s10 <= 0.6 * s10p
        r20 = rets[i_event - 21 : i_event - 1]
        r20_prev = rets[i_event - 41 : i_event - 21]
        s20 = _rolling_std(r20)
        s20p = _rolling_std(r20_prev)
        if np.isfinite(s20) and np.isfinite(s20p) and s20p > 0:
            y_compress_20d = s20 <= 0.6 * s20p

    return YesterdaySetup(
        symbol=symbol,
        event_day=idx[i_event],
        event_chg_pct=float(event_chg),
        y_chg_pct=float(y_chg),
        event_gap_pct=float(event_gap),
        y_vol_x20=y_vol_x20,
        y_rng_x_atr14=y_rng_x_atr14,
        y_near_20d_high=bool(y_near_20d_high),
        y_compress_10d=bool(y_compress_10d),
        y_compress_20d=bool(y_compress_20d),
    )


def _fwd_ret(close: np.ndarray, i: int, n: int) -> float | None:
    if i < 0 or i >= close.size or i + n >= close.size:
        return None
    a = float(close[i])
    b = float(close[i + n])
    if not np.isfinite(a) or not np.isfinite(b) or a <= 0:
        return None
    return b / a - 1.0


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze setups preceding big % up days.")
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--symbol", default=None, help="Analyze a single symbol (e.g. NSE:PCBL-EQ). Overrides universe scan.")
    ap.add_argument("--threshold", type=float, default=10.0, help="Event day CHG%% >= threshold (close-to-close).")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--full-history", action="store_true", help="Scan all event days (not just latest).")
    ap.add_argument("--max-symbols", type=int, default=0)
    args = ap.parse_args()

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    if args.symbol:
        syms = [str(args.symbol).strip()]
    else:
        syms = sorted(expected_symbols_for_universe(args.universe))
    if args.max_symbols and args.max_symbols > 0:
        syms = syms[: int(args.max_symbols)]

    thr = float(args.threshold)
    hits_latest: list[YesterdaySetup] = []
    hist_rows: list[dict] = []

    for sym in syms:
        df = _load_daily_ohlcv(sym, data_dir)
        if df is None or len(df) < 120:
            continue
        df = df.dropna(subset=["open", "high", "low", "close"])
        if len(df) < 60:
            continue
        c = df["close"].astype(float).to_numpy()
        if c.size < 3:
            continue

        if not bool(args.full_history):
            i = int(len(df) - 1)
            prev = float(c[i - 1])
            if not np.isfinite(prev) or prev <= 0:
                continue
            chg = (float(c[i]) - prev) / prev * 100.0
            if chg >= thr:
                s = _yesterday_setup(df, sym, i)
                if s:
                    hits_latest.append(s)
            continue

        # Full history scan (event days)
        for i in range(25, len(df)):
            prev = float(c[i - 1])
            if not np.isfinite(prev) or prev <= 0:
                continue
            chg = (float(c[i]) - prev) / prev * 100.0
            if chg < thr:
                continue
            s = _yesterday_setup(df, sym, i)
            if not s:
                continue
            row = s.__dict__.copy()
            row["fwd_5d"] = _fwd_ret(c, i, 5)
            row["fwd_10d"] = _fwd_ret(c, i, 10)
            row["fwd_20d"] = _fwd_ret(c, i, 20)
            hist_rows.append(row)

    if not args.full_history:
        print(f"Universe={args.universe!r} | threshold={thr:.2f}% | latest-day hits={len(hits_latest)}")
        for s in sorted(hits_latest, key=lambda x: x.event_chg_pct, reverse=True):
            print(
                f"{s.symbol} {s.event_day.date()} CHG%={s.event_chg_pct:.2f} "
                f"| y_chg={s.y_chg_pct:+.2f} gap={s.event_gap_pct:+.2f} "
                f"| y_vol_x20={(f'{s.y_vol_x20:.2f}' if s.y_vol_x20 is not None else 'NA')} "
                f"y_rng_x_atr14={(f'{s.y_rng_x_atr14:.2f}' if s.y_rng_x_atr14 is not None else 'NA')} "
                f"| near20H={_pct(s.y_near_20d_high)} c10={_pct(s.y_compress_10d)} c20={_pct(s.y_compress_20d)}"
            )
        return

    dfh = pd.DataFrame(hist_rows)
    if dfh.empty:
        print(f"Universe={args.universe!r} | threshold={thr:.2f}% | events=0")
        return

    print(f"Universe={args.universe!r} | threshold={thr:.2f}% | events={len(dfh)}")
    for col in ["y_near_20d_high", "y_compress_10d", "y_compress_20d"]:
        pct = float(dfh[col].mean() * 100.0)
        print(f"{col}: {pct:.1f}% of events")
    if "y_vol_x20" in dfh.columns:
        vv = dfh["y_vol_x20"].replace([np.inf, -np.inf], np.nan).dropna()
        if not vv.empty:
            print(f"y_vol_x20: median={float(vv.median()):.2f} p>=2.0={float((vv>=2.0).mean()*100):.1f}%")
    if "y_rng_x_atr14" in dfh.columns:
        rr = dfh["y_rng_x_atr14"].replace([np.inf, -np.inf], np.nan).dropna()
        if not rr.empty:
            print(f"y_rng_x_atr14: median={float(rr.median()):.2f} p>=1.5={float((rr>=1.5).mean()*100):.1f}%")

    for n, col in [(5, "fwd_5d"), (10, "fwd_10d"), (20, "fwd_20d")]:
        v = dfh[col].replace([np.inf, -np.inf], np.nan).dropna()
        if v.empty:
            continue
        print(f"fwd_{n}d: n={len(v)} median={float(v.median())*100:.2f}% p>=5%={float((v>=0.05).mean()*100):.1f}%")


if __name__ == "__main__":
    main()

