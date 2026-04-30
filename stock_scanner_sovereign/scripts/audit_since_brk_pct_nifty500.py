#!/usr/bin/env python3
"""
Verify SINCE BRK % (D) rule vs parquet-only structural row (Nifty 500).

Same anchor as daily Breakout Clock SINCE BRK % (D): structural break only:
  anchor = brk_b_anchor_level (if <= 0, UI shows "—"; no rolling brk_lvl fallback)
  pct = ((price / anchor) - 1) * 100 when anchor > 0

Price proxy: last daily bar **close** from parquet (EOD truth). Live UI uses LTP from SHM;
for parquet parity check this proves anchor + % math from the same history the scanner uses.

Run in Docker (from stock_scanner_sovereign):
  PYTHONPATH=. python3 scripts/audit_since_brk_pct_nifty500.py
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _nse_eq(sym: str) -> str:
    s = str(sym or "").strip().upper()
    return s if ":" in s else f"NSE:{s}-EQ"


def _load_nifty500_symbols(csv_path: str) -> list[str]:
    out: list[str] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sym = (row.get("Symbol") or "").strip().upper()
            if sym:
                out.append(_nse_eq(sym))
    return sorted(set(out))


def main() -> int:
    if sys.version_info < (3, 8):
        print("ERROR: need Python >= 3.8")
        return 2

    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=os.path.join(_ROOT, "data", "nifty500.csv"))
    ap.add_argument("--limit", type=int, default=900)
    ap.add_argument("--don-len", type=int, default=10)
    args = ap.parse_args()

    from backend.breakout_logic import _update_minimal_cycle_state
    from utils.pipeline_bridge import PipelineBridge

    bridge = PipelineBridge()
    symbols = _load_nifty500_symbols(args.csv)
    no_hist = 0
    no_anchor = 0
    ok = 0
    rows: list[tuple[str, float, float, float, str]] = []

    for sym in symbols:
        hv = bridge.get_historical_data(sym, limit=int(args.limit))
        if hv is None or len(hv) < 6:
            no_hist += 1
            continue
        r: dict = {"symbol": sym}
        _update_minimal_cycle_state(r, hv, don_len=int(args.don_len))
        ad = float(r.get("brk_b_anchor_level", 0.0) or 0.0)
        close = float(hv[-1][4])
        tag = str(r.get("last_tag") or "—")
        if ad <= 0.0 or close <= 0.0:
            no_anchor += 1
            rows.append((sym, close, max(ad, 0.0), float("nan"), tag))
            continue
        pct = (close / ad - 1.0) * 100.0
        ok += 1
        rows.append((sym, close, ad, pct, tag))

    out_path = os.path.join(_ROOT, "data", "audit_since_brk_pct_nifty500.tsv")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("symbol\tlast_close\tanchor\tpct_eod_proxy\tlast_tag_d\n")
        for sym, close, ad, pct, tag in rows:
            ps = f"{pct:+.4f}" if pct == pct else ""
            f.write(f"{sym}\t{close:.4f}\t{ad:.4f}\t{ps}\t{tag}\n")

    print(f"symbols={len(symbols)} ok_anchor={ok} no_history={no_hist} no_anchor_row={no_anchor}")
    print("anchor = brk_b_anchor_level only (daily clock; matches frozen break level)")
    print("price  = last parquet daily close (EOD proxy for LTP)")
    print("wrote", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
