#!/usr/bin/env python3
"""
Probe one ticker: raw sidecar row vs get_ui_view(mode=timing) and manual % checks.
Run from repo:  cd stock_scanner_sovereign && python3 scripts/probe_breakout_timing_symbol.py --symbol HINDALCO
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

_DEPS_HINT = """\
Missing Python packages (need NumPy for BreakoutScanner).

  cd stock_scanner_sovereign
  python3 -m venv .venv
  source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
  pip install -r requirements.txt
  python scripts/probe_breakout_timing_symbol.py --symbol HINDALCO --universe "Nifty 500"

Or use whatever interpreter already runs your scanner / Reflex app (same venv).
"""


def _pct_move(anchor: object, ltp: object) -> str:
    try:
        a = float(anchor or 0.0)
        l = float(ltp or 0.0)
        if a > 0.0 and l > 0.0:
            return f"{((l / a) - 1.0) * 100.0:+.4f}%"
    except (TypeError, ValueError):
        pass
    return "—"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="HINDALCO", help="Substring match, e.g. HINDALCO")
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--wait", type=float, default=10.0, help="Seconds after update_universe for hydration")
    args = ap.parse_args()
    needle = args.symbol.strip().upper()

    try:
        import numpy  # noqa: F401 — backend requires it
    except ModuleNotFoundError:
        print(_DEPS_HINT, file=sys.stderr)
        return 1

    from backend.breakout_engine import BreakoutScanner

    sc = BreakoutScanner(universe=args.universe)
    sc.update_universe(args.universe, None)
    print(f"Waiting {args.wait:.1f}s for initial hydration…")
    time.sleep(args.wait)

    sym = None
    for s in sc.symbols:
        if needle in s.upper():
            sym = s
            break
    if not sym:
        print(f"ERROR: no symbol containing {needle!r} in {args.universe!r}")
        return 1

    view = sc.get_ui_view(
        page=1,
        page_size=100,
        search=needle,
        profile="ALL",
        brk_stage="ALL",
        filter_mrs_grid="ALL",
        wmrs_slope="ALL",
        filter_m_rsi2="ALL",
        preset="ALL",
        sort_key="symbol",
        sort_desc=False,
        timing_filter="ALL",
        mode="timing",
    )
    rows = view.get("results") or []
    ui = next((r for r in rows if needle in str(r.get("symbol", "")).upper()), None)

    with sc.lock:
        raw = dict(sc.results.get(sym) or {})

    keys = [
        "ltp",
        "rv",
        "change_pct",
        "mrs",
        "brk_lvl",
        "brk_lvl_w",
        "last_tag",
        "last_tag_w",
        "last_event_ts",
        "last_event_ts_w",
        "brk_b_anchor_close",
        "brk_b_anchor_ts",
        "brk_b_anchor_close_w",
        "brk_b_anchor_ts_w",
        "cb_live_entry_px_d",
        "cb_live_entry_px_w",
        "cb_live_entry_day_d",
        "cb_pending_day_d",
        "cb_pending_ts_d",
        "timing_last_tag",
        "timing_last_event_ts",
        "timing_last_tag_w",
        "timing_last_event_ts_w",
        "cb_pending_week_w",
        "cb_pending_ts_w",
    ]

    print("=" * 72)
    print(f"SYMBOL: {sym}")
    print("=" * 72)
    print("--- raw `results` row (after get_ui_view) ---")
    for k in keys:
        if k in raw and raw.get(k) not in (None, "", 0, 0.0):
            print(f"  {k:24s} {raw[k]!r}")
    # always show ltp / brk even if zero
    for k in ("ltp", "brk_lvl", "brk_lvl_w"):
        print(f"  {k:24s} {raw.get(k)!r}")

    ltp = raw.get("ltp")
    print()
    print("--- manual % (same formulas as format_ui_row) ---")
    print(f"  % FROM B (D):   LTP vs brk_b_anchor_close  → {_pct_move(raw.get('brk_b_anchor_close'), ltp)}")
    print(f"  SINCE BRK (D):  LTP vs cb_live_entry_px_d  → {_pct_move(raw.get('cb_live_entry_px_d'), ltp)}")
    print(f"  % FROM B (W):   LTP vs brk_b_anchor_close_w → {_pct_move(raw.get('brk_b_anchor_close_w'), ltp)}")
    print(f"  SINCE BRK (W):  LTP vs cb_live_entry_px_w  → {_pct_move(raw.get('cb_live_entry_px_w'), ltp)}")
    print(f"  ltp > brk_lvl (D)? {float(ltp or 0) > float(raw.get('brk_lvl') or 0)}")

    if ui:
        print()
        print("--- UI row (get_ui_view → format_ui_row) ---")
        for k in (
            "brk_move_pct",
            "brk_move_live_pct",
            "brk_b_anchor_dt",
            "brk_move_pct_w",
            "brk_move_live_pct_w",
            "brk_b_anchor_dt_w",
            "timing_last_tag",
            "timing_last_event_dt",
            "timing_last_tag_w",
            "timing_last_event_dt_w",
            "chp",
            "rv",
            "mrs_weekly",
            "setup_score_ui",
        ):
            print(f"  {k:24s} {ui.get(k)!r}")
    else:
        print()
        print("WARNING: no UI row returned (filters / search). total_count=", view.get("total_count"))

    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
