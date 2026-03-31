#!/usr/bin/env python3
"""
Event study: **monthly** Wilder RSI(2) < threshold AND **weekly** mRS > floor vs benchmark.

- Monthly RSI(2): ``month_end_close`` (pandas ME) on daily closes, then Wilder RSI(period=2).
  Value as-of each **Friday IST week** = last completed month-end RSI (forward-filled onto week index).

- Weekly mRS: same as scanner / ``backtest_wrsi2_below_forward_weeks`` — (stock/bench) on Friday
  week-closes vs 52-week SMA of ratio, ``((ratio/sma)-1)*10``.

Signal: on each completed week ``t`` where
  monthly_RSI2(t) < ``--mrsi2-max`` (default 5)  AND  weekly_mRS(t) > ``--min-weekly-mrs`` (default 1).

Forward: ``--forward-weeks`` weekly closes:
  ret = close(week t+N) / close(week t) - 1

Optional exits (vs **signal Friday close** as entry):

- ``--exit-on weekly`` (default): scan **Friday** closes only through ``--forward-weeks``.
- ``--exit-on daily``: scan **each session close** after signal Friday through the **last day ≤ horizon Friday** (more realistic if you watch daily closes).

Bracket: ``--stop-loss-pct 7``, ``--take-profit-pct 10`` — each bar, **stop before target**.

Costs: ``--round-trip-pct 0.25`` subtracts that **percent** from every realized return (one line item).

Date filters: ``--signal-after 2018-01-01``, ``--signal-before 2023-12-31`` limit which signals enter the stats.

Examples:
  python scripts/backtest_monthly_rsi2_mrs_forward_weeks.py --universe "Nifty 500"
  python scripts/backtest_monthly_rsi2_mrs_forward_weeks.py --mrsi2-max 5 --min-weekly-mrs 1 --forward-weeks 3
  python scripts/backtest_monthly_rsi2_mrs_forward_weeks.py ... --export-csv events.csv

Grid search (loads data once, ranks parameter combos):
  python scripts/grid_search_mrsi2_mrs.py --universe \"Nifty 500\" --exit-on daily --round-trip-pct 0.3
"""
from __future__ import annotations

import argparse
from collections import Counter
import os
import sys
from datetime import date
from typing import Literal

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.monthly_rsi2_trade_rules import (  # noqa: E402
    month_end_close,
    rsi_wilder,
    week_end_close,
)
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


def _load_close(symbol: str, data_dir: str) -> pd.Series | None:
    path = resolve_parquet_path(symbol, data_dir)
    if not path:
        return None
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
    return out.set_index("ts")["close"]


def _weekly_mrs_aligned(stock_close: pd.Series, bench_close: pd.Series) -> tuple[pd.Series, pd.Series] | None:
    bc = bench_close.reindex(stock_close.index).ffill()
    w_s = week_end_close(stock_close.astype(float))
    w_b = week_end_close(bc.astype(float))
    idx = w_s.index.intersection(w_b.index)
    if len(idx) < 60:
        return None
    w_s = w_s.reindex(idx).astype(float)
    w_b = w_b.reindex(idx).astype(float)
    ratio = w_s / w_b.replace(0, np.nan)
    sma = ratio.shift(1).rolling(52, min_periods=52).mean()
    wmrs = ((ratio / sma) - 1.0) * 10.0
    return w_s, wmrs


def _monthly_rsi2_on_week_index(daily_close: pd.Series, week_index: pd.DatetimeIndex, period: int) -> pd.Series:
    """Monthly RSI(period) on month-end closes, forward-filled onto ``week_index`` (IST weekly labels)."""
    sc = daily_close.dropna().sort_index()
    if len(sc) < 120:
        return pd.Series(index=week_index, dtype=float)
    if sc.index.tz is None:
        sc = sc.tz_localize("UTC")
    m = month_end_close(sc)
    if len(m) < period + 2:
        return pd.Series(index=week_index, dtype=float)
    r = rsi_wilder(m, period=period)
    if r.index.tz is None:
        r = r.copy()
        r.index = r.index.tz_localize("UTC")
    else:
        r = r.tz_convert("UTC")
    w_utc = week_index.tz_convert("UTC") if week_index.tz is not None else week_index
    # Each week needs RSI from the **last completed month-end** on or before that week — not exact index match
    left = pd.DataFrame({"t": w_utc}).sort_values("t")
    right = pd.DataFrame({"t": r.index, "rsi": r.values}).sort_values("t")
    merged = pd.merge_asof(left, right, on="t", direction="backward")
    return pd.Series(merged["rsi"].to_numpy(), index=week_index)


