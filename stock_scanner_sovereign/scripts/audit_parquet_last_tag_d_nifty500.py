#!/usr/bin/env python3
"""
Audit: structural LAST TAG D vs local daily parquet (Nifty 500 sample).

Proof chain (same as dashboard /breakout-clock-daily structural column):
  1) ``PipelineBridge.get_historical_data`` reads ONLY ``PIPELINE_DATA_DIR/*.parquet``
     (see ``utils/pipeline_bridge.py``).
  2) ``backend.breakout_logic._update_minimal_cycle_state`` is the same function the
     breakout scanner uses to populate ``last_tag`` on daily bars.

This script does NOT call the Reflex UI; it reproduces the exact structural tag the
grid shows as LAST TAG D (``format_ui_row`` passes through ``last_tag`` unchanged).

Usage (from ``stock_scanner_sovereign/``):
  PYTHONPATH=. python3 scripts/audit_parquet_last_tag_d_nifty500.py --sample 120

Optional:
  --csv path/to/nifty500.csv   (default: data/nifty500.csv under this package)
  --seed 42                    (reproducible random sample)
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import sys
from datetime import datetime, timezone

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_update_minimal_cycle_state = None
PipelineBridge = None
resolve_parquet_path = None


def _nse_eq(sym: str) -> str:
    s = str(sym or "").strip().upper()
    if ":" in s:
        return s
    return f"NSE:{s}-EQ"


def _load_nifty500_symbols(csv_path: str) -> list[str]:
    out: list[str] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sym = (row.get("Symbol") or "").strip().upper()
            if sym:
                out.append(_nse_eq(sym))
    return sorted(set(out))


def _parquet_last_ts_unix(path: str) -> float | None:
    """Last daily bar timestamp in parquet as unix seconds (float), independent of PipelineBridge."""
    try:
        import pandas as pd

        part = pd.read_parquet(path)
        ts_col = next((c for c in part.columns if str(c).lower() in ("timestamp", "ts")), None)
        if ts_col is None:
            return None
        ts = pd.to_datetime(part[ts_col], utc=True)
        mx = ts.max()
        if pd.isna(mx):
            return None
        return float(mx.timestamp())
    except Exception:
        return None


def main() -> int:
    if sys.version_info < (3, 8):
        got = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print("ERROR: Python >= 3.8 is required for this repo's backend modules.")
        print(f"Current interpreter: {got}")
        print("Try one of these:")
        print("  python3.10 scripts/audit_parquet_last_tag_d_nifty500.py --sample 120")
        print("  python3.11 scripts/audit_parquet_last_tag_d_nifty500.py --sample 120")
        return 2

    global _update_minimal_cycle_state, PipelineBridge, resolve_parquet_path
    from backend.breakout_logic import _update_minimal_cycle_state as _u  # noqa: WPS433
    from utils.pipeline_bridge import PipelineBridge as _pb  # noqa: WPS433
    from utils.universe_history_audit import resolve_parquet_path as _rp  # noqa: WPS433

    _update_minimal_cycle_state = _u
    PipelineBridge = _pb
    resolve_parquet_path = _rp

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--csv",
        default=os.path.join(_ROOT, "data", "nifty500.csv"),
        help="Nifty 500 CSV (Symbol column → NSE:SYM-EQ)",
    )
    ap.add_argument("--sample", type=int, default=120, help="How many symbols to audit (random sample)")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed for reproducible sample")
    ap.add_argument("--limit", type=int, default=900, help="History bars passed to cycle replay")
    ap.add_argument("--don-len", type=int, default=10, help="Donchian window (match BREAKOUT_PIVOT_HIGH_WINDOW default)")
    ap.add_argument("--data-dir", default=None, help="Override PIPELINE_DATA_DIR (else from settings)")
    args = ap.parse_args()

    if args.data_dir:
        os.environ["PIPELINE_DATA_DIR"] = str(args.data_dir)

    from config.settings import settings  # noqa: WPS433 — after optional env override

    data_dir = settings.PIPELINE_DATA_DIR
    bridge = PipelineBridge()

    symbols = _load_nifty500_symbols(args.csv)
    if not symbols:
        print("ERROR: no symbols loaded from", args.csv)
        return 2

    rng = random.Random(int(args.seed))
    want = min(int(args.sample), len(symbols))
    picked = sorted(rng.sample(symbols, want)) if want < len(symbols) else list(symbols)

    missing_file = 0
    missing_bridge = 0
    short_hist = 0
    no_tag = 0
    ts_mismatch = 0
    ok = 0

    rows_out: list[str] = []

    print("PIPELINE_DATA_DIR =", data_dir)
    print("sample_size =", want, "don_len =", int(args.don_len), "hist_limit =", int(args.limit))
    print("---")

    for sym in picked:
        path = resolve_parquet_path(sym, data_dir)
        if path is None:
            missing_file += 1
            rows_out.append(f"{sym}\tNO_PARQUET\t\t")
            continue

        hv = bridge.get_historical_data(sym, limit=int(args.limit))
        if hv is None:
            missing_bridge += 1
            rows_out.append(f"{sym}\tBRIDGE_NONE\t{path}\t")
            continue
        if len(hv) < 6:
            short_hist += 1
            rows_out.append(f"{sym}\tSHORT_HIST\t{path}\tlen={len(hv)}")
            continue

        pq_last_ts = _parquet_last_ts_unix(path)
        br_last_ts = float(hv[-1][0])
        if pq_last_ts is not None and abs(pq_last_ts - br_last_ts) > 1.5:
            # allow 1s slack for float rounding; parquet vs numpy int64[s] edge cases
            ts_mismatch += 1

        r: dict = {"symbol": sym}
        _update_minimal_cycle_state(r, hv, don_len=int(args.don_len))
        tag = str(r.get("last_tag") or "").strip() or "—"
        if tag in ("", "—"):
            no_tag += 1

        ok += 1
        last_ist = ""
        try:
            last_ist = datetime.fromtimestamp(br_last_ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
        except Exception:
            last_ist = str(br_last_ts)

        rows_out.append(
            f"{sym}\t{tag}\t{len(hv)}\t{os.path.basename(path)}\tlast_ts={last_ist}"
        )

    print(f"symbols_universe={len(symbols)} audited={len(picked)}")
    print(f"ok_with_history={ok} missing_parquet_file={missing_file} bridge_empty={missing_bridge} short_hist_flag={short_hist}")
    print(f"parquet_vs_bridge_last_ts_mismatch={ts_mismatch} (should be 0 when data_dir matches live parquet)")
    print(f"last_tag_blank={no_tag}")
    print("--- first 25 rows: SYMBOL \\t LAST_TAG_D \\t bars \\t file \\t note")
    for line in rows_out[:25]:
        print(line)

    out_path = os.path.join(_ROOT, "data", "audit_last_tag_d_sample.tsv")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("symbol\tlast_tag_d\tbars\tparquet_file\tnote\n")
            for line in rows_out:
                f.write(line + "\n")
        print("wrote", out_path)
    except Exception as e:
        print("WARN: could not write TSV:", e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
