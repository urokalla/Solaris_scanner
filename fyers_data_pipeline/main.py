import time
import logging
from datetime import datetime, time as dt_time, timezone, timedelta
import subprocess
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.connection_manager import ConnectionManager
from src.utils import setup_logging

logger = setup_logging("pipeline_service", "pipeline.log")

_ROOT = os.path.dirname(os.path.abspath(__file__))


def _ist_now():
    now_utc = datetime.now(timezone.utc)
    return now_utc + timedelta(hours=5, minutes=30)


def _state_dir():
    """Persist scheduler checkpoints next to Parquet data (survives container restarts)."""
    d = os.getenv("PIPELINE_DATA_DIR", os.path.join(_ROOT, "data", "historical"))
    os.makedirs(d, exist_ok=True)
    return d


def _read_date_flag(name: str) -> str | None:
    p = os.path.join(_state_dir(), name)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


def _write_date_flag(name: str, day: str) -> None:
    p = os.path.join(_state_dir(), name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(day)


def run_script(rel_path: str):
    """Runs a python script under this repo (absolute path)."""
    script_path = os.path.join(_ROOT, rel_path)
    logger.info(f"🚀 Starting script: {script_path}")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            logger.info(f"✅ Script finished successfully: {script_path}")
            if result.stdout:
                logger.info(result.stdout[-4000:])
            return True
        logger.error(f"❌ Script failed: {script_path}\nstderr: {result.stderr}\nstdout: {result.stdout[-2000:]}")
        return False
    except Exception as e:
        logger.exception(f"Exception running {script_path}: {e}")
        return False


def main_loop():
    logger.info("📡 Sovereign Pipeline Service Started")
    conn = ConnectionManager()

    eod_h = int(os.getenv("EOD_SYNC_IST_HOUR", "15"))
    eod_m = int(os.getenv("EOD_SYNC_IST_MINUTE", "45"))
    eod_after = dt_time(eod_h, eod_m)

    bf_h = int(os.getenv("BACKFILL_IST_HOUR", "1"))
    bf_m = int(os.getenv("BACKFILL_IST_MINUTE", "0"))

    while True:
        try:
            now_ist = _ist_now()
            current_date = now_ist.date()
            current_time = now_ist.time()
            today_str = current_date.isoformat()

            # JOB 1: Daily EOD — append today’s 1D bar after NSE close (~15:30 IST); data usually ready by ~15:45 IST
            # Mon–Fri only; first loop after EOD_SYNC_IST_* where we haven’t succeeded today.
            if now_ist.weekday() < 5 and current_time >= eod_after:
                if _read_date_flag(".eod_last_ok_date") != today_str:
                    logger.info(
                        f"📥 [Scheduler] Daily EOD sync (IST ≥ {eod_h:02d}:{eod_m:02d}, append today)..."
                    )
                    if run_script(os.path.join("scripts", "eod_sync.py")):
                        _write_date_flag(".eod_last_ok_date", today_str)

            # JOB 2: Deep backfill — narrow IST window (sleep=30s can skip a single minute)
            if current_time.hour == bf_h and bf_m <= current_time.minute < bf_m + 5:
                if _read_date_flag(".backfill_last_ok_date") != today_str:
                    logger.info(f"🚀 [Scheduler] Deep backfill ({bf_h:02d}:{bf_m:02d} IST window)...")
                    if run_script(os.path.join("scripts", "backfill.py")):
                        _write_date_flag(".backfill_last_ok_date", today_str)

            if not conn.connect():
                logger.error("🔑 Fyers Token Expired or Missing. Pipeline will retry in 1 minute.")

            time.sleep(30)

        except KeyboardInterrupt:
            logger.info("🛑 Service stopping...")
            break
        except Exception as e:
            logger.exception(f"Unexpected error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
