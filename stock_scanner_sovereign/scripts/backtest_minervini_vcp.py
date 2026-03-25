#!/usr/bin/env python3
"""
Offline backtest for :func:`utils.minervini_vcp.vcp_features` on daily Parquet history.

Does not touch the dashboard, sidecar, or scanner — run from the repo root or anywhere
with ``stock_scanner_sovereign`` on the path (script fixes ``sys.path``).

Example:
  cd stock_scanner_sovereign
  python3 scripts/backtest_minervini_vcp.py --universe "Nifty 500"
  # Faster scan: last 1200 bars only, evaluate every 3 days
  python3 scripts/backtest_minervini_vcp.py --universe "Nifty 500" --tail-bars 1200 --day-step 3

Progress prints to stderr; summary stats to stdout. If it "hangs", watch stderr for ``[vcp-bt]``.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.constants import BENCHMARK_MAP  # noqa: E402
from utils.minervini_vcp import vcp_features  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


@dataclass
class VCPEvent:
    symbol: str
    date: pd.Timestamp
    entry: float
    mrs: float
    mrs_status: str
    vcp_note: str
    max_ret_10: float
    dd_10: float
    max_ret_20: float
    dd_20: float
    max_ret_40: float
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
    return pd.DataFrame(
        {
            "mrs": mrs.astype(float),
            "mrs_prev": mrs_prev.astype(float),
            "mrs_signal": mrs_signal.astype(float),
            "mrs_status": status,
        }
    ).dropna(subset=["mrs"])


def _forward_metrics_np(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    i: int,
    horizon: int,
) -> tuple[float, float]:
    entry = float(close[i])
    if not np.isfinite(entry) or entry <= 0:
        return float("nan"), float("nan")
    hi = high[i + 1 : i + 1 + horizon]
    lo = low[i + 1 : i + 1 + horizon]
    if hi.size == 0:
        return float("nan"), float("nan")
    mx, mn = float(np.max(hi)), float(np.min(lo))
    max_ret = (mx / entry) - 1.0 if np.isfinite(mx) and mx > 0 else float("nan")
    dd = (mn / entry) - 1.0 if np.isfinite(mn) and mn > 0 else float("nan")
    return max_ret, dd


def _daily_to_ohlcv_np(d: pd.DataFrame) -> np.ndarray:
    """Oldest-first ndarray for :func:`vcp_features`."""
    idx = pd.to_datetime(d.index, utc=True)
    ts = (idx.astype("int64") // 10**9).to_numpy(dtype=np.float64)
    o = d["open"].to_numpy(dtype=np.float64)
    h = d["high"].to_numpy(dtype=np.float64)
    low = d["low"].to_numpy(dtype=np.float64)
    c = d["close"].to_numpy(dtype=np.float64)
    if "volume" in d.columns:
        v = d["volume"].to_numpy(dtype=np.float64)
        return np.column_stack([ts, o, h, low, c, v])
    return np.column_stack([ts, o, h, low, c])


def _build_vcp_events_for_symbol(
    symbol: str,
    s_daily: pd.DataFrame,
    bench_weekly_close: pd.Series,
    lookback: int,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
    require_mrs_positive: bool,
    vcp_kwargs: dict,
    tail_bars: int,
    day_step: int,
) -> list[VCPEvent]:
    weekly = _compute_weekly_mrs(_to_weekly_close(s_daily), bench_weekly_close)
    if weekly.empty:
        return []

    wk = weekly.copy()
    wk.index = wk.index.tz_convert("UTC") if wk.index.tz is not None else wk.index.tz_localize("UTC")
    d = pd.merge_asof(
        s_daily.reset_index().sort_values("timestamp"),
        wk.reset_index().rename(columns={"index": "timestamp"}).sort_values("timestamp"),
        on="timestamp",
        direction="backward",
    ).set_index("timestamp")
    d = d[~d.index.duplicated(keep="last")]
    d = d.dropna(subset=["mrs"])
    if d.empty:
        return []

    if start_date is not None:
        d = d[d.index >= start_date]
    if end_date is not None:
        d = d[d.index <= end_date]
    if tail_bars and len(d) > int(tail_bars):
        d = d.iloc[-int(tail_bars) :]

    min_need = max(lookback + 45, 120)
    if len(d) < min_need:
        return []

    horizon = 40
    ohlcv_full = _daily_to_ohlcv_np(d)
    mrs_arr = d["mrs"].to_numpy(dtype=np.float64)
    mrs_status_arr = d["mrs_status"].to_numpy()
    close_arr = d["close"].to_numpy(dtype=np.float64)
    high_arr = d["high"].to_numpy(dtype=np.float64)
    low_arr = d["low"].to_numpy(dtype=np.float64)
    idx_times = d.index.to_numpy()

    n = len(d)
    idx_start = lookback - 1
    rng_end = n - horizon
    # Optional stride: still detect first-on after off when step>1 by scanning stepped indices only
    step = max(1, int(day_step))
    i_list = list(range(idx_start, rng_end, step))
    if not i_list:
        return []

    flags: list[bool] = []
    notes: list[str] = []
    for i in i_list:
        if require_mrs_positive and mrs_arr[i] <= 0:
            flags.append(False)
            notes.append("")
            continue
        win = ohlcv_full[i - lookback + 1 : i + 1]
        feat = vcp_features(win, lookback=lookback, **vcp_kwargs)
        flags.append(bool(feat["vcp_ok"]))
        notes.append(str(feat.get("vcp_note") or ""))

    events: list[VCPEvent] = []
    for j, i in enumerate(i_list):
        if not flags[j]:
            continue
        if j > 0 and flags[j - 1]:
            continue
        r10, dd10 = _forward_metrics_np(high_arr, low_arr, close_arr, i, 10)
        r20, dd20 = _forward_metrics_np(high_arr, low_arr, close_arr, i, 20)
        r40, dd40 = _forward_metrics_np(high_arr, low_arr, close_arr, i, 40)
        events.append(
            VCPEvent(
                symbol=symbol,
                date=pd.Timestamp(idx_times[i]),
                entry=float(close_arr[i]),
                mrs=float(mrs_arr[i]),
                mrs_status=str(mrs_status_arr[i]),
                vcp_note=notes[j],
                max_ret_10=r10,
                dd_10=dd10,
                max_ret_20=r20,
                dd_20=dd20,
                max_ret_40=r40,
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
    ap = argparse.ArgumentParser(description="Backtest Minervini-style VCP proxy on Parquet daily data.")
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--lookback", type=int, default=90, help="Trading days fed into vcp_features")
    ap.add_argument("--n-segments", type=int, default=3)
    ap.add_argument("--min-step", type=float, default=0.07, dest="min_relax_step")
    ap.add_argument("--vol-dryup", type=float, default=0.88, help="Set negative to disable volume dry-up")
    ap.add_argument("--no-constructive", action="store_true", help="Skip near-high constructive filter")
    ap.add_argument("--no-mrs-filter", action="store_true", help="Allow VCP signals when weekly mRS <= 0")
    ap.add_argument("--start-date", default=None)
    ap.add_argument("--end-date", default=None)
    ap.add_argument("--max-symbols", type=int, default=0, help="0 = all universe symbols with parquet")
    ap.add_argument(
        "--tail-bars",
        type=int,
        default=2500,
        help="Use only the last N daily bars after date filters (speed; 0 = full history). Default 2500.",
    )
    ap.add_argument(
        "--day-step",
        type=int,
        default=1,
        help="Evaluate VCP every N trading days (1 = full scan; 5 ≈ 5× faster, coarser events).",
    )
    ap.add_argument(
        "--progress-every",
        type=int,
        default=20,
        help="Print progress to stderr every K symbols (0 = quiet).",
    )
    ap.add_argument("--dump-csv", default=None)
    args = ap.parse_args()

    vol_ratio = float(args.vol_dryup) if float(args.vol_dryup) >= 0 else None
    vcp_kwargs = {
        "n_segments": int(args.n_segments),
        "min_relax_step": float(args.min_relax_step),
        "volume_dryup_ratio": vol_ratio,
        "require_constructive": not bool(args.no_constructive),
    }

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    syms = sorted(expected_symbols_for_universe(args.universe))
    if not syms:
        print(f"No symbols for universe={args.universe!r}")
        raise SystemExit(2)
    if args.max_symbols > 0:
        syms = syms[: int(args.max_symbols)]

    bench_sym = BENCHMARK_MAP.get(args.universe, "NSE:NIFTY500-INDEX")
    b_daily = _load_daily_ohlcv(bench_sym, data_dir)
    if b_daily is None or b_daily.empty:
        print(f"Benchmark missing: {bench_sym}")
        raise SystemExit(2)
    b_weekly = _to_weekly_close(b_daily)
    if b_weekly.empty:
        raise SystemExit(2)

    sd = pd.Timestamp(args.start_date, tz="UTC") if args.start_date else None
    ed = pd.Timestamp(args.end_date, tz="UTC") if args.end_date else None

    tail_bars = int(args.tail_bars) if int(args.tail_bars) > 0 else 0
    ev_every = int(args.progress_every)
    print(
        f"[vcp-bt] data_dir={data_dir} symbols_in_universe={len(syms)} "
        f"tail_bars={'ALL' if not tail_bars else tail_bars} day_step={int(args.day_step)}",
        file=sys.stderr,
    )

    events: list[VCPEvent] = []
    processed = 0
    t0 = time.perf_counter()
    for k, s in enumerate(syms, start=1):
        d0 = _load_daily_ohlcv(s, data_dir)
        if d0 is None or len(d0) < 120:
            continue
        processed += 1
        if ev_every and processed % ev_every == 0:
            print(f"[vcp-bt] symbols_done={processed}/{len(syms)} elapsed_s={time.perf_counter() - t0:.1f}", file=sys.stderr)
        events.extend(
            _build_vcp_events_for_symbol(
                symbol=s,
                s_daily=d0,
                bench_weekly_close=b_weekly,
                lookback=int(args.lookback),
                start_date=sd,
                end_date=ed,
                require_mrs_positive=not bool(args.no_mrs_filter),
                vcp_kwargs=vcp_kwargs,
                tail_bars=tail_bars,
                day_step=int(args.day_step),
            )
        )

    print(f"Universe={args.universe!r} | symbols_loaded={processed} | VCP events={len(events)}")
    if not events:
        print("No VCP first-triggers in range. Loosen flags (--no-constructive, --no-mrs-filter, smaller --min-step).")
        raise SystemExit(0)

    df = pd.DataFrame([e.__dict__ for e in events]).sort_values(["date", "symbol"])
    if args.dump_csv:
        path = os.path.abspath(args.dump_csv)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        df.to_csv(path, index=False)
        print(f"Wrote {path}")

    for h, lab in [(10, "10d"), (20, "20d"), (40, "40d")]:
        col = f"max_ret_{h}"
        v = df[col].replace([np.inf, -np.inf], np.nan).dropna()
        if v.empty:
            continue
        print(
            f"{lab}: n={len(v)} | "
            f"median_max_ret={float(v.median()) * 100:.2f}% | "
            f"p(max_ret>=5%)={_pct(v >= 0.05):.1f}% | "
            f"p(max_ret>=10%)={_pct(v >= 0.10):.1f}%"
        )


if __name__ == "__main__":
    main()