ExitKind = Literal["stop", "tp", "time"]


def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        return t.tz_localize("UTC")
    return t.tz_convert("UTC")


def _realized_ret_daily_bracket(
    daily_close: pd.Series,
    signal_ts: pd.Timestamp,
    horizon_end_ts: pd.Timestamp,
    entry_close: float,
    forward_weeks: int,
    stop_loss_pct: float | None,
    take_profit_pct: float | None,
) -> tuple[float, int, ExitKind]:
    """
    Walk **daily** closes **strictly after** ``signal_ts`` through **≤** ``horizon_end_ts`` (UTC-aligned).
    ``entry_close`` should be the signal **Friday** close (same as weekly series).
    Returns (return, **trading_days** in exit path window, kind).
    """
    c0 = float(entry_close)
    if c0 <= 0 or not np.isfinite(c0):
        return float("nan"), 0, "time"
    _ = max(1, int(forward_weeks))
    sl = abs(float(stop_loss_pct)) / 100.0 if stop_loss_pct is not None and stop_loss_pct > 0 else None
    tp = abs(float(take_profit_pct)) / 100.0 if take_profit_pct is not None and take_profit_pct > 0 else None

    d = daily_close.dropna().sort_index()
    if d.index.tz is None:
        d = d.tz_localize("UTC")
    else:
        d = d.tz_convert("UTC")
    sig = _to_utc(signal_ts)
    end = _to_utc(horizon_end_ts)
    window = d.loc[(d.index > sig) & (d.index <= end)]

    if sl is None and tp is None:
        if window.empty:
            return float("nan"), 0, "time"
        c1 = float(window.iloc[-1])
        return (c1 / c0 - 1.0), int(len(window)), "time"

    n = 0
    for _ts, cj in window.items():
        n += 1
        cj = float(cj)
        if not np.isfinite(cj):
            continue
        rj = cj / c0 - 1.0
        if sl is not None and rj <= -sl:
            return rj, n, "stop"
        if tp is not None and rj >= tp:
            return rj, n, "tp"
    if window.empty:
        return float("nan"), 0, "time"
    cend = float(window.iloc[-1])
    return (cend / c0 - 1.0), int(len(window)), "time"


def _realized_ret_weekly_bracket(
    w_s: pd.Series,
    i: int,
    forward_weeks: int,
    stop_loss_pct: float | None,
    take_profit_pct: float | None,
) -> tuple[float, int, ExitKind]:
    """
    Realized return vs **signal week close** using only **Friday week-end closes**.

    Walks weeks ``i+1 … i+forward_weeks``. On each close: if stop is set and return ≤ −stop%,
    exit (``stop``); else if take-profit is set and return ≥ +tp%, exit (``tp``).
    If neither fires, exit at week ``i+forward_weeks`` (``time``).
    """
    c0 = float(w_s.iloc[i])
    if c0 <= 0 or not np.isfinite(c0):
        return float("nan"), 0, "time"
    fw = max(1, int(forward_weeks))
    sl = abs(float(stop_loss_pct)) / 100.0 if stop_loss_pct is not None and stop_loss_pct > 0 else None
    tp = abs(float(take_profit_pct)) / 100.0 if take_profit_pct is not None and take_profit_pct > 0 else None

    if sl is None and tp is None:
        c1 = float(w_s.iloc[i + fw])
        if not np.isfinite(c1):
            return float("nan"), fw, "time"
        return (c1 / c0 - 1.0), fw, "time"

    for j in range(1, fw + 1):
        cj = float(w_s.iloc[i + j])
        if not np.isfinite(cj):
            return float("nan"), j, "time"
        rj = cj / c0 - 1.0
        if sl is not None and rj <= -sl:
            return rj, j, "stop"
        if tp is not None and rj >= tp:
            return rj, j, "tp"
    cend = float(w_s.iloc[i + fw])
    if not np.isfinite(cend):
        return float("nan"), fw, "time"
    return (cend / c0 - 1.0), fw, "time"


