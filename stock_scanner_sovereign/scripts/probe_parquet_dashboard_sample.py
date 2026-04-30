#!/usr/bin/env python3
"""Print parquet-replayed structural fields vs timing get_ui_view for a few symbols."""
from __future__ import annotations

import argparse
import os
import sys
import time

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(_ROOT)
sys.path.insert(0, _ROOT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--symbols",
        default="3MINDIA,ABB,ACMESOLAR,AIAENG,AUBANK",
        help="Comma-separated short names (match search / Nifty tickers)",
    )
    ap.add_argument("--universe", default="Nifty 500")
    ap.add_argument("--wait", type=float, default=10.0)
    args = ap.parse_args()

    from backend.breakout_engine import BreakoutScanner
    from backend.breakout_logic import _update_minimal_cycle_state
    from utils.pipeline_bridge import PipelineBridge

    def nse_eq(short: str) -> str:
        s = short.strip().upper()
        return s if ":" in s else f"NSE:{s}-EQ"

    names = [x.strip() for x in str(args.symbols).split(",") if x.strip()]
    pairs = [(n, nse_eq(n)) for n in names]

    bridge = PipelineBridge()
    don = 10

    print("=== PARQUET (PipelineBridge + _update_minimal_cycle_state) ===")
    print("name\tsymbol\tlast_close\tbrk_b_anchor_level\tbrk_lvl\tLAST_TAG_D\t%vs_anchor(close)")
    for name, sym in pairs:
        hv = bridge.get_historical_data(sym, limit=900)
        if hv is None or len(hv) < 6:
            print(f"{name}\t{sym}\t(no parquet)\t\t\t\t")
            continue
        r: dict = {"symbol": sym}
        _update_minimal_cycle_state(r, hv, don_len=don)
        close = float(hv[-1][4])
        anch = float(r.get("brk_b_anchor_level") or 0)
        brkl = float(r.get("brk_lvl") or 0)
        tag = r.get("last_tag") or "—"
        pct = f"{((close / anch) - 1.0) * 100.0:+.4f}%" if anch > 0.0 else "—"
        print(f"{name}\t{sym}\t{close:.4f}\t{anch:.4f}\t{brkl:.4f}\t{tag}\t{pct}")

    sc = BreakoutScanner(universe=args.universe)
    sc.update_universe(args.universe, None)
    print(f"\n(wait {args.wait:.1f}s scanner hydrate…)")
    time.sleep(float(args.wait))

    print("\n=== DASHBOARD / SIDECAR (get_ui_view mode=timing clock=daily) ===")
    print("name\tltp\traw_brk_b_anchor_level\tUI_SINCE_BRK_pct\tLAST_TAG_D\tmanual_LTP_vs_anchor")
    for name, sym in pairs:
        view = sc.get_ui_view(
            page=1,
            page_size=30,
            search=name,
            mode="timing",
            clock_timeframe="daily",
            timing_filter="ALL",
            preset="ALL",
            profile="ALL",
            brk_stage="ALL",
            filter_mrs_grid="ALL",
            wmrs_slope="ALL",
            filter_m_rsi2="ALL",
            sort_key="symbol",
            sort_desc=False,
        )
        rows = view.get("results") or []
        row = rows[0] if rows else None
        if not row:
            print(f"{name}\t(no row)\t\t\t\t")
            continue
        with sc.lock:
            raw = dict(sc.results.get(sym) or {})
        ltp = row.get("ltp")
        ba = raw.get("brk_b_anchor_level")
        ui_pct = row.get("brk_move_live_pct")
        lt = row.get("last_tag")
        try:
            l_f = float(ltp or 0)
            a_f = float(ba or 0)
            man = f"{((l_f / a_f) - 1.0) * 100.0:+.4f}%" if a_f > 0.0 and l_f > 0.0 else "—"
        except (TypeError, ValueError):
            man = "—"
        print(f"{name}\t{ltp}\t{ba}\t{ui_pct}\t{lt}\t{man}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
