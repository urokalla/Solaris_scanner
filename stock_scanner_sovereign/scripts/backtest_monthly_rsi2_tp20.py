#!/usr/bin/env python3
"""
Backtest mechanical monthly RSI2 + +20% take-profit (see utils/monthly_rsi2_trade_rules.py).

Writes CSV with: symbol, signal month-end, monthly RSI2, entry_date, entry_price,
exit_date, exit_price, return, exit_reason, bars_held.

Examples:
  python scripts/backtest_monthly_rsi2_tp20.py --universe "Nifty 500" --dump-csv tmp/mrsi2_tp20_trades.csv
  python scripts/backtest_monthly_rsi2_tp20.py --entry next_session_close --exit-mode limit_hit
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.monthly_rsi2_trade_rules import MonthlyRsi2Trade, simulate_monthly_rsi2_trades  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


def _load_daily_ohlc(symbol: str, data_dir: str) -> pd.DataFrame | None:
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
    if s.empty or len(s) < 300:
        return None
    return s.set_index("ts").sort_index()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--rsi-threshold", type=float, default=2.0)
    ap.add_argument("--tp-pct", type=float, default=20.0, help="Take profit percent (e.g. 20 = +20%)")
    ap.add_argument("--max-hold", type=int, default=252)
    ap.add_argument(
        "--entry",
        choices=("signal_month_close", "next_session_close"),
        default="signal_month_close",
        help="signal_month_close = buy last bar of signal month; next_session_close = buy next day close",
    )
    ap.add_argument(
        "--exit-mode",
        choices=("close", "limit_hit"),
        default="close",
        help="close = exit when close crosses +TP%; limit_hit = exit when high touches TP, fill at exact limit",
    )
    ap.add_argument("--max-symbols", type=int, default=0)
    ap.add_argument("--dump-csv", default=None)
    args = ap.parse_args()

    tp_frac = max(0.0, args.tp_pct) / 100.0
    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    syms = sorted(expected_symbols_for_universe(args.universe))
    if args.max_symbols > 0:
        syms = syms[: args.max_symbols]

    all_trades: list[MonthlyRsi2Trade] = []
    skipped = 0
    for sym in syms:
        o = _load_daily_ohlc(sym, data_dir)
        if o is None:
            skipped += 1
            continue
        trades = simulate_monthly_rsi2_trades(
            sym,
            o["close"],
            o["high"],
            rsi_threshold=args.rsi_threshold,
            take_profit_pct=tp_frac,
            entry_mode=args.entry,
            exit_mode=args.exit_mode,
            max_hold_trading_days=args.max_hold,
        )
        all_trades.extend(trades)

    print(f"Monthly RSI2 + {args.tp_pct:.0f}% TP — universe={args.universe!r}")
    print(f"entry={args.entry!r} | exit-mode={args.exit_mode!r} | RSI2 <= {args.rsi_threshold}")
    print(f"data_dir={data_dir} | symbols skipped/missing: {skipped} | trades: {len(all_trades)}")

    if not all_trades:
        raise SystemExit(1)

    reached = [t for t in all_trades if t.exit_reason.startswith("TP20")]
    tmo = [t for t in all_trades if t.exit_reason == "TIMEOUT"]
    print(f"Exit: TP hit: {len(reached)} | TIMEOUT at max_hold: {len(tmo)}")
    rets = pd.Series([t.ret for t in all_trades if t.ret is not None])
    if len(rets):
        print(f"Return/trade: mean={rets.mean()*100:.2f}% median={rets.median()*100:.2f}% win%={(rets>0).mean()*100:.1f}%")

    if args.dump_csv:
        os.makedirs(os.path.dirname(os.path.abspath(args.dump_csv)) or ".", exist_ok=True)
        rows = []
        for t in all_trades:
            rows.append(
                {
                    "symbol": t.symbol,
                    "signal_month_end": t.signal_month_end.isoformat(),
                    "rsi2_monthly": round(t.rsi2_monthly, 4),
                    "entry_date": t.entry_date.isoformat(),
                    "entry_price": t.entry_price,
                    "exit_date": t.exit_date.isoformat() if t.exit_date else "",
                    "exit_price": t.exit_price,
                    "return_pct": round((t.ret or 0) * 100, 4) if t.ret is not None else None,
                    "exit_reason": t.exit_reason,
                    "bars_held": t.bars_held,
                }
            )
        pd.DataFrame(rows).to_csv(args.dump_csv, index=False)
        print(f"Wrote {args.dump_csv}")

if __name__ == "__main__":
    main()
