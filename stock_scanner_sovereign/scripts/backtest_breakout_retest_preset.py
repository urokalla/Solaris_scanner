#!/usr/bin/env python3
"""
Backtest an explicit BREAKOUT+RETEST preset on local parquet history.

This is an offline approximation of sidecar behavior (daily bars), not a tick-accurate replay.
It is designed to answer: "does this preset have edge on my universe history?"

Example:
  python scripts/backtest_breakout_retest_preset.py --universe "Nifty 500"
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.constants import BENCHMARK_MAP  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


@dataclass
class Event:
    symbol: str
    date: pd.Timestamp
    entry: float
    mrs: float
    brk_lvl: float
    pct_vs_brk: float
    status: str
    max_ret_10: float
    dd_10: float
    max_ret_20: float
    max_ret_40: float
    dd_20: float
    dd_40: float


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
    out = df[[ts_col, o_col, h_col, l_col, c_col] + ([v_col] if v_col else [])].copy()
    out.columns = ["timestamp", "open", "high", "low", "close"] + (["volume"] if v_col else [])
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"])
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    if out.empty:
        return None
    out = out.set_index("timestamp")
    return out


def _to_weekly_close(df_daily: pd.DataFrame) -> pd.Series:
    return df_daily["close"].resample("W-FRI").last().dropna()


def _compute_weekly_mrs(
    stock_weekly_close: pd.Series,
    bench_weekly_close: pd.Series,
    mrs_ma_weeks: int = 52,
    mrs_signal_period: int = 30,
) -> pd.DataFrame:
    w = pd.concat([stock_weekly_close.rename("s"), bench_weekly_close.rename("b")], axis=1, sort=False).dropna()
    if w.empty:
        return pd.DataFrame(columns=["mrs", "mrs_prev", "mrs_signal", "mrs_status"])
    ratio = w["s"] / w["b"]
    ma = ratio.rolling(mrs_ma_weeks, min_periods=max(20, mrs_ma_weeks // 2)).mean()
    mrs = ((ratio / ma) - 1.0) * 100.0
    mrs_prev = mrs.shift(1)
    mrs_signal = mrs.rolling(mrs_signal_period, min_periods=5).mean()
    buy_now = ((mrs > 0) & (mrs_prev <= 0)) | ((mrs > 0) & (mrs > mrs_signal) & (mrs_prev <= mrs_signal))
    status = np.where(mrs <= 0, "NOT TRENDING", np.where(buy_now, "BUY NOW", "TRENDING"))
    out = pd.DataFrame(
        {
            "mrs": mrs.astype(float),
            "mrs_prev": mrs_prev.astype(float),
            "mrs_signal": mrs_signal.astype(float),
            "mrs_status": status,
        }
    )
    return out.dropna(subset=["mrs"])


def _forward_metrics(df: pd.DataFrame, i: int, horizon: int) -> tuple[float, float]:
    entry = float(df["close"].iat[i])
    if not np.isfinite(entry) or entry <= 0:
        return float("nan"), float("nan")
    fwd = df.iloc[i + 1 : i + 1 + horizon]
    if fwd.empty:
        return float("nan"), float("nan")
    mx = float(fwd["high"].max())
    mn = float(fwd["low"].min())
    max_ret = (mx / entry) - 1.0 if np.isfinite(mx) and mx > 0 else float("nan")
    dd = (mn / entry) - 1.0 if np.isfinite(mn) and mn > 0 else float("nan")
    return max_ret, dd


def _build_events_for_symbol(
    symbol: str,
    s_daily: pd.DataFrame,
    bench_weekly_close: pd.Series,
    pivot_window: int,
    near_low: float,
    near_high: float,
    recent_breakout_lookback: int,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
) -> list[Event]:
    weekly = _compute_weekly_mrs(_to_weekly_close(s_daily), bench_weekly_close)
    if weekly.empty:
        return []

    # Map weekly MRS/status onto daily bars (latest available weekly value).
    d = s_daily.copy()
    wk = weekly.copy()
    wk.index = wk.index.tz_convert("UTC") if wk.index.tz is not None else wk.index.tz_localize("UTC")
    d = pd.merge_asof(
        d.reset_index().sort_values("timestamp"),
        wk.reset_index().rename(columns={"index": "timestamp"}).sort_values("timestamp"),
        on="timestamp",
        direction="backward",
    ).set_index("timestamp")
    d = d.dropna(subset=["mrs"])
    if d.empty:
        return []

    if start_date is not None:
        d = d[d.index >= start_date]
    if end_date is not None:
        d = d[d.index <= end_date]
    if len(d) < max(80, pivot_window + recent_breakout_lookback + 5):
        return []

    d["brk_lvl"] = d["high"].shift(1).rolling(pivot_window, min_periods=pivot_window).max()
    d["ratio_brk"] = d["close"] / d["brk_lvl"]
    d["is_breakout"] = d["close"] > d["brk_lvl"]
    d["recent_breakout"] = (
        d["is_breakout"].shift(1).rolling(recent_breakout_lookback, min_periods=1).max().fillna(0).astype(bool)
    )
    d["in_retest_zone"] = (d["ratio_brk"] >= near_low) & (d["ratio_brk"] <= near_high)
    d["trend_ok"] = (d["mrs"] > 0) & d["mrs_status"].isin(["BUY NOW", "TRENDING"])
    d["trend_up"] = d["mrs"] > 0

    # Explicit preset proxy:
    # - trend regime positive
    # - recent breakout happened
    # - now around breakout level (retest zone)
    # - not in down regime
    d["preset_retest"] = d["trend_ok"] & d["recent_breakout"] & d["in_retest_zone"] & d["trend_up"]

    # Only first day of each contiguous signal block (avoid repeated counting).
    first_hit = d["preset_retest"] & (~d["preset_retest"].shift(1).fillna(False))
    idxs = np.flatnonzero(first_hit.values)
    events: list[Event] = []
    for i in idxs:
        px = float(d["close"].iat[i])
        brk = float(d["brk_lvl"].iat[i]) if np.isfinite(d["brk_lvl"].iat[i]) else float("nan")
        ratio = float(d["ratio_brk"].iat[i]) if np.isfinite(d["ratio_brk"].iat[i]) else float("nan")
        if not np.isfinite(px) or px <= 0 or not np.isfinite(brk) or brk <= 0:
            continue
        r10, dd10 = _forward_metrics(d, i, 10)
        r20, dd20 = _forward_metrics(d, i, 20)
        r40, dd40 = _forward_metrics(d, i, 40)
        events.append(
            Event(
                symbol=symbol,
                date=pd.Timestamp(d.index[i]),
                entry=px,
                mrs=float(d["mrs"].iat[i]),
                brk_lvl=brk,
                pct_vs_brk=(ratio - 1.0) * 100.0,
                status=str(d["mrs_status"].iat[i]),
                max_ret_10=r10,
                dd_10=dd10,
                max_ret_20=r20,
                max_ret_40=r40,
                dd_20=dd20,
                dd_40=dd40,
            )
        )
    return events


def _pct(x: Iterable[bool]) -> float:
    arr = np.asarray(list(x), dtype=bool)
    if arr.size == 0:
        return float("nan")
    return float(arr.mean() * 100.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--pivot-window", type=int, default=20)
    ap.add_argument("--retest-low", type=float, default=0.98, help="PRICE/BRK_LVL lower bound")
    ap.add_argument("--retest-high", type=float, default=1.03, help="PRICE/BRK_LVL upper bound")
    ap.add_argument("--recent-breakout-bars", type=int, default=15)
    ap.add_argument("--start-date", default=None, help="YYYY-MM-DD")
    ap.add_argument("--end-date", default=None, help="YYYY-MM-DD")
    ap.add_argument("--max-symbols", type=int, default=0, help="0 = all")
    ap.add_argument("--min-events", type=int, default=50)
    ap.add_argument("--dump-csv", default=None, help="optional path to save all events CSV")
    args = ap.parse_args()

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    syms = sorted(expected_symbols_for_universe(args.universe))
    if not syms:
        print(f"No symbols found for universe={args.universe!r}")
        raise SystemExit(2)
    if args.max_symbols > 0:
        syms = syms[: args.max_symbols]

    bench_sym = BENCHMARK_MAP.get(args.universe, "NSE:NIFTY500-INDEX")
    b_daily = _load_daily_ohlcv(bench_sym, data_dir)
    if b_daily is None or b_daily.empty:
        print(f"Benchmark parquet missing/unreadable: {bench_sym} in {data_dir}")
        raise SystemExit(2)
    b_weekly_close = _to_weekly_close(b_daily)
    if b_weekly_close.empty:
        print(f"Benchmark weekly close empty: {bench_sym}")
        raise SystemExit(2)

    sd = pd.Timestamp(args.start_date, tz="UTC") if args.start_date else None
    ed = pd.Timestamp(args.end_date, tz="UTC") if args.end_date else None

    events: list[Event] = []
    processed = 0
    for s in syms:
        d = _load_daily_ohlcv(s, data_dir)
        if d is None or len(d) < 120:
            continue
        processed += 1
        events.extend(
            _build_events_for_symbol(
                symbol=s,
                s_daily=d,
                bench_weekly_close=b_weekly_close,
                pivot_window=max(2, int(args.pivot_window)),
                near_low=float(args.retest_low),
                near_high=float(args.retest_high),
                recent_breakout_lookback=max(2, int(args.recent_breakout_bars)),
                start_date=sd,
                end_date=ed,
            )
        )

    if not events:
        print("No events found for this configuration.")
        raise SystemExit(0)

    df = pd.DataFrame([e.__dict__ for e in events]).sort_values(["date", "symbol"])
    if args.dump_csv:
        out_csv = os.path.abspath(args.dump_csv)
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)
        df.to_csv(out_csv, index=False)

    # Success metrics
    valid10 = df["max_ret_10"].replace([np.inf, -np.inf], np.nan).notna()
    valid20 = df["max_ret_20"].replace([np.inf, -np.inf], np.nan).notna()
    valid40 = df["max_ret_40"].replace([np.inf, -np.inf], np.nan).notna()
    n10 = int(valid10.sum())
    n20 = int(valid20.sum())
    n40 = int(valid40.sum())
    hit5_10 = _pct(df.loc[valid10, "max_ret_10"] >= 0.05)
    hit10_10 = _pct(df.loc[valid10, "max_ret_10"] >= 0.10)
    hit20_10 = _pct(df.loc[valid10, "max_ret_10"] >= 0.20)
    hit5_20 = _pct(df.loc[valid20, "max_ret_20"] >= 0.05)
    hit10_20 = _pct(df.loc[valid20, "max_ret_20"] >= 0.10)
    hit20_20 = _pct(df.loc[valid20, "max_ret_20"] >= 0.20)
    hit5_40 = _pct(df.loc[valid40, "max_ret_40"] >= 0.05)
    hit10_40 = _pct(df.loc[valid40, "max_ret_40"] >= 0.10)
    hit20_40 = _pct(df.loc[valid40, "max_ret_40"] >= 0.20)

    med10 = float(df.loc[valid10, "max_ret_10"].median()) if n10 else float("nan")
    med20 = float(df.loc[valid20, "max_ret_20"].median()) if n20 else float("nan")
    med40 = float(df.loc[valid40, "max_ret_40"].median()) if n40 else float("nan")
    dd10 = float(df.loc[valid10, "dd_10"].median()) if n10 else float("nan")
    dd20 = float(df.loc[valid20, "dd_20"].median()) if n20 else float("nan")
    dd40 = float(df.loc[valid40, "dd_40"].median()) if n40 else float("nan")

    print("=== BREAKOUT_RETEST PRESET BACKTEST (approx) ===")
    print(f"universe={args.universe}")
    print(f"benchmark={bench_sym}")
    print(f"data_dir={data_dir}")
    print(
        "rules="
        f"mrs>0 & mrs_status in BUY NOW/TRENDING & recent_breakout({args.recent_breakout_bars}) "
        f"& price/brk in [{args.retest_low:.3f},{args.retest_high:.3f}]"
    )
    print(f"symbols_with_data={processed}/{len(syms)}")
    print(f"events_total={len(df)}")
    if args.start_date or args.end_date:
        print(f"date_range={args.start_date or 'min'}..{args.end_date or 'max'}")
    print("---")
    print(f"10d samples={n10} | hit>=5%: {hit5_10:.2f}% | hit>=10%: {hit10_10:.2f}% | hit>=20%: {hit20_10:.2f}% | median max-ret: {med10*100:.2f}% | median dd: {dd10*100:.2f}%")
    print(f"20d samples={n20} | hit>=5%: {hit5_20:.2f}% | hit>=10%: {hit10_20:.2f}% | hit>=20%: {hit20_20:.2f}% | median max-ret: {med20*100:.2f}% | median dd: {dd20*100:.2f}%")
    print(f"40d samples={n40} | hit>=5%: {hit5_40:.2f}% | hit>=10%: {hit10_40:.2f}% | hit>=20%: {hit20_40:.2f}% | median max-ret: {med40*100:.2f}% | median dd: {dd40*100:.2f}%")

    # Signal sufficiency warning for statistical confidence.
    if len(df) < int(args.min_events):
        print(
            f"WARNING: low event count ({len(df)} < {int(args.min_events)}). "
            "Treat rates as unstable; widen date range or universe."
        )

    # Top 10 recent events snapshot.
    tail = df.tail(10).copy()
    tail["date"] = pd.to_datetime(tail["date"]).dt.strftime("%Y-%m-%d")
    cols = ["date", "symbol", "entry", "mrs", "status", "brk_lvl", "pct_vs_brk", "max_ret_20", "dd_20"]
    print("---")
    print("recent_events(last 10):")
    print(tail[cols].to_string(index=False))


if __name__ == "__main__":
    main()

