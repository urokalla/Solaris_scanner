#!/usr/bin/env python3
"""
Backfill Parquet from Fyers **only** for symbols with no file or empty/unreadable Parquet
(under PIPELINE_DATA_DIR). Uses chunked history from `fyers_data_pipeline/scripts/backfill.py`.

Does **not** by default refill "short_span" (has file but <5y) — use --include-short-span for that.

Examples:
  python scripts/backfill_missing_parquet.py --universe "All NSE Stocks" --dry-run
  python scripts/backfill_missing_parquet.py --universe "All NSE Stocks" --limit 50
  # Prefer **pipeline** container (has fyers_apiv3 + backfill.py on /app):
  docker compose exec -w /app/stock_scanner_sovereign pipeline \\
    python scripts/backfill_missing_parquet.py --universe "All NSE Stocks" --data-dir /app/data/historical
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import sys
import time

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Repo root: …/RS_PROJECT/stock_scanner_sovereign -> parent is RS_PROJECT (host) or /app (Docker + fyers_data_pipeline mount)
ROOT = os.path.dirname(SOV)
sys.path.insert(0, SOV)

from config.settings import settings  # noqa: E402
from utils.constants import SYMBOL_GROUPS  # noqa: E402
from utils.universe_history_audit import audit_symbol_parquet  # noqa: E402
from utils.universe_validation import expected_symbols_for_universe  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
LOG = logging.getLogger("backfill_missing")


def _pipeline_root() -> str:
    """
    Resolve directory that contains `scripts/backfill.py` + `src/connection_manager.py`.

    - **Pipeline container**: repo is mounted at `/app` (see docker-compose `pipeline` service).
    - **Scanner container**: optional mount `./fyers_data_pipeline` -> `/app/fyers_data_pipeline`.
    - **Host**: sibling dir `…/RS_PROJECT/fyers_data_pipeline`.
    """
    env = os.environ.get("FYERS_PIPELINE_ROOT")
    if env and os.path.isfile(os.path.join(env, "scripts", "backfill.py")):
        return env
    # Same layout as fyers_data_pipeline image: /app/scripts/backfill.py
    if os.path.isfile(os.path.join(ROOT, "scripts", "backfill.py")):
        return ROOT
    nested = os.path.join(ROOT, "fyers_data_pipeline")
    if os.path.isfile(os.path.join(nested, "scripts", "backfill.py")):
        return nested
    return nested


def _load_pipeline_backfill():
    pipe = _pipeline_root()
    if not os.path.isdir(pipe):
        return None, None, (
            f"fyers_data_pipeline not found at {pipe}. "
            "On Docker, mount ./fyers_data_pipeline:/app/fyers_data_pipeline or set FYERS_PIPELINE_ROOT."
        )
    path = os.path.join(pipe, "scripts", "backfill.py")
    if not os.path.isfile(path):
        return None, None, f"Missing {path}"
    if pipe not in sys.path:
        sys.path.insert(0, pipe)
    spec = importlib.util.spec_from_file_location("fyers_backfill", path)
    if spec is None or spec.loader is None:
        return None, None, "Could not load backfill.py"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, pipe, None


def _needs_backfill(
    symbol: str,
    data_dir: str,
    *,
    include_short: bool,
) -> tuple[bool, str]:
    r = audit_symbol_parquet(symbol, data_dir, min_years=5.0)
    st = r.get("status", "")
    if st in ("missing_file", "empty_or_unreadable"):
        return True, st
    if include_short and st == "short_span":
        return True, st
    return False, st


def main() -> None:
    ap = argparse.ArgumentParser(description="Fyers Parquet backfill for missing/empty symbols only.")
    ap.add_argument("--universe", required=True, help='e.g. "All NSE Stocks"')
    ap.add_argument("--data-dir", default=None, help="PIPELINE_DATA_DIR")
    ap.add_argument(
        "--include-short-span",
        action="store_true",
        help="Also backfill symbols that have a file but <5y span (large API use)",
    )
    ap.add_argument("--years", type=int, default=5, help="Years for initial backfill (Fyers chunks)")
    ap.add_argument("--dry-run", action="store_true", help="List targets only, no API calls")
    ap.add_argument("--limit", type=int, default=0, help="Max symbols to process (0 = all)")
    ap.add_argument("--sleep", type=float, default=0.5, help="Seconds after each symbol")
    ap.add_argument(
        "--request-gap",
        type=float,
        default=1.25,
        help="Seconds before each Fyers history call (reduces rate-limit bursts)",
    )
    ap.add_argument(
        "--max-retries",
        type=int,
        default=8,
        help="Max attempts per date chunk (non-bad-symbol errors)",
    )
    ap.add_argument(
        "--max-rate-limit-retries",
        type=int,
        default=5,
        help="Max rate-limit backoffs per chunk before giving up (saves API quota)",
    )
    args = ap.parse_args()

    u = args.universe.strip()
    if u not in SYMBOL_GROUPS:
        LOG.error("Unknown universe %r. Options: %s", u, ", ".join(SYMBOL_GROUPS))
        sys.exit(2)

    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)
    if not os.path.isdir(data_dir):
        LOG.error("Not a directory: %s", data_dir)
        sys.exit(2)

    syms = sorted(expected_symbols_for_universe(u))
    if not syms:
        LOG.error("No symbols for universe %r (check CSV / seed).", u)
        sys.exit(2)

    targets: list[tuple[str, str]] = []
    for s in syms:
        need, reason = _needs_backfill(s, data_dir, include_short=args.include_short_span)
        if need:
            targets.append((s, reason))

    LOG.info(
        "Universe=%s  data_dir=%s  candidates=%d  to_backfill=%d  (include_short=%s)",
        u,
        data_dir,
        len(syms),
        len(targets),
        args.include_short_span,
    )
    if args.dry_run:
        for i, (sym, reason) in enumerate(targets[:500]):
            print(f"{reason}\t{sym}")
        if len(targets) > 500:
            print(f"... and {len(targets) - 500} more")
        print(f"TOTAL_TO_BACKFILL={len(targets)}")
        sys.exit(0)

    if not targets:
        LOG.info("Nothing to backfill.")
        sys.exit(0)

    if args.limit > 0:
        targets = targets[: args.limit]
        LOG.info("Limiting to first %d symbols.", args.limit)

    mod, pipe, err = _load_pipeline_backfill()
    if err or mod is None:
        LOG.error("%s", err)
        sys.exit(3)
    try:
        from src.connection_manager import ConnectionManager  # type: ignore
        from src.parquet_manager import ParquetManager  # type: ignore
    except ImportError as e:
        LOG.error("Pipeline import failed: %s", e)
        sys.exit(3)

    backfill_symbol = getattr(mod, "backfill_symbol", None)
    if not callable(backfill_symbol):
        LOG.error("backfill_symbol not found")
        sys.exit(3)

    conn = ConnectionManager()
    if not conn.connect():
        LOG.error("Fyers connection failed (token / FYERS_CLIENT_ID).")
        sys.exit(3)

    pq_manager = ParquetManager(storage_path=data_dir)
    ok = fail = 0
    for i, (symbol, reason) in enumerate(targets, 1):
        LOG.info("[%d/%d] %s (%s)", i, len(targets), symbol, reason)
        try:
            if backfill_symbol(
                conn,
                pq_manager,
                symbol,
                years=args.years,
                max_retries=args.max_retries,
                max_rate_limit_retries=args.max_rate_limit_retries,
                request_gap_s=args.request_gap,
            ):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            LOG.exception("Failed %s: %s", symbol, e)
            fail += 1
        time.sleep(args.sleep)

    LOG.info("Done. ok=%d fail=%d", ok, fail)
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
