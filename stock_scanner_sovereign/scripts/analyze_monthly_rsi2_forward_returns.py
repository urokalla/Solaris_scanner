#!/usr/bin/env python3
"""
Event study: monthly RSI(period=2) on Nifty names vs forward returns (daily bars).

- Build month-end close from daily OHLCV Parquet.
- RSI = Wilder RSI on monthly closes, period=2 (Trader/Connors-style monthly RSI2).
- Event: month where monthly RSI2 <= each threshold you pass (default: 2). Separate cohort per level.
- Forward horizon returns from month-end close: trading-day steps
  7, 14, 20, ~1m (21), ~6m (126), ~1y (252).

Examples:
  python scripts/analyze_monthly_rsi2_forward_returns.py --universe "Nifty 500"
  python scripts/analyze_monthly_rsi2_forward_returns.py --rsi-levels "2,5,10"
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
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


def _load_daily_ohlc(symbol: str, data_dir: str) -> pd.DataFrame | None:
    """Daily bars: close + high (high falls back to close if column missing)."""
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
    h_col = cols.get("high")
    if not all([ts_col, c_col]):
        return None
    use = [ts_col, c_col]
    if h_col:
        use.append(h_col)
    s = df[use].copy()
    s.columns = ["ts", "close"] + (["high"] if h_col else [])
    if "high" not in s.columns:
        s["high"] = s["close"]
    s["ts"] = pd.to_datetime(s["ts"], errors="coerce", utc=True)
    s = s.dropna(subset=["ts", "close", "high"])
    s = s.sort_values("ts").drop_duplicates(subset=["ts"], keep="last")
    if s.empty:
        return None
    return s.set_index("ts").sort_index()


def _load_daily_close(symbol: str, data_dir: str) -> pd.Series | None:
    o = _load_daily_ohlc(symbol, data_dir)
    return None if o is None else o["close"]


def rsi_wilder(close: pd.Series, period: int = 2) -> pd.Series:
    """Wilder RSI; `period=2` is RSI(2) on the given timeframe (here: monthly closes)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_g = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_l = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_g / avg_l.replace(0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    out = out.where(avg_l != 0, 100.0)
    out = out.where(avg_g != 0, 0.0)
    return out


def _month_end_close(daily_close: pd.Series) -> pd.Series:
    """Calendar month-end last available close (uses pandas 'ME' bucket)."""
    return daily_close.resample("ME").last().dropna()


def _entry_ix(daily_close: pd.Series, month_end_ts: pd.Timestamp) -> int | None:
    """Index of last daily bar on or before month-end label."""
    ts = pd.Timestamp(month_end_ts)
    pos = int(daily_close.index.searchsorted(ts, side="right") - 1)
    if pos < 0:
        return None
    return pos


def max_runup_high_vs_entry_close(
    high: pd.Series,
    close: pd.Series,
    entry_ix: int,
    forward_trading_days: int,
) -> float:
    """
    Max (high / entry_close - 1) over the next `forward_trading_days` sessions,
    starting the session *after* entry (signal = month-end close).
    """
    entry = float(close.iloc[entry_ix])
    if not np.isfinite(entry) or entry <= 0:
        return float("nan")
    start = entry_ix + 1
    end = start + forward_trading_days
    if start >= len(close) or start >= end:
        return float("nan")
    end = min(end, len(close))
    chunk = high.iloc[start:end]
    if chunk.empty:
        return float("nan")
    return float(chunk.max()) / entry - 1.0


def forward_return_trading_days(daily_close: pd.Series, entry_ix: int, n_days: int) -> float:
    if n_days <= 0 or entry_ix + n_days >= len(daily_close):
        return float("nan")
    a = float(daily_close.iloc[entry_ix])
    b = float(daily_close.iloc[entry_ix + n_days])
    if not (np.isfinite(a) and np.isfinite(b)) or a <= 0:
        return float("nan")
    return b / a - 1.0


HORIZONS: dict[str, int] = {
    "7d_td": 7,
    "14d_td": 14,
    "20d_td": 20,
    "1m_td": 21,
    "6m_td": 126,
    "1y_td": 252,
}


def _parse_rsi_levels(s: str) -> list[float]:
    out: list[float] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    return sorted(set(out))


def _cohort_label(level: float) -> str:
    return f"lte_{int(level)}" if float(level).is_integer() else f"lte_{level}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--max-symbols", type=int, default=0)
    ap.add_argument(
        "--rsi-levels",
        default="2",
        help='Comma-separated max RSI2 (monthly); event when RSI2 <= level. Example: "2" or "2,5,10"',
    )
    ap.add_argument(
        "--runup-window",
        type=int,
        default=252,
        help="Trading days after entry: scan daily HIGH for max run-up vs entry close (0 = skip).",
    )
    ap.add_argument(
        "--runup-target-pct",
        type=float,
        default=50.0,
        help="Report share of events whose max run-up reached at least this %% (e.g. 50).",
    )
    ap.add_argument(
        "--top-runups",
        type=int,
        default=25,
        help="Print this many largest run-ups (0 = don't list).",
    )
    args = ap.parse_args()

    levels = _parse_rsi_levels(args.rsi_levels)
    if not levels:
        print("No --rsi-levels parsed.")
        raise SystemExit(2)

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    syms = sorted(expected_symbols_for_universe(args.universe))
    if args.max_symbols > 0:
        syms = syms[: args.max_symbols]

    records: list[dict[str, object]] = []
    skipped_short = 0

    for sym in syms:
        ohlc = _load_daily_ohlc(sym, data_dir)
        if ohlc is None or len(ohlc) < 300:
            skipped_short += 1
            continue
        d = ohlc["close"]
        hi = ohlc["high"]
        mclose = _month_end_close(d)
        if len(mclose) < 10:
            skipped_short += 1
            continue
        rsi_m = rsi_wilder(mclose, period=2)
        for m_ts, rsi_val in rsi_m.items():
            if pd.isna(rsi_val):
                continue
            ix = _entry_ix(d, m_ts)
            if ix is None:
                continue
            runup = (
                max_runup_high_vs_entry_close(hi, d, ix, args.runup_window)
                if args.runup_window > 0
                else float("nan")
            )
            for L in levels:
                if rsi_val > L:
                    continue
                row: dict[str, object] = {
                    "symbol": sym,
                    "month_end": m_ts,
                    "cohort": _cohort_label(L),
                    "rsi2_m": float(rsi_val),
                    "runup_max": runup,
                }
                for label, h in HORIZONS.items():
                    row[label] = forward_return_trading_days(d, ix, h)
                records.append(row)

    if not records:
        print("No events. Check data path and universe.")
        raise SystemExit(1)

    df = pd.DataFrame(records)
    print(f"Monthly RSI(2) event study — universe={args.universe!r}")
    print(f"Data dir: {data_dir}")
    print(f"Symbols considered: {len(syms)} | skipped (short/miss): {skipped_short}")
    print("Horizons are **trading days after** month-end entry close (see labels).")
    print(f"Cohorts: monthly RSI2 <= each threshold in {levels!r} (same month can appear in wider bands).")
    print("---")

    cohort_order = [_cohort_label(L) for L in levels]
    for cohort in cohort_order:
        sub = df[df["cohort"] == cohort]
        n = len(sub)
        print(f"\n## {cohort} | events = {n}")
        if n == 0:
            continue
        fmt = []
        for label in HORIZONS:
            r = pd.to_numeric(sub[label], errors="coerce")
            r = r[np.isfinite(r)]
            if r.empty:
                fmt.append(f"  {label}: (no complete forwards)")
                continue
            fmt.append(
                f"  {label}: mean={r.mean()*100:+.2f}%  median={r.median()*100:+.2f}%  "
                f"win%={(r>0).mean()*100:.1f}%  n={len(r)}"
            )
        print("\n".join(fmt))

    if args.runup_window > 0 and "runup_max" in df.columns:
        tgt = args.runup_target_pct / 100.0
        w = args.runup_window
        print("\n---")
        print(
            f"Forward run-up: max daily HIGH / entry CLOSE, over next {w} trading sessions "
            f"(starting day after month-end signal)."
        )
        for cohort in cohort_order:
            sub = df[df["cohort"] == cohort]
            ru = pd.to_numeric(sub["runup_max"], errors="coerce")
            ru = ru[np.isfinite(ru)]
            n = len(ru)
            if n == 0:
                continue
            ge = int((ru >= tgt).sum())
            print(f"\n## {cohort} | run-up window={w} td | events with valid run-up: {n}")
            print(f"  Hit >= {args.runup_target_pct:.1f}% run-up: {ge} / {n} ({100.0 * ge / n:.1f}%)")
            print(f"  Run-up: mean={ru.mean()*100:.2f}%  median={ru.median()*100:.2f}%  max={ru.max()*100:.2f}%")
            if args.top_runups > 0:
                top = sub.nlargest(args.top_runups, "runup_max")[
                    ["symbol", "month_end", "rsi2_m", "runup_max"]
                ]
                print(f"  Top {len(top)} by run-up:")
                for _, r in top.iterrows():
                    print(
                        f"    {r['symbol']!s:22} month={str(r['month_end'])[:10]}  "
                        f"RSI2={r['rsi2_m']:.2f}  max_hi_runup={float(r['runup_max'])*100:.1f}%"
                    )


if __name__ == "__main__":
    main()
