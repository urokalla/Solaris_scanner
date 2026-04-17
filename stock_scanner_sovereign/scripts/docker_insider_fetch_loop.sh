#!/bin/sh
# Run inside Docker: refresh Insider CSV snapshots every 3 minutes by default.
# Override interval with INSIDER_FETCH_INTERVAL_SEC.

INTERVAL="${INSIDER_FETCH_INTERVAL_SEC:-180}"
cd /app/stock_scanner_sovereign || exit 1

echo "insider snapshot loop: every ${INTERVAL}s"

while true; do
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "${ts} fetch_nse_insider_snapshots.py start"
  python3 scripts/fetch_nse_insider_snapshots.py || echo "${ts} fetch exit $? (continuing)"
  sleep "${INTERVAL}"
done

