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

def run_script(script_path):
    """Runs a python script and logs output."""
    logger.info(f"🚀 Starting script: {script_path}")
    try:
        # Use the same python interpreter as the service
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ Script finished successfully: {script_path}")
            return True
        else:
            logger.error(f"❌ Script failed: {script_path}\nError: {result.stderr}")
            return False
    except Exception as e:
        logger.exception(f"Exception running {script_path}: {e}")
        return False

def is_market_closed():
    """Simple check to see if it's past market hours (e.g., after 4:00 PM IST)."""
    # Note: Containers are often UTC, so we should be careful. 
    # For now, we'll assume the service handles the scheduling loop.
    now = datetime.now().time()
    market_close = dt_time(16, 0) # 4:00 PM
    return now > market_close

def main_loop():
    logger.info("📡 Sovereign Pipeline Service Started")
    conn = ConnectionManager()
    
    # 30-YEAR ENGINEER FIX: Track job execution to avoid multiple runs in the same minute
    last_eod_run = None
    last_backfill_run = None
    
    while True:
        try:
            # 1. IST Timezone Logic (UTC + 5:30)
            now_utc = datetime.now(timezone.utc)
            now_ist = now_utc + timedelta(hours=5, minutes=30)
            current_date = now_ist.date()
            current_time = now_ist.time()
            
            # 2. JOB 1: Daily EOD Sync (3:45 PM IST)
            # Fyers EOD candles are usually ready 10-15 mins after market close.
            if current_time.hour == 15 and current_time.minute == 45:
                if last_eod_run != current_date:
                    logger.info("📥 [Scheduler] Triggering Daily EOD Sync (3:45 PM IST)...")
                    run_script("scripts/eod_sync.py")
                    last_eod_run = current_date
            
            # 3. JOB 2: Deep Backfill (1:00 AM IST)
            # Ensuring 5-year data integrity once per day during low-load hours.
            if current_time.hour == 1 and current_time.minute == 0:
                if last_backfill_run != current_date:
                    logger.info("🚀 [Scheduler] Triggering Deep Backfill (1:00 AM IST)...")
                    run_script("scripts/backfill.py")
                    last_backfill_run = current_date
            
            # 4. Maintenance / Token Check
            if not conn.connect():
                logger.error("🔑 Fyers Token Expired or Missing. Pipeline will retry in 1 minute.")
            
            # Sleep 30s to prevent CPU hogging while waiting for the next minute
            time.sleep(30)
            
        except KeyboardInterrupt:
            logger.info("🛑 Service stopping...")
            break
        except Exception as e:
            logger.exception(f"Unexpected error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
