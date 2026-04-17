#!/bin/sh
# Run inside Docker:
#   1) NSE → nse_corporate_announcements.csv on EVENTS_FETCH_INTERVAL_SEC (default 1 hour).
#   2) Screener → screener_eps_snapshot.csv once per IST calendar day after a quiet window
#      (default 20:30 IST) — same container, no extra service.
#
# Override: EVENTS_FETCH_INTERVAL_SEC=180 (3 min), 3600 (1 hour), etc.
# Disable EPS: SCREENER_EPS_FETCH_ENABLED=0

INTERVAL="${EVENTS_FETCH_INTERVAL_SEC:-3600}"
DAYS="${EVENTS_FETCH_DAYS:-7}"
cd /app/stock_scanner_sovereign || exit 1

UNIV="${SCREENER_EPS_UNIVERSE_CSV:-data/nifty_total_market.csv}"
EPS_SLEEP="${SCREENER_EPS_SLEEP_SEC:-0.2}"

echo "events snapshot loop: every ${INTERVAL}s, --days ${DAYS}"
echo "screener EPS (same container): enabled=${SCREENER_EPS_FETCH_ENABLED:-1} IST=${SCREENER_EPS_IST_HOUR:-20}:${SCREENER_EPS_IST_MINUTE:-30} universe=${UNIV}"

while true; do
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "${ts} fetch_nse_corporate_announcements.py start"
  python3 scripts/fetch_nse_corporate_announcements.py --days "${DAYS}" || echo "${ts} fetch exit $? (continuing)"

  case "${NSE_ANNOUNCE_SUMMARY_ENABLED:-0}" in
    0|false|FALSE|no|NO) ;;
    *)
      MAXN="${NSE_ANNOUNCE_SUMMARY_MAX_NEW:-50}"
      SSLP="${NSE_ANNOUNCE_SUMMARY_SLEEP_SEC:-0.35}"
      echo "${ts} nse_announcement_summarize.py start (max-new=${MAXN})"
      python3 scripts/nse_announcement_summarize.py --max-new "${MAXN}" --sleep-sec "${SSLP}" || echo "${ts} summarize exit $? (continuing)"
      ;;
  esac

  # Once per IST day after quiet time (fixed IST offset, no tzdata required).
  case "${SCREENER_EPS_FETCH_ENABLED:-1}" in
    0|false|FALSE|no|NO) ;;
    *)
      if python3 - <<'PY'
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST)
h = int(os.environ.get("SCREENER_EPS_IST_HOUR", "20"))
m = int(os.environ.get("SCREENER_EPS_IST_MINUTE", "30"))
today = now.strftime("%Y-%m-%d")
marker = Path("/app/stock_scanner_sovereign/data/.screener_eps_last_run_ist")
if marker.exists():
    try:
        if marker.read_text(encoding="utf-8", errors="ignore").strip() == today:
            raise SystemExit(1)
    except OSError:
        pass
if now.hour > h or (now.hour == h and now.minute >= m):
    raise SystemExit(0)
raise SystemExit(1)
PY
      then
        ts2=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        echo "${ts2} fetch_screener_eps_snapshot.py start (IST daily)"
        if python3 scripts/fetch_screener_eps_snapshot.py --universe-csv "${UNIV}" --sleep-sec "${EPS_SLEEP}"; then
          python3 - <<'PY'
from datetime import datetime, timedelta, timezone
from pathlib import Path
IST = timezone(timedelta(hours=5, minutes=30))
Path("/app/stock_scanner_sovereign/data/.screener_eps_last_run_ist").write_text(
    datetime.now(IST).strftime("%Y-%m-%d"), encoding="utf-8"
)
PY
          echo "${ts2} screener EPS snapshot OK"
        else
          echo "${ts2} screener EPS snapshot failed exit $? (retry next loop)"
        fi
      fi
      ;;
  esac

  sleep "${INTERVAL}"
done
