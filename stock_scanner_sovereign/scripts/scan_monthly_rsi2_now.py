#!/usr/bin/env python3
"""
List symbols whose latest monthly Wilder RSI(2) is below a threshold (default: < 2).

**Current month:** uses the **latest available daily close** in that month (today’s EOD bar once
synced). Pandas labels the month row with the month-end timestamp; the price is **not** “next week”
—it’s the last close in data for that month.

Data source:
  --source parquet (default): daily from Parquet under PIPELINE_DATA_DIR
  --source db: daily from Postgres ``prices`` (timeframe ``1d``)

Examples:
  python scripts/scan_monthly_rsi2_now.py --universes "Nifty 50,Nifty 500"
  python scripts/scan_monthly_rsi2_now.py --source db --db-limit 2500 --universes "Nifty 50,Nifty 500"
  python scripts/scan_monthly_rsi2_now.py --lte --max 2.0 --universe "Nifty 500"
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.monthly_rsi2_trade_rules import latest_monthly_rsi2  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


def _load_daily_close_parquet(symbol: str, data_dir: str) -> pd.Series | None:
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
    if not all([ts_col, c_col]):
        return None
    s = df[[ts_col, c_col]].copy()
    s.columns = ["ts", "close"]
    s["ts"] = pd.to_datetime(s["ts"], errors="coerce", utc=True)
    s = s.dropna(subset=["ts", "close"]).sort_values("ts").drop_duplicates("ts", keep="last")
    if s.empty or len(s) < 80:
        return None
    return s.set_index("ts")["close"]


def _load_daily_close_db(symbol: str, db, limit: int) -> pd.Series | None:
    from backend.database import DatabaseManager  # noqa: PLC0415

    raw = db.get_historical_data(symbol, "1d", limit=limit)
    if raw is None or len(raw) == 0:
        return None
    ts = pd.to_datetime(raw[:, 0], unit="s", utc=True)
    close = raw[:, 4].astype(float)
    s = pd.Series(close, index=ts).sort_index().drop_duplicates(keep="last")
    if len(s) < 80:
        return None
    return s


def _scan_universe(
    name: str,
    *,
    source: str,
    data_dir: str,
    db,
    db_limit: int,
    max_rsi: float,
    lte: bool,
) -> list[tuple[str, pd.Timestamp, float, pd.Timestamp, float]]:
    syms = sorted(expected_symbols_for_universe(name))
    out: list[tuple[str, pd.Timestamp, float, pd.Timestamp, float]] = []
    for sym in syms:
        if source == "db":
            c = _load_daily_close_db(sym, db, db_limit)
        else:
            c = _load_daily_close_parquet(sym, data_dir)
        if c is None:
            continue
        lr = latest_monthly_rsi2(c, period=2)
        if lr is None:
            continue
        m_ts, rsi, asof_ts, asof_c = lr
        ok = rsi <= max_rsi if lte else rsi < max_rsi
        if ok:
            out.append((sym, m_ts, rsi, asof_ts, asof_c))
    out.sort(key=lambda x: x[2])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default=None, help='Single universe display name, e.g. "Nifty 500"')
    ap.add_argument(
        "--universes",
        default=None,
        help='Comma-separated universes (overrides --universe), e.g. "Nifty 50,Nifty 500"',
    )
    ap.add_argument("--data-dir", default=None, help="Parquet root (default: settings.PIPELINE_DATA_DIR)")
    ap.add_argument(
        "--source",
        choices=("parquet", "db"),
        default="parquet",
        help="Daily bars: parquet files or Postgres prices table",
    )
    ap.add_argument("--db-limit", type=int, default=2500, help="Max 1d rows per symbol when --source db")
    ap.add_argument(
        "--max",
        dest="max_rsi",
        type=float,
        default=2.0,
        help="Threshold; default strict match is RSI < this (use --lte for <=).",
    )
    ap.add_argument(
        "--lte",
        action="store_true",
        help="Use RSI <= threshold instead of RSI < threshold.",
    )
    args = ap.parse_args()

    if args.universes:
        univs = [u.strip() for u in args.universes.split(",") if u.strip()]
    elif args.universe:
        univs = [args.universe]
    else:
        univs = ["Nifty 50", "Nifty 500"]

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    op = "<=" if args.lte else "<"

    db = None
    if args.source == "db":
        from backend.database import DatabaseManager  # noqa: PLC0415

        db = DatabaseManager()

    print(f"Monthly RSI(2) | last daily bar in **current month** drives current bucket | RSI2 {op} {args.max_rsi}")
    print(f"Source: {args.source}" + (f" | Parquet: {data_dir}" if args.source == "parquet" else f" | Postgres prices 1d limit={args.db_limit}"))
    print(f"Universes: {univs}")
    print("---")

    for u in univs:
        rows = _scan_universe(
            u,
            source=args.source,
            data_dir=data_dir,
            db=db,
            db_limit=args.db_limit,
            max_rsi=args.max_rsi,
            lte=args.lte,
        )
        print(f"\n## {u} | count = {len(rows)}")
        if not rows:
            continue
        for sym, m_ts, rsi, asof_ts, _asof_c in rows:
            print(
                f"  {sym:28}  m_bucket={str(m_ts)[:10]}  RSI2={rsi:.4f}  last_daily={str(asof_ts)[:10]}"
            )


if __name__ == "__main__":
    main()
