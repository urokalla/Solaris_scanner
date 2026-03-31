#!/bin/sh
# Run inside Docker: NSE → nse_corporate_announcements.csv on a fixed interval (default 1 hour).
# Override: EVENTS_FETCH_INTERVAL_SEC=180 (3 min), 3600 (1 hour), etc.

INTERVAL="${EVENTS_FETCH_INTERVAL_SEC:-3600}"
DAYS="${EVENTS_FETCH_DAYS:-7}"
cd /app/stock_scanner_sovereign || exit 1

echo "events snapshot loop: every ${INTERVAL}s, --days ${DAYS}"

while true; do
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "${ts} fetch_nse_corporate_announcements.py start"
  python3 scripts/fetch_nse_corporate_announcements.py --days "${DAYS}" || echo "${ts} fetch exit $? (continuing)"
  sleep "${INTERVAL}"
done
