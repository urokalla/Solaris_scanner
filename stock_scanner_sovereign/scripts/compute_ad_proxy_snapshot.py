#!/usr/bin/env python3
"""
Compute 65-day Accumulation/Distribution proxy snapshot (A-E) from local parquet history.

Output CSV:
  stock_scanner_sovereign/data/ad_proxy_snapshot.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import DatabaseManager
from utils.pipeline_bridge import PipelineBridge


def _grade_from_ratio(ratio: float) -> str:
    if ratio > 1.50:
        return "A"
    if ratio >= 1.10:
        return "B"
    if ratio >= 0.90:
        return "C"
    if ratio >= 0.50:
        return "D"
    return "E"


def _compute_ad(arr) -> tuple[float, str, float, float, int] | None:
    # PipelineBridge returns columns: timestamp, open, high, low, close, volume
    if arr is None or len(arr) < 66 or arr.shape[1] < 6:
        return None
    close = arr[:, 4]
    volume = arr[:, 5]
    n = len(close)
    start = n - 65

    accum_w = 0.0
    dist_w = 0.0
    active_days = 0

    for i in range(start, n):
        p = i - 1
        if p < 0:
            continue
        c_prev = float(close[p])
        c_now = float(close[i])
        v_prev = float(volume[p])
        v_now = float(volume[i])
        if c_prev <= 0 or v_now <= 0:
            continue

        ret = (c_now / c_prev) - 1.0
        if abs(ret) < 0.002:
            continue
        if v_now <= v_prev:
            continue

        # 50-day volume MA as baseline (up to current bar)
        v_from = max(0, i - 49)
        v_ma50 = float(volume[v_from : i + 1].mean())
        weight = 1.5 if v_now > v_ma50 else 1.0
        weighted_v = v_now * weight
        active_days += 1

        if ret > 0:
            accum_w += weighted_v
        elif ret < 0:
            dist_w += weighted_v

    if dist_w <= 0 and accum_w > 0:
        ratio = 9.99
    elif dist_w <= 0 and accum_w <= 0:
        ratio = 1.0
    else:
        ratio = accum_w / dist_w

    return ratio, _grade_from_ratio(ratio), accum_w, dist_w, active_days


def main() -> int:
    p = argparse.ArgumentParser(description="Compute A/D proxy snapshot from local parquet history.")
    p.add_argument("--universe", default="Nifty 500", help="Universe name from DB symbols table.")
    p.add_argument("--limit", type=int, default=400, help="History rows to load per symbol.")
    p.add_argument(
        "--out",
        default="data/ad_proxy_snapshot.csv",
        help="Output CSV path relative to stock_scanner_sovereign root.",
    )
    args = p.parse_args()

    repo = Path(__file__).resolve().parents[1]
    out_path = (repo / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager()
    bridge = PipelineBridge()
    symbols = db.get_symbols_by_universe(args.universe) or []
    rows: list[dict] = []

    for sym in sorted(set(symbols)):
        arr = bridge.get_historical_data(sym, limit=max(args.limit, 80))
        res = _compute_ad(arr)
        if res is None:
            continue
        ratio, grade, accum_w, dist_w, active_days = res
        rows.append(
            {
                "symbol": sym,
                "ad_ratio": f"{ratio:.4f}",
                "ad_grade": grade,
                "ad_accum_w": f"{accum_w:.2f}",
                "ad_dist_w": f"{dist_w:.2f}",
                "ad_active_days": str(active_days),
            }
        )

    rows.sort(key=lambda r: (r["ad_grade"], -float(r["ad_ratio"])))
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["symbol", "ad_ratio", "ad_grade", "ad_accum_w", "ad_dist_w", "ad_active_days"],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

