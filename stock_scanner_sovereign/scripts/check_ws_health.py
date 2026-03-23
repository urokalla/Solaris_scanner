#!/usr/bin/env python3
"""
Quick scanner websocket health check from container logs.

Usage:
  python3 stock_scanner_sovereign/scripts/check_ws_health.py --since 20m
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys


TICK_RE = re.compile(
    r"TickHealth\] tokens=(?P<tokens>\d+)/(?P<total>\d+)\s+stale>\d+s=(?P<stale>\d+)\s+unresolved=(?P<unresolved>\d+)\s+last_tick_age=(?P<age>[^ ]+)"
)


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or f"Command failed: {' '.join(cmd)}")
    return (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Scanner websocket health checker")
    ap.add_argument("--since", default="20m", help="docker logs window (default: 20m)")
    ap.add_argument("--container", default="sovereign_scanner", help="scanner container name")
    args = ap.parse_args()

    out = run(["docker", "logs", args.container, "--since", args.since])
    lines = out.splitlines()

    latest_tick = None
    unresolved_warn = 0
    invalid_err = 0
    ssl_err = 0
    for ln in lines:
        m = TICK_RE.search(ln)
        if m:
            latest_tick = m.groupdict()
        if "Fyers unresolved symbols after recovery" in ln:
            unresolved_warn += 1
        if "invalid_symbols" in ln:
            invalid_err += 1
        if "UNEXPECTED_EOF_WHILE_READING" in ln:
            ssl_err += 1

    print("=== WS Health Check ===")
    print(f"container={args.container} since={args.since}")
    if latest_tick is None:
        print("status=WARN no TickHealth line found in log window")
    else:
        print(
            "latest_tickhealth "
            f"tokens={latest_tick['tokens']}/{latest_tick['total']} "
            f"stale={latest_tick['stale']} unresolved={latest_tick['unresolved']} "
            f"last_tick_age={latest_tick['age']}"
        )
    print(f"log_counts unresolved_warnings={unresolved_warn} invalid_symbol_errors={invalid_err} ssl_eof_errors={ssl_err}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)

