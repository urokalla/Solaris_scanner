#!/usr/bin/env python3
"""
Backtest a **Chartink-style** cash screener (range expansion + multi-TF bullish + volume + SMA stack).

**Scan modes**

- ``--scan eod`` — rules on **completed daily** bars (after market close).
- ``--scan ist_0930`` — rules at **09:30 IST** using **9:15–9:30** session slice from **minute** parquet
  (requires ``--minute-data-dir``). Compares **morning range** to prior **7 full daily** ranges.
  SMA stack uses **prior session** closes. Forward return: **daily close** ``N`` sessions later vs **09:30 LTP**
  (last close in the minute window).

Minute parquet: same columns as daily (``timestamp``/``ts``, ``open``, ``high``, ``low``, ``close``, ``volume``).
One file per symbol, e.g. ``NSE_RELIANCE-EQ.parquet`` under ``--minute-data-dir``.

Examples:
  python scripts/backtest_chartink_range_expansion.py --universe \"Nifty 500\" --forward-days 5
  python scripts/backtest_chartink_range_expansion.py --scan ist_0930 --minute-data-dir /path/to/min1 \\
    --universe \"Nifty 500\" --forward-days 5
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import time as dt_time

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402

_T915 = dt_time(9, 15, 0)
_T930 = dt_time(9, 30, 0)


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
    if not all([ts_col, o_col, h_col, l_col, c_col, v_col]):
        return None
    out = df[[ts_col, o_col, h_col, l_col, c_col, v_col]].copy()
    out.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    for c in ["open", "high", "low", "close", "volume"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    if out.empty or len(out) < 80:
        return None
    return out.set_index("timestamp")


def _minute_parquet_candidates(symbol: str, minute_dir: str) -> list[str]:
    safe = symbol.replace(":", "_").replace("/", "_")
    naked = symbol.split(":")[-1] if ":" in symbol else symbol
    names = [
        f"{safe}.parquet",
        f"{naked}.parquet",
        f"{symbol}.parquet",
    ]
    return [os.path.join(minute_dir, n) for n in names]


def _load_minute_ohlcv(symbol: str, minute_dir: str) -> pd.DataFrame | None:
    for p in _minute_parquet_candidates(symbol, minute_dir):
        if not os.path.isfile(p):
            continue
        try:
            df = pd.read_parquet(p)
        except Exception:
            continue
        cols = {c.lower(): c for c in df.columns}
        ts_col = cols.get("timestamp") or cols.get("ts")
        o_col = cols.get("open")
        h_col = cols.get("high")
        l_col = cols.get("low")
        c_col = cols.get("close")
        v_col = cols.get("volume")
        if not all([ts_col, o_col, h_col, l_col, c_col, v_col]):
            continue
        out = df[[ts_col, o_col, h_col, l_col, c_col, v_col]].copy()
        out.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
        for c in ["open", "high", "low", "close", "volume"]:
            out[c] = pd.to_numeric(out[c], errors="coerce")
        out = out.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
        out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
        if out.empty:
            continue
        return out.set_index("timestamp")
    return None


def _morning_slice_agg(minute_df: pd.DataFrame) -> pd.DataFrame:
    """One row per **IST calendar date**: OHLCV for bars with local time in [09:15, 09:30]."""
    m = minute_df.sort_index().astype(float)
    if m.index.tz is None:
        m.index = m.index.tz_localize("UTC")
    ist = m.tz_convert("Asia/Kolkata")
    tloc = ist.index.time
    mask = (tloc >= _T915) & (tloc <= _T930)
    slot = ist.loc[mask].copy()
    if slot.empty:
        return pd.DataFrame()
    slot["_day"] = slot.index.normalize()
    g = slot.groupby("_day", sort=False)
    agg = g.agg(
        mo=("open", "first"),
        mh=("high", "max"),
        ml=("low", "min"),
        mc=("close", "last"),
        mv=("volume", "sum"),
    )
    agg.index.name = "ist_date"
    return agg


def _signals_eod(df: pd.DataFrame, *, min_vol_yesterday: float) -> pd.Series:
    d = df.sort_index().astype(float)
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    ist = d.tz_convert("Asia/Kolkata")

    o, h, l, c, v = ist["open"], ist["high"], ist["low"], ist["close"], ist["volume"]
    rng = h - l
    past_max = rng.shift(1).rolling(7, min_periods=7).max()
    range_ok = (rng > past_max) & rng.shift(1).notna()

    daily_ok = (c > o) & (c > c.shift(1))

    iso = ist.index.isocalendar()
    grp_w = iso["year"].astype(str) + "_" + iso["week"].astype(str)
    week_open = ist.groupby(grp_w, sort=False)["open"].transform("first")
    week_ok = c > week_open

    grp_m = pd.Series(
        [f"{t.year}-{t.month:02d}" for t in ist.index],
        index=ist.index,
        dtype="string",
    )
    month_open = ist.groupby(grp_m, sort=False)["open"].transform("first")
    month_ok = c > month_open

    vol_ok = (v.shift(1) > min_vol_yesterday) & (v > 1.25 * v.shift(1))

    sma20 = c.rolling(20, min_periods=20).mean()
    sma40 = c.rolling(40, min_periods=40).mean()
    sma60 = c.rolling(60, min_periods=60).mean()
    ma_ok = (sma20 > sma40) & (sma40 > sma60)

    return range_ok & daily_ok & week_ok & month_ok & vol_ok & ma_ok


def _events_morning_930(
    daily: pd.DataFrame,
    morning: pd.DataFrame,
    *,
    min_vol_yesterday: float,
    forward_days: int,
) -> list[tuple[pd.Timestamp, float, float]]:
    """
    Returns list of (signal_day_utc_index, morning_ltp_mc, forward_return).
    ``signal_day_utc_index`` = daily bar timestamp (UTC) for that session.
    """
    d = daily.sort_index().astype(float)
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    ist_index = d.index.tz_convert("Asia/Kolkata")
    o, h, l, c, v = d["open"], d["high"], d["low"], d["close"], d["volume"]

    rng = h - l
    past_max = rng.shift(1).rolling(7, min_periods=7).max()

    iso = ist_index.isocalendar()
    grp_w = iso["year"].astype(str) + "_" + iso["week"].astype(str)
    week_open = d.groupby(grp_w, sort=False)["open"].transform("first")
    grp_m = pd.Series(
        [f"{t.year}-{t.month:02d}" for t in ist_index],
        index=d.index,
        dtype="string",
    )
    month_open = d.groupby(grp_m, sort=False)["open"].transform("first")

    sma20 = c.rolling(20, min_periods=20).mean().shift(1)
    sma40 = c.rolling(40, min_periods=40).mean().shift(1)
    sma60 = c.rolling(60, min_periods=60).mean().shift(1)
    ma_ok = (sma20 > sma40) & (sma40 > sma60)

    out: list[tuple[pd.Timestamp, float, float]] = []
    n = len(d)
    fd = max(1, int(forward_days))
    for i in range(60, n - fd):
        day_norm = ist_index[i].normalize()
        if day_norm not in morning.index:
            continue
        mo = float(morning.loc[day_norm, "mo"])
        mh = float(morning.loc[day_norm, "mh"])
        ml = float(morning.loc[day_norm, "ml"])
        mc = float(morning.loc[day_norm, "mc"])
        mv = float(morning.loc[day_norm, "mv"])
        if not all(np.isfinite([mo, mh, ml, mc, mv])) or mo <= 0:
            continue

        mr = mh - ml
        pm = past_max.iloc[i]
        if not np.isfinite(pm) or mr <= pm:
            continue
        if not (mc > mo and mc > c.iloc[i - 1]):
            continue
        if not (mc > week_open.iloc[i] and mc > month_open.iloc[i]):
            continue
        vy = v.iloc[i - 1]
        if vy <= min_vol_yesterday or mv <= 1.25 * vy:
            continue
        if not bool(ma_ok.iloc[i]):
            continue

        entry = mc
        if entry <= 0:
            continue
        exit_px = float(c.iloc[i + fd])
        if not np.isfinite(exit_px):
            continue
        ret = exit_px / entry - 1.0
        out.append((d.index[i], ret, entry))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--scan", choices=("eod", "ist_0930"), default="eod")
    ap.add_argument("--minute-data-dir", default=None, help="Required for --scan ist_0930")
    ap.add_argument("--forward-days", type=int, default=5)
    ap.add_argument("--min-vol-yesterday", type=float, default=10_000.0, help="Min prior-day volume (shares)")
    ap.add_argument("--max-symbols", type=int, default=0)
    args = ap.parse_args()

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    fd = max(1, int(args.forward_days))

    if args.scan == "ist_0930":
        if not args.minute_data_dir or not os.path.isdir(args.minute_data_dir):
            print("--scan ist_0930 requires an existing --minute-data-dir with per-symbol minute parquet.")
            sys.exit(2)

    syms = sorted(expected_symbols_for_universe(args.universe))
    if args.max_symbols > 0:
        syms = syms[: args.max_symbols]

    rets: list[float] = []
    n_ok = 0
    n_minute = 0

    for k, sym in enumerate(syms):
        if k % 75 == 0:
            print(f"Scanning {k}/{len(syms)}…", flush=True)
        df = _load_daily_ohlcv(sym, data_dir)
        if df is None:
            continue
        n_ok += 1

        if args.scan == "eod":
            try:
                sig = _signals_eod(df, min_vol_yesterday=args.min_vol_yesterday)
            except Exception:
                continue
            sig_utc = sig.tz_convert("UTC").reindex(df.index).fillna(False)
            c = df["close"].astype(float)
            fwd = c.shift(-fd) / c - 1.0
            for ts, ok in sig_utc.items():
                if not ok or not np.isfinite(fwd.get(ts, np.nan)):
                    continue
                r = float(fwd.loc[ts])
                if np.isfinite(r):
                    rets.append(r)
        else:
            mdf = _load_minute_ohlcv(sym, os.path.abspath(args.minute_data_dir))
            if mdf is None:
                continue
            n_minute += 1
            morning = _morning_slice_agg(mdf)
            if morning.empty:
                continue
            try:
                ev = _events_morning_930(
                    df,
                    morning,
                    min_vol_yesterday=args.min_vol_yesterday,
                    forward_days=fd,
                )
            except Exception:
                continue
            for _ts, r, _e in ev:
                if np.isfinite(r):
                    rets.append(r)

    arr = np.array(rets, dtype=float)
    print(f"\nUniverse: {args.universe} | symbols with daily OHLCV: {n_ok}")
    if args.scan == "ist_0930":
        print(f"Symbols with minute file used: {n_minute}")
    print(f"Scan: {args.scan}" + (" (09:15–09:30 IST bar vs 7× prior full-day range)" if args.scan == "ist_0930" else " (full daily bar)"))
    print(
        "Rules: range; C>O; C>yest close; week/month vs daily week/month opens; "
        f"yest vol>{args.min_vol_yesterday:g}; vol rules; SMA20>SMA40>SMA60"
        + (" (SMA as of prior close)" if args.scan == "ist_0930" else "")
    )
    if args.scan == "ist_0930":
        print(f"Forward: {fd} sessions — **exit** = daily close, **entry** = 09:30 window last close")
    else:
        print(f"Forward: {fd} trading days (daily close / signal close)")
    print(f"Events: {len(arr)}")
    if len(arr) == 0:
        if args.scan == "ist_0930" and n_minute == 0:
            print("No minute parquet matched any symbol (check filenames under --minute-data-dir).")
        return

    print(f"Success rate (ret > 0): {(arr > 0).mean() * 100:.2f}%")
    print(f"Mean return:   {arr.mean() * 100:.3f}%")
    print(f"Median return: {np.median(arr) * 100:.3f}%")
    print(f"Std return:    {arr.std() * 100:.3f}%")
    print(f"Worst / Best:  {arr.min() * 100:.2f}% / {arr.max() * 100:.2f}%")


if __name__ == "__main__":
    main()
