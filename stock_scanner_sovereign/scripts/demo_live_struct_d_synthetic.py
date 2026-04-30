#!/usr/bin/env python3
"""
Synthetic checks for LIVE_STRUCT_D (backend.live_struct_d).
Run: cd stock_scanner_sovereign && python3 scripts/demo_live_struct_d_synthetic.py
Docker: docker compose run --rm --no-deps sidecar python3 scripts/demo_live_struct_d_synthetic.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from unittest.mock import patch

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from utils.zone_info import ZoneInfo
from backend.live_struct_d import (
    TAG_ET9_WAIT_F21C,
    donchian_next_b_live,
    reconcile_live_struct_d,
    update_live_struct_d_row,
)

_IST = ZoneInfo("Asia/Kolkata")


def _synthetic_hv_for_b_breakout(ltp: float, don_len: int = 5) -> np.ndarray:
    """15 daily rows: rising tape so LTP as last 'close' clears Donchian vs prior window."""
    n = 15
    hv = np.zeros((n, 6), dtype=np.float64)
    for i in range(n):
        ts = float(i * 86400)
        c = 100.0 + float(i)
        h = c + 2.0
        l = c - 1.0
        o = c - 0.1
        hv[i] = (ts, o, h, l, c, 1.0)
    return hv


def _row_b4_trending(e9: float = 112.0, e21: float = 106.0) -> dict:
    return {
        "symbol": "NSE:SYNTH-EQ",
        "last_tag": "B4",
        "b_count": 4,
        "e9t_count": 0,
        "e21c_count": 0,
        "cycle_state": 1,
        "cycle_last_bar_key": "2026-04-29",
        "ema9_d": e9,
        "ema21_d": e21,
        "ltp": 0.0,
    }


def _print_state(label: str, d: dict) -> None:
    print(
        f"  [{label}] live_struct_d={d.get('live_struct_d')!r} "
        f"lsd_latch={d.get('lsd_latch')!r} ge9={d.get('lsd_ge9', 0)} "
        f"touch={d.get('lsd_e9ct_touch', 0)} streak={d.get('lsd_under9_streak', 0)}"
    )


def main() -> int:
    print("=== LIVE_STRUCT_D synthetic demo ===\n")

    # --- 1) B5 Breakout_Live_Watch (Donchian + LTP) ---
    hv = _synthetic_hv_for_b_breakout(ltp=120.0, don_len=5)
    d = _row_b4_trending(e9=110.0, e21=105.0)
    d["ltp"] = 120.0
    assert donchian_next_b_live(hv, 120.0, 5, 110.0, 105.0), "sanity: synthetic hv should Donchian-break"
    t0 = datetime(2026, 4, 29, 10, 0, 0, tzinfo=_IST)
    update_live_struct_d_row(d, hv, 5, t0)
    print("1) B4 + LTP clears Donchian + stack → expect B5_Breakout_Live_Watch")
    _print_state("after live update", d)
    assert "B5_Breakout_Live_Watch" in str(d.get("live_struct_d")), d

    # EOD reconcile → B5_Confirmed (last_tag B5)
    d["last_tag"] = "B5"
    d["b_count"] = 5
    with patch("backend.live_struct_d._eod_gate", return_value=True):
        reconcile_live_struct_d(d, datetime(2026, 4, 29, 17, 0, 0, tzinfo=_IST))
    print("   EOD reconcile last_tag=B5 → expect B5_Confirmed")
    _print_state("after reconcile", d)
    assert d.get("live_struct_d") == "B5_Confirmed", d

    # --- 2) E9CT1_Live_Watch (touch under 9, reclaim) ---
    d2 = {
        "symbol": "NSE:SYNTH2-EQ",
        "last_tag": "B1",
        "b_count": 1,
        "e9t_count": 0,
        "e21c_count": 0,
        "cycle_state": 1,
        "cycle_last_bar_key": "2026-04-29",
        "ema9_d": 100.0,
        "ema21_d": 95.0,
        "lsd_ge9": 0,
        "lsd_e9ct_touch": 0,
        "lsd_under9_streak": 0,
        "ltp": 101.0,
    }
    hv2 = _synthetic_hv_for_b_breakout(101.0)
    update_live_struct_d_row(d2, hv2, 5, t0)  # ge9
    d2["ltp"] = 98.0
    update_live_struct_d_row(d2, hv2, 5, t0)  # touch
    d2["ltp"] = 101.5
    update_live_struct_d_row(d2, hv2, 5, t0)  # reclaim → E9CT1_Live_Watch
    print("\n2) B1 touch EMA9 then reclaim → expect E9CT1_Live_Watch")
    _print_state("after reclaim", d2)
    assert "E9CT1_Live_Watch" in str(d2.get("live_struct_d")), d2

    d2["last_tag"] = "E9CT1"
    with patch("backend.live_struct_d._eod_gate", return_value=True):
        reconcile_live_struct_d(d2, datetime(2026, 4, 29, 17, 0, 0, tzinfo=_IST))
    print("   EOD last_tag=E9CT1 → E9CT1_Confirmed")
    _print_state("after reconcile", d2)
    assert d2.get("live_struct_d") == "E9CT1_Confirmed", d2

    # --- 3) ET9DNWF21C_Live_Watch (two polls under 9, no reclaim) ---
    d3 = {
        "symbol": "NSE:SYNTH3-EQ",
        "last_tag": "B2",
        "b_count": 2,
        "e9t_count": 0,
        "e21c_count": 0,
        "cycle_state": 1,
        "cycle_last_bar_key": "2026-04-29",
        "ema9_d": 100.0,
        "ema21_d": 95.0,
        "ltp": 102.0,
        "lsd_ge9": 0,
        "lsd_e9ct_touch": 0,
        "lsd_under9_streak": 0,
    }
    hv3 = _synthetic_hv_for_b_breakout(50.0)  # no B5 breakout
    update_live_struct_d_row(d3, hv3, 5, t0)  # ge9
    d3["ltp"] = 98.0
    update_live_struct_d_row(d3, hv3, 5, t0)  # streak 1
    d3["ltp"] = 97.0
    update_live_struct_d_row(d3, hv3, 5, t0)  # streak 2 → ET9 live watch
    print("\n3) B2 two polls under EMA9 without reclaim → ET9DNWF21C_Live_Watch")
    _print_state("after 2 under", d3)
    assert TAG_ET9_WAIT_F21C in str(d3.get("live_struct_d")), d3

    # --- 4) E21C1_Live_Watch (pullback + reclaim both EMAs) ---
    d4 = {
        "symbol": "NSE:SYNTH4-EQ",
        "last_tag": TAG_ET9_WAIT_F21C,
        "b_count": 2,
        "e9t_count": 0,
        "e21c_count": 0,
        "cycle_state": 2,
        "cycle_last_bar_key": "2026-04-29",
        "ema9_d": 100.0,
        "ema21_d": 99.0,
        "ltp": 102.0,
        "lsd_ge9": 0,
        "lsd_e9ct_touch": 0,
        "lsd_under9_streak": 0,
    }
    hv4 = _synthetic_hv_for_b_breakout(50.0)
    update_live_struct_d_row(d4, hv4, 5, t0)
    print("\n4) ET9 + cycle_state=2 + LTP above E9 & E21 → E21C1_Live_Watch")
    _print_state("after pullback reclaim", d4)
    assert "E21C1_Live_Watch" in str(d4.get("live_struct_d")), d4

    # --- 5) Cross-branch: latched B5 watch, EOD prints E9CT1 ---
    d5 = _row_b4_trending()
    d5["live_struct_d"] = "B5_Breakout_Live_Watch"
    d5["lsd_latch"] = "B:5"
    d5["lsd_ist_day"] = "2026-04-29"
    d5["last_tag"] = "E9CT1"
    d5["cycle_last_bar_key"] = "2026-04-29"
    with patch("backend.live_struct_d._eod_gate", return_value=True):
        reconcile_live_struct_d(d5, datetime(2026, 4, 29, 17, 0, 0, tzinfo=_IST))
    print("\n5) Latch B5 watch, EOD last_tag=E9CT1 → cross-branch string")
    _print_state("cross", d5)
    assert "E9CT1_Confirmed" in str(d5.get("live_struct_d")), d5
    assert "B5_live_aborted" in str(d5.get("live_struct_d")), d5

    print("\n=== All synthetic checks passed ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
