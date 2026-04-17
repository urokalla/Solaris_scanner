#!/usr/bin/env python3
"""
Backtest a non-repainting daily SMC-style sequence on local parquet history.

Long setup studied here:
1. Confirmed bullish CHoCH on a break above the latest confirmed swing high.
2. Confirmed bullish BOS after that bullish CHoCH.
3. A bullish FVG forms on/after the BOS bar.
4. Price later revisits that bullish FVG zone (touch / partial fill).
5. Entry is the close of the first touch bar.

This is intentionally more stable than many Pine overlays:
- swings are confirmed with left/right pivot windows
- no future leak from moving historical pivots after confirmation
- FVGs use completed daily candles only

Example:
  python3 scripts/backtest_smc_choch_bos_fvg.py --universe "Nifty 500"
  python3 scripts/backtest_smc_choch_bos_fvg.py --universe "Nifty 500" --start-date 2016-01-01 --dump-csv tmp/smc.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


@dataclass
class TouchEvent:
    symbol: str
    touch_date: pd.Timestamp
    choch_date: pd.Timestamp
    bos_date: pd.Timestamp
    fvg_date: pd.Timestamp
    entry: float
    fvg_top: float
    fvg_bottom: float
    touch_depth_pct: float
    max_ret_5: float
    max_ret_10: float
    max_ret_20: float
    dd_5: float
    dd_10: float
    dd_20: float


@dataclass
class Trade:
    symbol: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    choch_date: pd.Timestamp
    bos_date: pd.Timestamp
    fvg_date: pd.Timestamp
    entry: float
    stop: float
    target: float
    exit: float
    ret: float
    exit_reason: str
    bars_held: int
    risk_pct: float
    touch_depth_pct: float


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
    for c in ["open", "high", "low", "close"] + (["volume"] if "volume" in out.columns else []):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"])
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    if out.empty:
        return None
    return out.set_index("timestamp")


def _pivot_highs(high: np.ndarray, left: int, right: int) -> np.ndarray:
    n = len(high)
    out = np.zeros(n, dtype=bool)
    for i in range(left, n - right):
        v = high[i]
        if not np.isfinite(v):
            continue
        if np.all(v > high[i - left : i]) and np.all(v >= high[i + 1 : i + 1 + right]):
            out[i] = True
    return out


def _pivot_lows(low: np.ndarray, left: int, right: int) -> np.ndarray:
    n = len(low)
    out = np.zeros(n, dtype=bool)
    for i in range(left, n - right):
        v = low[i]
        if not np.isfinite(v):
            continue
        if np.all(v < low[i - left : i]) and np.all(v <= low[i + 1 : i + 1 + right]):
            out[i] = True
    return out


def _forward_metrics(df: pd.DataFrame, i: int, horizon: int) -> tuple[float, float]:
    entry = float(df["close"].iat[i])
    if not np.isfinite(entry) or entry <= 0:
        return float("nan"), float("nan")
    fwd = df.iloc[i + 1 : i + 1 + horizon]
    if fwd.empty:
        return float("nan"), float("nan")
    mx = float(fwd["high"].max())
    mn = float(fwd["low"].min())
    return (mx / entry) - 1.0, (mn / entry) - 1.0


def _touch_depth_pct(low_px: float, top: float, bottom: float) -> float:
    rng = top - bottom
    if not np.isfinite(rng) or rng <= 0:
        return float("nan")
    touched = top - low_px
    return float(np.clip(touched / rng, 0.0, 1.25) * 100.0)


def _build_events_for_symbol(
    symbol: str,
    d: pd.DataFrame,
    left_bars: int,
    right_bars: int,
    max_wait_after_bos: int,
    min_fvg_pct: float,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
) -> list[TouchEvent]:
    if start_date is not None:
        d = d[d.index >= start_date]
    if end_date is not None:
        d = d[d.index <= end_date]
    if len(d) < max(120, left_bars + right_bars + max_wait_after_bos + 25):
        return []

    high = d["high"].to_numpy(dtype=np.float64)
    low = d["low"].to_numpy(dtype=np.float64)
    close = d["close"].to_numpy(dtype=np.float64)
    idx = d.index.to_list()
    ph = _pivot_highs(high, left_bars, right_bars)
    pl = _pivot_lows(low, left_bars, right_bars)

    trend = 0  # -1 bearish, +1 bullish, 0 unknown
    last_pivot_high_idx = -1
    last_pivot_high = float("nan")
    last_pivot_low_idx = -1
    last_pivot_low = float("nan")

    choch_up_idx = -1
    bos_up_idx = -1
    active_bull_fvg: dict[str, float | int] | None = None
    events: list[TouchEvent] = []

    for i in range(len(d)):
        confirm_idx = i - right_bars
        if confirm_idx >= 0:
            if ph[confirm_idx]:
                last_pivot_high_idx = confirm_idx
                last_pivot_high = high[confirm_idx]
            if pl[confirm_idx]:
                last_pivot_low_idx = confirm_idx
                last_pivot_low = low[confirm_idx]

        broke_up = (
            last_pivot_high_idx >= 0
            and i > last_pivot_high_idx
            and np.isfinite(last_pivot_high)
            and close[i] > last_pivot_high
            and close[i - 1] <= last_pivot_high
        )
        broke_down = (
            i > 0
            and last_pivot_low_idx >= 0
            and i > last_pivot_low_idx
            and np.isfinite(last_pivot_low)
            and close[i] < last_pivot_low
            and close[i - 1] >= last_pivot_low
        )

        if broke_down:
            if trend >= 0:
                trend = -1
            else:
                trend = -1
            active_bull_fvg = None
            choch_up_idx = -1
            bos_up_idx = -1

        if broke_up:
            if trend <= 0:
                trend = 1
                choch_up_idx = i
                bos_up_idx = -1
                active_bull_fvg = None
            else:
                trend = 1
                bos_up_idx = i
                active_bull_fvg = None

        if i >= 2 and trend == 1 and bos_up_idx >= 0:
            gap_bottom = high[i - 2]
            gap_top = low[i]
            if np.isfinite(gap_bottom) and np.isfinite(gap_top) and gap_top > gap_bottom:
                gap_pct = ((gap_top / gap_bottom) - 1.0) * 100.0 if gap_bottom > 0 else 0.0
                if gap_pct >= min_fvg_pct and i >= bos_up_idx:
                    active_bull_fvg = {
                        "created_idx": i,
                        "bottom": float(gap_bottom),
                        "top": float(gap_top),
                    }

        if active_bull_fvg is None:
            continue

        created_idx = int(active_bull_fvg["created_idx"])
        top = float(active_bull_fvg["top"])
        bottom = float(active_bull_fvg["bottom"])
        if i <= created_idx:
            continue
        if max_wait_after_bos > 0 and (i - bos_up_idx) > max_wait_after_bos:
            active_bull_fvg = None
            continue
        if close[i] < bottom:
            active_bull_fvg = None
            continue

        touched = low[i] <= top and high[i] >= bottom
        if not touched:
            continue

        r5, dd5 = _forward_metrics(d, i, 5)
        r10, dd10 = _forward_metrics(d, i, 10)
        r20, dd20 = _forward_metrics(d, i, 20)
        events.append(
            TouchEvent(
                symbol=symbol,
                touch_date=pd.Timestamp(idx[i]),
                choch_date=pd.Timestamp(idx[choch_up_idx]) if choch_up_idx >= 0 else pd.Timestamp(idx[i]),
                bos_date=pd.Timestamp(idx[bos_up_idx]) if bos_up_idx >= 0 else pd.Timestamp(idx[i]),
                fvg_date=pd.Timestamp(idx[created_idx]),
                entry=float(close[i]),
                fvg_top=top,
                fvg_bottom=bottom,
                touch_depth_pct=_touch_depth_pct(float(low[i]), top, bottom),
                max_ret_5=r5,
                max_ret_10=r10,
                max_ret_20=r20,
                dd_5=dd5,
                dd_10=dd10,
                dd_20=dd20,
            )
        )
        active_bull_fvg = None
    return events


def _simulate_trades(
    d: pd.DataFrame,
    events: list[TouchEvent],
    stop_buffer_pct: float,
    stop_mode: str,
    target_r: float,
    max_hold: int,
    fee_per_side: float,
) -> list[Trade]:
    if not events:
        return []
    idx_to_i = {pd.Timestamp(ts): i for i, ts in enumerate(d.index)}
    trades: list[Trade] = []
    next_entry_i = 0
    for e in events:
        entry_i = idx_to_i.get(pd.Timestamp(e.touch_date))
        if entry_i is None or entry_i < next_entry_i:
            continue
        entry_raw = float(d["close"].iat[entry_i])
        if not np.isfinite(entry_raw) or entry_raw <= 0:
            continue
        swing_low = float(d["low"].iloc[max(0, entry_i - 10) : entry_i + 1].min())
        fvg_stop = float(e.fvg_bottom)
        if stop_mode == "fvg":
            stop_base = fvg_stop
        elif stop_mode == "swing":
            stop_base = swing_low
        else:
            stop_base = min(fvg_stop, swing_low)
        stop = stop_base * (1.0 - stop_buffer_pct)
        if not np.isfinite(stop) or stop <= 0 or stop >= entry_raw:
            continue
        risk = (entry_raw / stop) - 1.0
        if not np.isfinite(risk) or risk <= 0:
            continue
        target = entry_raw * (1.0 + target_r * risk)
        entry = entry_raw * (1.0 + fee_per_side)
        exit_i = entry_i
        exit_px = float("nan")
        exit_reason = "OPEN"
        last_i = min(len(d) - 1, entry_i + max_hold)
        for i in range(entry_i + 1, last_i + 1):
            lo = float(d["low"].iat[i])
            hi = float(d["high"].iat[i])
            if np.isfinite(lo) and lo <= stop:
                exit_i = i
                exit_px = stop * (1.0 - fee_per_side)
                exit_reason = "STOP"
                break
            if np.isfinite(hi) and hi >= target:
                exit_i = i
                exit_px = target * (1.0 - fee_per_side)
                exit_reason = "TARGET"
                break
        if exit_reason == "OPEN":
            exit_i = last_i
            raw_exit = float(d["close"].iat[exit_i])
            if not np.isfinite(raw_exit) or raw_exit <= 0:
                continue
            exit_px = raw_exit * (1.0 - fee_per_side)
            exit_reason = "TIMEOUT" if exit_i < len(d) - 1 else "LAST_BAR"
        ret = exit_px / entry - 1.0
        trades.append(
            Trade(
                symbol=e.symbol,
                entry_date=pd.Timestamp(d.index[entry_i]),
                exit_date=pd.Timestamp(d.index[exit_i]),
                choch_date=e.choch_date,
                bos_date=e.bos_date,
                fvg_date=e.fvg_date,
                entry=entry_raw,
                stop=stop,
                target=target,
                exit=exit_px / (1.0 - fee_per_side),
                ret=ret,
                exit_reason=exit_reason,
                bars_held=exit_i - entry_i,
                risk_pct=risk * 100.0,
                touch_depth_pct=e.touch_depth_pct,
            )
        )
        next_entry_i = exit_i + 1
    return trades


def _pct(x: np.ndarray) -> float:
    if x.size == 0:
        return float("nan")
    return float(x.mean() * 100.0)


def _summarize(events: list[TouchEvent], label: str) -> None:
    if not events:
        print(f"{label}: no events")
        return
    df = pd.DataFrame([asdict(e) for e in events])
    print(f"{label}: events={len(df)}")
    for horizon in (5, 10, 20):
        ret = df[f"max_ret_{horizon}"].to_numpy(dtype=np.float64)
        dd = df[f"dd_{horizon}"].to_numpy(dtype=np.float64)
        good_r = ret[np.isfinite(ret)]
        good_d = dd[np.isfinite(dd)]
        if good_r.size == 0:
            continue
        print(
            f"  {horizon:>2}d max_ret mean/median={100*good_r.mean():.2f}%/{100*np.median(good_r):.2f}%"
            f" | win={_pct(good_r > 0):.1f}%"
            f" | dd mean={100*good_d.mean():.2f}%"
        )
    td = df["touch_depth_pct"].to_numpy(dtype=np.float64)
    td = td[np.isfinite(td)]
    if td.size:
        print(f"  touch depth median={np.median(td):.1f}% of FVG | p25/p75={np.percentile(td,25):.1f}%/{np.percentile(td,75):.1f}%")


def _trade_summary(trades: list[Trade]) -> dict[str, float | int]:
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
            "compound_multiple": float("nan"),
        }
    r = np.array([t.ret for t in trades], dtype=float)
    wins = r[r > 0]
    losses = r[r <= 0]
    gross_win = float(wins.sum()) if wins.size else 0.0
    gross_loss = float(losses.sum()) if losses.size else 0.0
    pf = gross_win / abs(gross_loss) if gross_loss < 0 else float("inf")
    eq = float(np.prod(1.0 + r))
    return {
        "n_trades": len(trades),
        "win_rate": float((r > 0).mean()),
        "avg_ret": float(np.mean(r)),
        "median_ret": float(np.median(r)),
        "avg_win": float(np.mean(wins)) if wins.size else float("nan"),
        "avg_loss": float(np.mean(losses)) if losses.size else float("nan"),
        "profit_factor": float(pf),
        "avg_bars_held": float(np.mean([t.bars_held for t in trades])),
        "compound_multiple": eq,
    }


def _print_trade_summary(trades: list[Trade], label: str) -> None:
    st = _trade_summary(trades)
    print(f"{label}: trades={st['n_trades']}")
    if not st["n_trades"]:
        return
    print(
        f"  win={st['win_rate']*100:.1f}% | avg={st['avg_ret']*100:.2f}% | median={st['median_ret']*100:.2f}% | "
        f"avg win/loss={st['avg_win']*100:.2f}%/{st['avg_loss']*100:.2f}%"
    )
    print(
        f"  profit factor={st['profit_factor']:.2f} | avg bars held={st['avg_bars_held']:.1f} | "
        f"naive compounded multiple={st['compound_multiple']:.2f}x"
    )


def _print_symbol_breakdown(trades: list[Trade], top_n: int) -> None:
    if not trades or top_n <= 0:
        return
    rows = pd.DataFrame(
        {
            "symbol": [t.symbol for t in trades],
            "ret": [t.ret for t in trades],
            "bars_held": [t.bars_held for t in trades],
        }
    )
    g = rows.groupby("symbol", as_index=False).agg(
        trades=("ret", "size"),
        win_rate=("ret", lambda s: float((s > 0).mean())),
        avg_ret=("ret", "mean"),
        median_ret=("ret", "median"),
        avg_bars=("bars_held", "mean"),
    )
    g = g.sort_values(["avg_ret", "trades"], ascending=[False, False]).head(top_n)
    if g.empty:
        return
    print(f"Top {len(g)} symbols by average trade return:")
    for _, row in g.iterrows():
        print(
            f"  {row['symbol']}: trades={int(row['trades'])} | win={row['win_rate']*100:.1f}% | "
            f"avg={row['avg_ret']*100:.2f}% | median={row['median_ret']*100:.2f}% | bars={row['avg_bars']:.1f}"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--left-bars", type=int, default=3, help="Pivot bars to the left")
    ap.add_argument("--right-bars", type=int, default=3, help="Pivot bars to the right; makes swings confirmed")
    ap.add_argument("--max-wait-after-bos", type=int, default=20, help="Max sessions from BOS to FVG touch")
    ap.add_argument("--min-fvg-pct", type=float, default=0.25, help="Minimum bullish FVG size in percent")
    ap.add_argument("--start-date", default=None, help="YYYY-MM-DD")
    ap.add_argument("--end-date", default=None, help="YYYY-MM-DD")
    ap.add_argument("--max-symbols", type=int, default=0, help="0 = all universe symbols")
    ap.add_argument("--min-history", type=int, default=200)
    ap.add_argument("--fee-bps", type=float, default=0.0, help="Per-side cost in basis points")
    ap.add_argument("--stop-mode", choices=("fvg", "swing", "wider"), default="wider")
    ap.add_argument("--stop-buffer-pct", type=float, default=0.10, help="Extra stop room below chosen stop base")
    ap.add_argument("--target-r", type=float, default=2.0, help="Target multiple of initial risk")
    ap.add_argument("--max-hold", type=int, default=20, help="Max holding days after entry")
    ap.add_argument("--top-symbols", type=int, default=10, help="Print best symbols by average trade return")
    ap.add_argument("--dump-csv", default=None, help="Optional path to save all touch events")
    ap.add_argument("--dump-trades-csv", default=None, help="Optional path to save simulated trades")
    args = ap.parse_args()

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    syms = sorted(expected_symbols_for_universe(args.universe))
    if not syms:
        print(f"No symbols found for universe={args.universe!r}")
        return 2
    if args.max_symbols > 0:
        syms = syms[: args.max_symbols]

    sd = pd.Timestamp(args.start_date, tz="UTC") if args.start_date else None
    ed = pd.Timestamp(args.end_date, tz="UTC") if args.end_date else None
    fee = max(0.0, float(args.fee_bps)) / 10_000.0

    all_events: list[TouchEvent] = []
    all_trades: list[Trade] = []
    processed = 0
    skipped = 0
    for sym in syms:
        d = _load_daily_ohlcv(sym, data_dir)
        if d is None or len(d) < args.min_history:
            skipped += 1
            continue
        processed += 1
        sym_events = _build_events_for_symbol(
            symbol=sym,
            d=d,
            left_bars=max(1, int(args.left_bars)),
            right_bars=max(1, int(args.right_bars)),
            max_wait_after_bos=max(1, int(args.max_wait_after_bos)),
            min_fvg_pct=max(0.0, float(args.min_fvg_pct)),
            start_date=sd,
            end_date=ed,
        )
        all_events.extend(sym_events)
        all_trades.extend(
            _simulate_trades(
                d=(d[d.index >= sd] if sd is not None else d).loc[:ed] if ed is not None else (d[d.index >= sd] if sd is not None else d),
                events=sym_events,
                stop_buffer_pct=max(0.0, float(args.stop_buffer_pct)) / 100.0,
                stop_mode=str(args.stop_mode),
                target_r=max(0.1, float(args.target_r)),
                max_hold=max(1, int(args.max_hold)),
                fee_per_side=fee,
            )
        )

    print(
        f"SMC CHoCH->BOS->bullish FVG touch | universe={args.universe} | processed={processed} | skipped={skipped} | "
        f"left/right={args.left_bars}/{args.right_bars} | min_fvg={args.min_fvg_pct:.2f}% | max_wait={args.max_wait_after_bos}"
    )
    _summarize(all_events, "All symbols")
    print(
        f"Trade model: stop={args.stop_mode} buffer={args.stop_buffer_pct:.2f}% | target={args.target_r:.2f}R | "
        f"max_hold={args.max_hold} | fee={args.fee_bps:.2f}bps/side"
    )
    _print_trade_summary(all_trades, "Pooled trades")
    _print_symbol_breakdown(all_trades, int(args.top_symbols))

    if args.dump_csv and all_events:
        out = os.path.abspath(args.dump_csv)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        pd.DataFrame([asdict(e) for e in all_events]).sort_values(["touch_date", "symbol"]).to_csv(out, index=False)
        print(f"saved csv: {out}")
    if args.dump_trades_csv and all_trades:
        out = os.path.abspath(args.dump_trades_csv)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        pd.DataFrame([asdict(t) for t in all_trades]).sort_values(["entry_date", "symbol"]).to_csv(out, index=False)
        print(f"saved trades csv: {out}")
    return 0 if all_events else 1


if __name__ == "__main__":
    raise SystemExit(main())
