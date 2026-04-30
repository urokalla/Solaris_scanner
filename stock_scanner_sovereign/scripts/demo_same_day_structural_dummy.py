#!/usr/bin/env python3
"""
Dummy OHLC + real _update_minimal_cycle_state: prove when LAST TAG D can show B1
when the last parquet row is *today* (same calendar session as IST "now").

Run (needs numpy):
  cd stock_scanner_sovereign && python3 scripts/demo_same_day_structural_dummy.py

Or Docker:
  docker compose run --rm --no-deps sidecar python3 scripts/demo_same_day_structural_dummy.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from utils.zone_info import ZoneInfo
from backend.breakout_logic import _update_minimal_cycle_state
from config.settings import settings

_IST = ZoneInfo("Asia/Kolkata")


def build_dummy_hv() -> np.ndarray:
    """
    Daily rows ending **2026-04-27** IST (same session date as the test "now").
    Slow grind up, then last bar spikes so B1 appears only when that last row
    is included in replay (i = len-1), not when replay stops at len-2.
    """
    n = 45
    hv = np.zeros((n, 6), dtype=np.float64)
    last_day = datetime(2026, 4, 27, 15, 30, 0, tzinfo=_IST)
    start = last_day - timedelta(days=n - 1)
    base = 100.0
    for idx in range(n):
        ts = (start + timedelta(days=idx)).timestamp()
        c = base + idx * 0.15
        o, h, l = c - 0.05, c + 0.6, c - 0.6
        if idx == n - 1:
            c, h, l, o = 135.0, 136.0, 134.0, 134.5
        hv[idx] = (ts, o, h, l, c, 1.0)
    return hv


def _patch_datetime(fixed: datetime):
    """Patch breakout_logic.datetime: only .now() fixed; .fromtimestamp stays real."""
    import backend.breakout_logic as bl

    class _DT:
        __slots__ = ()

        @staticmethod
        def now(tz=None):
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed if fixed.tzinfo else fixed.replace(tzinfo=tz)

        @staticmethod
        def fromtimestamp(ts, tz=None):
            return datetime.fromtimestamp(ts, tz=tz)

        @staticmethod
        def combine(d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    return patch.object(bl, "datetime", _DT)


def run_case(label: str, fixed_now: datetime) -> tuple[str, str]:
    hv = build_dummy_hv()
    r: dict = {}
    with _patch_datetime(fixed_now):
        _update_minimal_cycle_state(r, hv, don_len=10, weekly=False)
    lt = str(r.get("last_tag") or "—")
    bk = str(r.get("cycle_last_bar_key") or "")
    return lt, bk


def main() -> int:
    hv = build_dummy_hv()
    last_d = datetime.fromtimestamp(float(hv[-1][0]), tz=_IST).date()
    print("Dummy symbol: NSE:DUMMY-EQ (synthetic hv only)")
    print(f"Last row IST session date: {last_d}")
    print(
        "STRUCTURAL_SAMEDAY_AFTER_EOD:",
        settings.STRUCTURAL_SAMEDAY_AFTER_EOD_ENABLED,
        f"{settings.STRUCTURAL_SAMEDAY_AFTER_EOD_IST_HOUR:02d}:"
        f"{settings.STRUCTURAL_SAMEDAY_AFTER_EOD_IST_MINUTE:02d} IST",
    )
    print()

    # Same calendar day as last bar, *before* cutoff → structural bar index uses prior day.
    before = datetime(2026, 4, 27, 14, 0, 0, tzinfo=_IST)
    lt_b, bk_b = run_case("before cutoff", before)
    print(f"A) IST now = {before.strftime('%Y-%m-%d %H:%M')} (before cutoff, same day as last bar)")
    print(f"   last_tag={lt_b!r}  cycle_last_bar_key={bk_b!r}")

    # Same calendar day, *after* cutoff → last row included.
    after = datetime(2026, 4, 27, 17, 0, 0, tzinfo=_IST)
    lt_a, bk_a = run_case("after cutoff", after)
    print(f"B) IST now = {after.strftime('%Y-%m-%d %H:%M')} (after cutoff, same day as last bar)")
    print(f"   last_tag={lt_a!r}  cycle_last_bar_key={bk_a!r}")

    # Next calendar day → last row always included (no same-day defer).
    nxt = datetime(2026, 4, 28, 10, 0, 0, tzinfo=_IST)
    lt_n, bk_n = run_case("next day", nxt)
    print(f"C) IST now = {nxt.strftime('%Y-%m-%d %H:%M')} (next session day)")
    print(f"   last_tag={lt_n!r}  cycle_last_bar_key={bk_n!r}")

    print()
    if lt_b != "B1" and lt_a == "B1":
        print(
            "Proof: B1 is NOT assigned for structural replay before the cutoff on the same day, "
            "but IS assigned after the cutoff — same calendar day, no need to wait until the 28th."
        )
    elif lt_b == "B1":
        print("Note: before-cutoff already B1 (cutoff/window vs data edge); check STRUCTURAL_* env.")
    else:
        print("Unexpected outcome; inspect hv or don_len.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
