#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import psycopg2

from frontend_reflex.breakout_engine_manager import get_breakout_scanner


def _weekly_close(hv):
    by_week = {}
    for r in hv:
        try:
            ts = float(r[0])
            close = float(r[4])
        except Exception:
            continue
        if not np.isfinite(ts) or not np.isfinite(close) or close <= 0:
            continue
        d = datetime.fromtimestamp(ts, tz=timezone.utc)
        y, w, _ = d.isocalendar()
        by_week[(int(y), int(w))] = close
    keys = sorted(by_week.keys())
    return keys, np.array([by_week[k] for k in keys], dtype=float)


def _cross_metrics(stock_hv, bench_hv):
    s_keys, s_close = _weekly_close(stock_hv)
    b_keys, b_close = _weekly_close(bench_hv)
    if len(s_keys) < 70 or len(b_keys) < 70:
        return None

    b_idx = {k: i for i, k in enumerate(b_keys)}
    common = [k for k in s_keys if k in b_idx]
    if len(common) < 70:
        return None

    s_map = {k: v for k, v in zip(s_keys, s_close)}
    s = np.array([s_map[k] for k in common], dtype=float)
    b = np.array([b_close[b_idx[k]] for k in common], dtype=float)
    ratio = s / np.maximum(b, 1e-12)
    if len(ratio) < 55:
        return None

    sma52 = np.convolve(ratio, np.ones(52) / 52.0, mode="valid")
    if len(sma52) < 4:
        return None
    mrs = ((ratio[51:] / np.maximum(sma52, 1e-12)) - 1.0) * 100.0

    # mrs[i] corresponds to common[i+51]
    last_cross = -1
    for i in range(1, len(mrs)):
        if mrs[i - 1] <= 0 and mrs[i] > 0:
            last_cross = i
    if last_cross < 0:
        return None

    j = last_cross - 1
    below_weeks = 0
    while j >= 0 and mrs[j] <= 0:
        below_weeks += 1
        j -= 1

    cross_week_key = common[last_cross + 51]
    cross_date = datetime.fromisocalendar(cross_week_key[0], cross_week_key[1], 5).replace(tzinfo=timezone.utc)
    cross_ts = float(cross_date.timestamp())
    from_neg_days = float(max(0, below_weeks) * 7)
    return cross_ts, from_neg_days


def main():
    sc = get_breakout_scanner(universe="Nifty 500")
    sc.update_universe("Nifty 500", None)

    bench_hv = sc.bridge.get_historical_data(sc.bench_sym, limit=2500)
    if bench_hv is None or len(bench_hv) < 300:
        bench_hv = sc.db.get_historical_data(sc.bench_sym, "1d", limit=2500)
    if bench_hv is None or len(bench_hv) < 300:
        print("benchmark history unavailable")
        return

    rows = []
    for sym in sc.symbols:
        hv = sc.bridge.get_historical_data(sym, limit=2500)
        if hv is None or len(hv) < 300:
            hv = sc.db.get_historical_data(sym, "1d", limit=2500)
        if hv is None or len(hv) < 300:
            continue
        m = _cross_metrics(hv, bench_hv)
        if m is None:
            continue
        rows.append((sym, m[0], m[1]))

    conn = psycopg2.connect(host="db", dbname="fyers_db", user="fyers_user", password="fyers_pass")
    cur = conn.cursor()
    updated = 0
    for sym, cross_ts, from_neg_days in rows:
        cur.execute(
            """
            UPDATE live_state
            SET
              mrs_0_cross_unix = CASE
                WHEN mrs_0_cross_unix IS NULL OR mrs_0_cross_unix <= 0 THEN %s
                ELSE mrs_0_cross_unix
              END,
              mrs_0_cross_from_neg_days = GREATEST(COALESCE(mrs_0_cross_from_neg_days, 0), %s)
            WHERE symbol = %s
            """,
            (cross_ts, from_neg_days, sym),
        )
        updated += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"computed={len(rows)} updated={updated}")


if __name__ == "__main__":
    main()
