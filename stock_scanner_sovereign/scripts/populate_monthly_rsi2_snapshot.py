#!/usr/bin/env python3
"""
Fill ``monthly_rsi2_lt2_snapshot`` for DBeaver / Excel export.

Default **parquet** daily bars (same as ``scan_monthly_rsi2_now.py``); use ``--source db`` for Postgres.

In Docker, `fyers_pipeline` schedules this on weekdays after
``MONTHLY_RSI2_SNAPSHOT_IST_HOUR/MINUTE`` (default 15:00 IST); see ``fyers_data_pipeline/main.py``.

  SELECT * FROM monthly_rsi2_lt2_snapshot
  WHERE snapshot_date = CURRENT_DATE
  ORDER BY universe, rsi2;

Examples:
  python scripts/populate_monthly_rsi2_snapshot.py
  python scripts/populate_monthly_rsi2_snapshot.py --universes "Nifty 50,Nifty 500"
  python scripts/populate_monthly_rsi2_snapshot.py --source db --snapshot-date 2026-03-25 --lte
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from utils.zone_info import ZoneInfo  # noqa: E402

from psycopg2.extras import execute_values

import pandas as pd

from backend.database import DatabaseManager  # noqa: E402
from config.settings import settings  # noqa: E402
from utils.monthly_rsi2_trade_rules import latest_monthly_rsi2  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402


def _load_daily_close_parquet(symbol: str, data_dir: str):
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


def _load_daily_close_db(db: DatabaseManager, symbol: str, limit: int):
    raw = db.get_historical_data(symbol, "1d", limit=limit)
    if raw is None or len(raw) == 0:
        return None
    ts = pd.to_datetime(raw[:, 0], unit="s", utc=True)
    close = raw[:, 4].astype(float)
    s = pd.Series(close, index=ts).sort_index().drop_duplicates(keep="last")
    if len(s) < 80:
        return None
    return s


def _ensure_table(conn) -> None:
    sql_path = os.path.join(SOV, "sql", "monthly_rsi2_lt2_snapshot.sql")
    if not os.path.isfile(sql_path):
        return
    with open(sql_path, encoding="utf-8") as f:
        blob = f.read()
    cur = conn.cursor()
    for part in blob.split(";"):
        stmt = part.strip()
        if not stmt or stmt.startswith("--"):
            continue
        cur.execute(stmt)
    conn.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--snapshot-date",
        default=None,
        help="Store as this calendar date (default: Asia/Kolkata today).",
    )
    ap.add_argument("--universes", default="Nifty 50,Nifty 500")
    ap.add_argument(
        "--source",
        choices=("parquet", "db"),
        default="parquet",
        help="Daily bars: Parquet (default, same as scan_monthly_rsi2_now.py) or Postgres prices 1d",
    )
    ap.add_argument("--data-dir", default=None, help="Parquet root (default: settings.PIPELINE_DATA_DIR)")
    ap.add_argument("--db-limit", type=int, default=2500)
    ap.add_argument("--max-rsi", type=float, default=2.0)
    ap.add_argument("--lte", action="store_true")
    args = ap.parse_args()

    if args.snapshot_date:
        snap = date.fromisoformat(args.snapshot_date)
    else:
        snap = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    univs = [u.strip() for u in args.universes.split(",") if u.strip()]
    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    db = DatabaseManager()

    rows: list[tuple] = []
    for u in univs:
        for sym in sorted(expected_symbols_for_universe(u)):
            if args.source == "parquet":
                s = _load_daily_close_parquet(sym, data_dir)
            else:
                s = _load_daily_close_db(db, sym, args.db_limit)
            if s is None:
                continue
            lr = latest_monthly_rsi2(s, period=2)
            if lr is None:
                continue
            m_ts, rsi, asof_ts, asof_c = lr
            ok = rsi <= args.max_rsi if args.lte else rsi < args.max_rsi
            if not ok:
                continue
            rows.append(
                (
                    snap,
                    u,
                    sym,
                    m_ts.date() if hasattr(m_ts, "date") else snap,
                    float(rsi),
                    asof_ts.date() if hasattr(asof_ts, "date") else snap,
                    float(asof_c),
                )
            )

    with db.get_connection() as conn:
        _ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM monthly_rsi2_lt2_snapshot WHERE snapshot_date = %s",
                (snap,),
            )
            if rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO monthly_rsi2_lt2_snapshot
                    (snapshot_date, universe, symbol, month_bucket, rsi2, last_daily, last_close)
                    VALUES %s
                    ON CONFLICT (snapshot_date, universe, symbol) DO UPDATE SET
                        month_bucket = EXCLUDED.month_bucket,
                        rsi2 = EXCLUDED.rsi2,
                        last_daily = EXCLUDED.last_daily,
                        last_close = EXCLUDED.last_close
                    """,
                    rows,
                )
        conn.commit()

    print(
        f"monthly_rsi2_lt2_snapshot: date={snap} source={args.source} rows={len(rows)} "
        f"universes={univs}"
        + (f" parquet={data_dir}" if args.source == "parquet" else f" db_limit={args.db_limit}")
    )
    print("DBeaver: SELECT * FROM monthly_rsi2_lt2_snapshot WHERE snapshot_date = '...' ORDER BY universe, rsi2;")


if __name__ == "__main__":
    main()
