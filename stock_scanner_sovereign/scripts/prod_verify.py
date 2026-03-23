#!/usr/bin/env python3
"""
PROD-style quick verification runner.

Runs:
1) docker compose ps
2) SHM <-> DB sync validator (inside dashboard container)
3) WS health checker
4) EOD status checker

Usage:
  python3 stock_scanner_sovereign/scripts/prod_verify.py
"""

from __future__ import annotations

import subprocess
import sys


def run(cmd: str) -> int:
    print(f"\n$ {cmd}")
    p = subprocess.run(cmd, shell=True, text=True)
    return p.returncode


def main() -> int:
    cmds = [
        "docker compose ps",
        "docker compose exec -e DB_HOST=db dashboard bash -lc 'cd /app/stock_scanner_sovereign && python3 validate_shm_db_sync.py'",
        "python3 stock_scanner_sovereign/scripts/check_ws_health.py --since 20m",
        "python3 stock_scanner_sovereign/scripts/check_eod_status.py --since 24h",
    ]
    failed = 0
    for c in cmds:
        rc = run(c)
        if rc != 0:
            failed += 1
            print(f"-> FAILED ({rc})")
    print("\n=== PROD Verify Summary ===")
    if failed == 0:
        print("status=OK all checks passed")
        return 0
    print(f"status=WARN failed_checks={failed}")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)