def _print_terminal_breakdown(
    meta: list[tuple[str, pd.Timestamp, float, float, float, int, int, ExitKind]],
    *,
    forward_weeks: int,
    max_event_lines: int,
    exit_on: str,
) -> None:
    """Human-readable summary in the terminal (no spreadsheet needed)."""
    n = len(meta)
    by_sym = Counter(sym for sym, *_ in meta)
    distinct_fridays = len({m[1].date() for m in meta})

    print("\n--- Breakdown (read this in the terminal; no Excel) ---")
    print(f"Total events: {n}  |  Unique symbols: {len(by_sym)}  |  Distinct signal Fridays: {distinct_fridays}")
    print("Events per symbol (most first):")
    for sym, c in by_sym.most_common():
        print(f"  {c}×  {sym}")

    print(f"\nAll events, oldest → newest (realized return % vs signal week close):")
    cap = max_event_lines if max_event_lines > 0 else n
    for j, (sym, ts, mr, mv, rt, hw, hd, kind) in enumerate(meta):
        if j >= cap:
            rest = n - cap
            print(f"  … {rest} more row(s). Use --max-event-lines 0 to print all, or --export-csv PATH to save.")
            break
        kind_tag = {"stop": " stop", "tp": " TP", "time": " time"}.get(kind, "")
        if exit_on == "daily" and hd > 0:
            htag = f"[{hd}d]"
        else:
            htag = f"[{hw}w]"
        print(f"  {ts.date()}  {sym}  mRSI2={mr:.2f}  W_mRS={mv:.2f}  ret={rt * 100:.2f}%  {htag}{kind_tag}")


SymbolPanelRow = tuple[str, pd.Series, pd.Series, pd.Series, pd.Series]


def _signal_date_ok(
    sig_d: date, signal_after: str | None, signal_before: str | None
) -> bool:
    if signal_after:
        lo = pd.to_datetime(signal_after).date()
        if sig_d < lo:
            return False
    if signal_before:
        hi = pd.to_datetime(signal_before).date()
        if sig_d > hi:
            return False
    return True


def build_mrsi2_mrs_panel(
    *,
    universe: str,
    data_dir: str,
    bench: str,
    max_forward_weeks: int,
    rsi_period: int,
    max_symbols: int,
    bench_close: pd.Series | None = None,
) -> tuple[list[SymbolPanelRow], pd.Series]:
    """
    Load all symbols once. Each row must have ``len(weeklys) >= 60 + max_forward_weeks``.
    """
    bc = bench_close if bench_close is not None else _load_close(bench, data_dir)
    if bc is None or bc.empty:
        raise FileNotFoundError(f"Missing benchmark: {bench}")
    syms = sorted(expected_symbols_for_universe(universe))
    if max_symbols > 0:
        syms = syms[:max_symbols]
    panel: list[SymbolPanelRow] = []
    for sym in syms:
        sc = _load_close(sym, data_dir)
        if sc is None or len(sc) < 400:
            continue
        aligned = _weekly_mrs_aligned(sc, bc)
        if aligned is None:
            continue
        w_s, wmrs = aligned
        if len(w_s) < 60 + max_forward_weeks:
            continue
        m_rsi_w = _monthly_rsi2_on_week_index(sc, w_s.index, rsi_period)
        panel.append((sym, sc, w_s, wmrs, m_rsi_w))
    return panel, bc


