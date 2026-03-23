#!/usr/bin/env python3
"""
Check latest EOD scheduler/script result from pipeline logs.

Usage:
  python3 stock_scanner_sovereign/scripts/check_eod_status.py --since 24h
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys


EOD_RE = re.compile(
    r"EOD_SYNC_RESULT ok=(?P<ok>\d+)/(?P<total>\d+)\s+appended=(?P<appended>\d+)\s+rejected=(?P<rejected>\d+)\s+fail=(?P<fail>\d+)"
)


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or f"Command failed: {' '.join(cmd)}")
    return (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")


def main() -> int:
    ap = argparse.ArgumentParser(description="EOD sync status checker")
    ap.add_argument("--since", default="24h", help="docker logs window (default: 24h)")
    ap.add_argument("--container", default="fyers_pipeline", help="pipeline container name")
    args = ap.parse_args()

    out = run(["docker", "logs", args.container, "--since", args.since])
    lines = out.splitlines()

    started = [ln for ln in lines if "Starting script: /app/scripts/eod_sync.py" in ln]
    finished_ok = [ln for ln in lines if "Script finished successfully: /app/scripts/eod_sync.py" in ln]
    finished_fail = [ln for ln in lines if "Script failed" in ln and "eod_sync.py" in ln]

    latest = None
    for ln in lines:
        m = EOD_RE.search(ln)
        if m:
            latest = m.groupdict()

    print("=== EOD Status Check ===")
    print(f"container={args.container} since={args.since}")
    print(f"runs started={len(started)} finished_ok={len(finished_ok)} finished_fail={len(finished_fail)}")
    if latest:
        print(
            "latest_eod_result "
            f"ok={latest['ok']}/{latest['total']} appended={latest['appended']} "
            f"rejected={latest['rejected']} fail={latest['fail']}"
        )
    else:
        print("status=WARN no EOD_SYNC_RESULT found in log window")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)

