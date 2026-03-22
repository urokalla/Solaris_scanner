#!/usr/bin/env python3
"""
One-universe audit: CSV vs Postgres membership, then Parquet history (~5y) under PIPELINE_DATA_DIR.

Optional: backfill short/missing symbols via Fyers using `fyers_data_pipeline/scripts/backfill.py` logic
(same chunked fetch + ParquetManager). Requires valid `access_token.txt` / FYERS_* env.

Examples (from repo root, DB env set):
  python stock_scanner_sovereign/scripts/universe_full_audit.py --universe "Nifty 50"
  python stock_scanner_sovereign/scripts/universe_full_audit.py --universe "Nifty 50" --backfill
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SOV)
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.constants import SYMBOL_GROUPS  # noqa: E402
from utils.universe_history_audit import MIN_YEARS_DEFAULT, audit_universe_parquet  # noqa: E402
from utils.universe_validation import (  # noqa: E402
    canonical_csv_path_for_universe,
    expected_symbols_for_universe,
    validate_universe_members_vs_canonical_csv,
)


def _load_fyers_backfill_module():
    pipe = os.path.join(ROOT, "fyers_data_pipeline")
    path = os.path.join(pipe, "scripts", "backfill.py")
    if not os.path.isfile(path):
        return None, f"Missing {path}"
    if pipe not in sys.path:
        sys.path.insert(0, pipe)
    spec = importlib.util.spec_from_file_location("fyers_backfill", path)
    if spec is None or spec.loader is None:
        return None, "Could not load backfill spec"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, None


def main() -> None:
    p = argparse.ArgumentParser(description="Universe membership + Parquet history audit (optional Fyers backfill).")
    p.add_argument("--universe", required=True, help='Display name, e.g. "Nifty 50"')
    p.add_argument("--data-dir", default=None, help="Override PIPELINE_DATA_DIR (default: from settings / env)")
    p.add_argument("--min-years", type=float, default=MIN_YEARS_DEFAULT, help="Minimum calendar years of daily history")
    p.add_argument("--membership-only", action="store_true", help="Skip Parquet checks")
    p.add_argument("--backfill", action="store_true", help="Run Fyers 5y backfill for symbols missing/short history")
    p.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = p.parse_args()

    u = args.universe.strip()
    if u not in SYMBOL_GROUPS:
        names = ", ".join(sorted(SYMBOL_GROUPS.keys()))
        print(f"Unknown universe {u!r}. Choose one of: {names}", file=sys.stderr)
        sys.exit(2)

    data_dir = args.data_dir or settings.PIPELINE_DATA_DIR
    out: dict = {"universe": u, "data_dir": data_dir}

    mem = validate_universe_members_vs_canonical_csv(universe_names=[u])[u]
    out["membership"] = mem
    csv_path = canonical_csv_path_for_universe(u)
    out["canonical_csv"] = csv_path

    if not mem.get("ok"):
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print("MEMBERSHIP MISMATCH (fix DB + seed or re-run seed_universes)")
            print(json.dumps(mem, indent=2))
        sys.exit(1)

    if args.membership_only:
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"OK membership for {u}: {mem['csv_count']} symbols match DB.")
        sys.exit(0)

    symbols = sorted(expected_symbols_for_universe(u))
    hist = audit_universe_parquet(symbols, data_dir=data_dir, min_years=args.min_years)
    out["history"] = hist

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print(f"Universe: {u}")
        print(f"Canonical file: {csv_path}")
        print(f"Parquet dir: {data_dir}")
        print(f"Membership: OK ({mem['csv_count']} symbols)")
        print(f"History OK: {hist['ok_count']}/{hist['symbols_checked']}  (fail: {hist['fail_count']})")
        if hist["failed_symbols"]:
            print("Symbols missing file or short history:")
            for s in hist["failed_symbols"]:
                row = next(x for x in hist["per_symbol"] if x["symbol"] == s)
                print(f"  - {s}: {row['status']} span_days={row.get('span_days')} rows={row.get('rows')}")

    if args.backfill:
        if hist["fail_count"] == 0:
            if not args.json:
                print("Nothing to backfill.")
            sys.exit(0)
        mod, err = _load_fyers_backfill_module()
        if err or mod is None:
            print(f"Backfill unavailable: {err}", file=sys.stderr)
            sys.exit(3)
        try:
            from src.connection_manager import ConnectionManager  # type: ignore
            from src.parquet_manager import ParquetManager  # type: ignore
        except ImportError as e:
            print(f"Could not import pipeline: {e}", file=sys.stderr)
            sys.exit(3)

        conn = ConnectionManager()
        if not conn.connect():
            print("Fyers connection failed (token / credentials).", file=sys.stderr)
            sys.exit(3)

        pq_manager = ParquetManager(storage_path=data_dir)
        backfill_symbol = getattr(mod, "backfill_symbol", None)
        if backfill_symbol is None:
            print("backfill_symbol not found in pipeline.", file=sys.stderr)
            sys.exit(3)

        if not args.json:
            print(f"Backfilling {len(hist['failed_symbols'])} symbols (5y chunked)...")
        for sym in hist["failed_symbols"]:
            try:
                backfill_symbol(conn, pq_manager, sym, years=int(args.min_years) + 1, max_retries=10)
            except Exception as ex:
                print(f"  FAIL {sym}: {ex}", file=sys.stderr)
        if not args.json:
            print("Backfill pass complete. Re-run without --backfill to verify.")
        sys.exit(0)

    sys.exit(0 if hist["fail_count"] == 0 else 1)


if __name__ == "__main__":
    main()