def evaluate_mrsi2_mrs_event_study(
    *,
    panel: list[SymbolPanelRow],
    mrsi2_max: float,
    min_weekly_mrs: float,
    forward_weeks: int,
    rsi_period: int,
    stop_loss_pct: float | None,
    take_profit_pct: float | None,
    exit_on: str,
    round_trip_pct: float,
    signal_after: str | None,
    signal_before: str | None,
) -> tuple[np.ndarray, list[tuple[str, pd.Timestamp, float, float, float, int, int, ExitKind]], int]:
    fw = max(1, int(forward_weeks))
    friction = max(0.0, float(round_trip_pct)) / 100.0
    rets: list[float] = []
    meta: list[tuple[str, pd.Timestamp, float, float, float, int, int, ExitKind]] = []
    for sym, sc, w_s, wmrs, m_rsi_w in panel:
        if len(w_s) < 60 + fw:
            continue
        for i in range(0, len(w_s) - fw):
            mr = float(m_rsi_w.iloc[i]) if i < len(m_rsi_w) else float("nan")
            mv = float(wmrs.iloc[i])
            if not np.isfinite(mr) or mr >= mrsi2_max:
                continue
            if not np.isfinite(mv) or mv <= min_weekly_mrs:
                continue
            sig_ts = w_s.index[i]
            if not _signal_date_ok(sig_ts.date(), signal_after, signal_before):
                continue
            c0 = float(w_s.iloc[i])
            if exit_on == "daily":
                ret_g, hold_d, ex = _realized_ret_daily_bracket(
                    sc,
                    sig_ts,
                    w_s.index[i + fw],
                    c0,
                    fw,
                    stop_loss_pct,
                    take_profit_pct,
                )
                hold_w = 0
            else:
                ret_g, hold_w, ex = _realized_ret_weekly_bracket(
                    w_s, i, fw, stop_loss_pct, take_profit_pct
                )
                hold_d = 0
            if not np.isfinite(ret_g):
                continue
            ret = ret_g - friction
            rets.append(ret)
            meta.append((sym, sig_ts, mr, mv, ret, hold_w, hold_d, ex))
    arr = np.array(rets, dtype=float)
    return arr, meta, len(panel)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--mrsi2-max", type=float, default=5.0, help="Monthly RSI(2) **strictly below** this")
    ap.add_argument("--min-weekly-mrs", type=float, default=1.0, help="Weekly mRS **strictly above** this")
    ap.add_argument("--forward-weeks", type=int, default=3)
    ap.add_argument("--rsi-period", type=int, default=2)
    ap.add_argument("--max-symbols", type=int, default=0)
    ap.add_argument("--bench", default="NSE:NIFTY500-INDEX")
    ap.add_argument(
        "--export-csv",
        default=None,
        metavar="PATH",
        help="Write every event (symbol, week, mRSI2, W_mRS, forward_ret) to CSV",
    )
    ap.add_argument(
        "--max-event-lines",
        type=int,
        default=0,
        help="Cap how many event rows are printed in the breakdown (0 = print all)",
    )
    ap.add_argument(
        "--no-breakdown",
        action="store_true",
        help="Skip the extra terminal breakdown (counts + full event list)",
    )
    ap.add_argument(
        "--stop-loss-pct",
        type=float,
        default=None,
        metavar="PCT",
        help="Stop: first bar (see --exit-on) with return ≤ −PCT%% vs signal Friday close",
    )
    ap.add_argument(
        "--take-profit-pct",
        type=float,
        default=None,
        metavar="PCT",
        help="Target: first bar with return ≥ +PCT%% vs signal Friday close",
    )
    ap.add_argument(
        "--exit-on",
        choices=("weekly", "daily"),
        default="weekly",
        help="Which closes to scan for stop/target/time exit (horizon still --forward-weeks Friday)",
    )
    ap.add_argument(
        "--round-trip-pct",
        type=float,
        default=0.0,
        metavar="PCT",
        help="Subtract this percent from every realized return (fees+slippage lump sum, e.g. 0.3)",
    )
    ap.add_argument(
        "--signal-after",
        default=None,
        metavar="YYYY-MM-DD",
        help="Only include signals on or after this **Friday** date (inclusive)",
    )
    ap.add_argument(
        "--signal-before",
        default=None,
        metavar="YYYY-MM-DD",
        help="Only include signals on or before this **Friday** date (inclusive)",
    )
    args = ap.parse_args()

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    fw = max(1, int(args.forward_weeks))

    try:
        panel, _bench = build_mrsi2_mrs_panel(
            universe=args.universe,
            data_dir=data_dir,
            bench=args.bench,
            max_forward_weeks=fw,
            rsi_period=args.rsi_period,
            max_symbols=args.max_symbols,
        )
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)

    n_syms = len(panel)
    for k in range(0, n_syms, 75):
        print(f"Scanning {k}/{n_syms}…", flush=True)

    arr, meta, n_loaded = evaluate_mrsi2_mrs_event_study(
        panel=panel,
        mrsi2_max=args.mrsi2_max,
        min_weekly_mrs=args.min_weekly_mrs,
        forward_weeks=fw,
        rsi_period=args.rsi_period,
        stop_loss_pct=args.stop_loss_pct,
        take_profit_pct=args.take_profit_pct,
        exit_on=args.exit_on,
        round_trip_pct=args.round_trip_pct,
        signal_after=args.signal_after,
        signal_before=args.signal_before,
    )
    print(f"\nUniverse: {args.universe} | symbols: {n_loaded}")
    print(
        f"Signal: monthly RSI({args.rsi_period}) < {args.mrsi2_max} "
        f"AND weekly mRS > {args.min_weekly_mrs} vs {args.bench}"
    )
    sl_on = args.stop_loss_pct is not None and args.stop_loss_pct > 0
    tp_on = args.take_profit_pct is not None and args.take_profit_pct > 0
    bar = "Friday weekly" if args.exit_on == "weekly" else "daily session"
    if sl_on or tp_on:
        bits: list[str] = []
        if sl_on:
            bits.append(f"−{abs(args.stop_loss_pct):.2g}% stop ({bar} close vs signal Friday)")
        if tp_on:
            bits.append(f"+{abs(args.take_profit_pct):.2g}% target ({bar} close vs signal Friday)")
        print(
            f"Exit scan: {args.exit_on} closes within {fw} calendar weeks to horizon Friday — "
            f"first hit: {'; '.join(bits)} (stop before target); else exit last bar in window"
        )
    else:
        print(f"Forward: {fw} weekly closes (full hold), exit-on={args.exit_on}")
    if args.round_trip_pct > 0:
        print(f"Friction: −{args.round_trip_pct:.3g}% subtracted from each realized return")
    if args.signal_after or args.signal_before:
        print(
            f"Signal date filter: after={args.signal_after or '—'}  before={args.signal_before or '—'}"
        )
    print(f"Events: {len(arr)}")
    if len(arr) == 0:
        return

    print(f"Success rate (ret > 0): {(arr > 0).mean() * 100:.2f}%")
    print(f"Mean return:   {arr.mean() * 100:.3f}%")
    print(f"Median return: {np.median(arr) * 100:.3f}%")
    print(f"Std return:    {arr.std() * 100:.3f}%")
    print(f"Worst / Best:  {arr.min() * 100:.2f}% / {arr.max() * 100:.2f}%")
    if sl_on or tp_on:
        n_stop = sum(1 for *_, k in meta if k == "stop")
        n_tp = sum(1 for *_, k in meta if k == "tp")
        n_time = sum(1 for *_, k in meta if k == "time")
        print(f"Exits — stop: {n_stop}  |  take-profit: {n_tp}  |  full horizon: {n_time}  (total {len(arr)})")

    meta.sort(key=lambda x: x[1])
    if args.export_csv:
        out_path = os.path.abspath(args.export_csv)
        edf = pd.DataFrame(
            [
                {
                    "symbol": sym,
                    "week_end": ts.isoformat(),
                    "monthly_rsi2": mr,
                    "weekly_mrs": mv,
                    f"ret_{fw}w": rt,
                    "hold_weeks": hw,
                    "hold_trading_days": hd,
                    "exit": ex,
                    "exit_on": args.exit_on,
                    "round_trip_pct_applied": args.round_trip_pct,
                }
                for sym, ts, mr, mv, rt, hw, hd, ex in meta
            ]
        )
        edf.to_csv(out_path, index=False)
        print(f"\nWrote {len(edf)} rows to {out_path}")

    if not args.no_breakdown:
        _print_terminal_breakdown(
            meta, forward_weeks=fw, max_event_lines=args.max_event_lines, exit_on=args.exit_on
        )


if __name__ == "__main__":
    main()
