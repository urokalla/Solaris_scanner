#!/usr/bin/env python3
"""
Copy current live_state.mrs → mrs_prev_day and rs_rating → rs_prev_day (same as master EOD).

Normally the master runs this once after ~15:30 IST. Use this script to backfill or refresh
when the scanner was down at close.

Warning: if you run this mid-session, "Prev" / RT Δ are vs this snapshot moment, not true
prior exchange close — re-run after EOD if you need canonical EOD baselines.

  cd stock_scanner_sovereign && python3 scripts/run_eod_live_state_snapshot.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("eod_snapshot")

from backend.database import DatabaseManager  # noqa: E402


def main() -> int:
    db = DatabaseManager()
    db.snapshot_mrs_prev_day_from_current_mrs()
    db.snapshot_rs_prev_day_from_current_rs()
    logger.info("EOD live_state snapshot done (mrs_prev_day + rs_prev_day).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
