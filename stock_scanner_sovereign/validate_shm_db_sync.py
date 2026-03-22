#!/usr/bin/env python3
"""
Validate Layer-3 alignment: SHM mmap vs Postgres live_state (incl. brk_lvl).

Run from repo root or stock_scanner_sovereign:
  python3 stock_scanner_sovereign/validate_shm_db_sync.py

SHM files live under stock_scanner_sovereign/ (scanner_results.mmap, symbols_idx_map.json).

Postgres from your laptop/WSL:
  The compose file does NOT publish Postgres to localhost by default, so DB_HOST=localhost
  usually fails with "connection refused". Use one of:

  A) Run this script inside a container on the same network as `db`:
       docker compose exec sovereign_dashboard bash -lc \\
         'cd /app/stock_scanner_sovereign && python3 validate_shm_db_sync.py'

  B) With explicit host (resolves inside compose):
       docker compose exec -e DB_HOST=db sovereign_dashboard bash -lc \\
         'cd /app/stock_scanner_sovereign && python3 validate_shm_db_sync.py'

  C) Add under `db:` in docker-compose.yml:  ports: [ "5432:5432" ]
     then: DB_HOST=127.0.0.1 python3 validate_shm_db_sync.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from backend.scanner_shm import SHMBridge
from utils.constants import SIGNAL_DTYPE


def _decode_sym(b) -> str:
    if isinstance(b, (bytes, bytearray)):
        return b.decode("utf-8", errors="ignore").strip("\x00").strip()
    return str(b)


def _db_section(shm: SHMBridge):
    from backend.database import DatabaseManager

    db = DatabaseManager()
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM live_state")
                n_ls = cur.fetchone()[0]
                cur.execute(
                    "SELECT COUNT(*) FROM live_state WHERE brk_lvl IS NOT NULL"
                )
                n_brk = cur.fetchone()[0]
        print(f"\nPostgres live_state: total rows={n_ls}, rows with brk_lvl set={n_brk}")

        try:
            db.ensure_live_state_brk_column()
        except Exception as e:
            print(f"  ensure_live_state_brk_column: {e}")

        sample = list(shm.idx_map.items())[:15]
        print("\nSample SHM vs DB (symbol | SHM LTP | SHM mRS | DB last_price | DB brk_lvl):")
        for sym, idx in sample:
            if idx >= len(shm.arr):
                continue
            r = shm.arr[idx]
            sym_s = _decode_sym(r["symbol"]) or sym
            ltp, mrs = float(r["ltp"]), float(r["mrs"])
            lp_db = brk_db = None
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT last_price, brk_lvl FROM live_state WHERE symbol = %s",
                        (sym_s,),
                    )
                    row = cur.fetchone()
                    if row:
                        lp_db, brk_db = row[0], row[1]
            print(
                f"  {sym_s[:36]:36} | LTP {ltp:10.2f} | mRS {mrs:8.2f} | DB lp={lp_db} | brk={brk_db}"
            )
    except ConnectionError as e:
        print(f"\n--- Postgres: skipped ({e}) ---")
        print(
            "  From the host, Postgres is usually not on localhost unless you publish port 5432.\n"
            "  Inside Docker, set DB_HOST=db and run this script in sovereign_dashboard (see docstring)."
        )
    except Exception as e:
        print(f"\n--- Postgres: error ({type(e).__name__}: {e}) ---")


def main():
    shm = SHMBridge()
    shm.setup(is_master_hint=False)
    n_map = len(shm.idx_map or {})
    print(f"SHM index map symbols: {n_map}")
    if n_map == 0:
        print(
            "  WARN: empty map — sovereign_scanner should write symbols_idx_map.json (master running?)."
        )

    mmap_ok = os.path.exists(shm.shm_path)
    print(f"SHM mmap path: {shm.shm_path} (exists={mmap_ok})")
    print(f"SIGNAL_DTYPE item size (bytes): {np.dtype(SIGNAL_DTYPE).itemsize}")

    _db_section(shm)

    print("\nDone.")


if __name__ == "__main__":
    main()
