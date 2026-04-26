import time
import logging
from datetime import datetime, time as dt_time, timezone, timedelta
import subprocess
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

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
        f.write(day.strip() + "\n")


def run_python_file(script_path: str) -> tuple[bool, str]:
    """Run a Python file; returns (ok, stdout) so callers can inspect markers like token_expired."""
    logger.info(f"🚀 Starting script: {script_path}")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
        stdout = result.stdout or ""
        if result.returncode == 0:
            logger.info(f"✅ Script finished successfully: {script_path}")
            if stdout:
                logger.info(stdout[-4000:])
            return True, stdout
        logger.error(f"❌ Script failed: {script_path}\nstderr: {result.stderr}\nstdout: {stdout[-2000:]}")
        return False, stdout
    except Exception as e:
        logger.exception(f"Exception running {script_path}: {e}")
        return False, ""


def run_script(rel_path: str) -> bool:
    """Backwards-compatible wrapper that returns only the ok flag."""
    ok, _ = run_python_file(os.path.join(_ROOT, rel_path))
    return ok


def run_script_verbose(rel_path: str) -> tuple[bool, str]:
    """Same as run_script but also returns stdout so callers can inspect markers."""
    return run_python_file(os.path.join(_ROOT, rel_path))


def _monthly_rsi2_snapshot_script_path() -> str | None:
    """Docker: …/app/stock_scanner_sovereign/… Host: repo sibling of fyers_data_pipeline."""
    candidates = (
        os.path.join(_ROOT, "stock_scanner_sovereign", "scripts", "populate_monthly_rsi2_snapshot.py"),
        os.path.join(os.path.dirname(_ROOT), "stock_scanner_sovereign", "scripts", "populate_monthly_rsi2_snapshot.py"),
    )
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _token_mtime_hours() -> float | None:
    """Age of the access token file in hours (None if missing)."""
    path = os.getenv("FYERS_ACCESS_TOKEN_PATH") or os.path.join(
        _ROOT, "stock_scanner_sovereign", "access_token.txt"
    )
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    return (time.time() - mtime) / 3600.0


def main_loop():
    logger.info("📡 Sovereign Pipeline Service Started")

    eod_h = int(os.getenv("EOD_SYNC_IST_HOUR", "15"))
    eod_m = int(os.getenv("EOD_SYNC_IST_MINUTE", "45"))
    eod_after = dt_time(eod_h, eod_m)

    snap_h = int(os.getenv("MONTHLY_RSI2_SNAPSHOT_IST_HOUR", "15"))
    snap_m = int(os.getenv("MONTHLY_RSI2_SNAPSHOT_IST_MINUTE", "0"))
    snap_after = dt_time(snap_h, snap_m)

    bf_h = int(os.getenv("BACKFILL_IST_HOUR", "1"))
    bf_m = int(os.getenv("BACKFILL_IST_MINUTE", "0"))

    # Manual-token mode: operator drops in a fresh access_token.txt daily. If eod_sync detects
    # the token is expired it exits 0 with an "EOD_SYNC_RESULT skipped reason=token_expired"
    # marker; we then back off for EOD_TOKEN_RETRY_MINUTES before the next attempt so logs
    # stay quiet. The moment the token file mtime changes, the next tick retries immediately.
    token_retry_min = max(1, int(os.getenv("EOD_TOKEN_RETRY_MINUTES", "60")))

    logger.info(
        f"📋 Monthly RSI2 snapshot: weekdays IST ≥ {snap_h:02d}:{snap_m:02d} "
        f"(MONTHLY_RSI2_SNAPSHOT_IST_HOUR/MINUTE; pre-close uses last closed daily bar in DB until EOD adds today)"
    )
    logger.info(
        "🔐 Token mode: MANUAL — drop a fresh token into stock_scanner_sovereign/access_token.txt daily. "
        "On expiry, EOD skips gracefully and retries every %d min (EOD_TOKEN_RETRY_MINUTES).",
        token_retry_min,
    )
    try:
        age = _token_mtime_hours()
        if age is None:
            logger.warning(
                "🔐 [Startup] access_token.txt is missing — EOD will skip until you add one."
            )
        else:
            logger.info("🔐 [Startup] access_token age %.1fh", age)
    except Exception as e:
        logger.warning("Token age check failed: %s", e)

    # Track the last failed-by-token attempt so we don't retry more than once per
    # EOD_TOKEN_RETRY_MINUTES, and so a fresh token file reset the backoff instantly.
    last_token_skip_ts: float = 0.0
    last_token_skip_mtime: float = 0.0

    # Startup catch-up: if the last EOD success is stale (>0 calendar days) and the
    # most-recent completed trading session is past, trigger EOD immediately so
    # eod_sync's gap-heal pass repairs the series without waiting for 15:45 IST.
    try:
        startup_ist = _ist_now()
        last_ok_str = _read_date_flag(".eod_last_ok_date")
        last_ok_date = datetime.strptime(last_ok_str, "%Y-%m-%d").date() if last_ok_str else None
        today_ist_date = startup_ist.date()
        # "Catch up" when the flag is older than today; eod_sync + heal pass handles
        # any interior gaps going back EOD_HEAL_DAYS.
        stale = last_ok_date is None or last_ok_date < today_ist_date
        if stale:
            logger.info(
                "🩹 [Scheduler] Startup catch-up: last EOD ok=%s, running eod_sync now "
                "(gap-heal window=EOD_HEAL_DAYS)",
                last_ok_str or "never",
            )
            ok, stdout = run_script_verbose(os.path.join("scripts", "eod_sync.py"))
            if "reason=token_expired" in stdout:
                logger.warning(
                    "🔐 Startup EOD skipped: access token expired. "
                    "Drop a fresh token into access_token.txt; scheduler will retry automatically."
                )
                last_token_skip_ts = time.time()
                try:
                    last_token_skip_mtime = os.path.getmtime(
                        os.getenv("FYERS_ACCESS_TOKEN_PATH")
                        or os.path.join(_ROOT, "stock_scanner_sovereign", "access_token.txt")
                    )
                except OSError:
                    last_token_skip_mtime = 0.0
            elif ok:
                _write_date_flag(".eod_last_ok_date", today_ist_date.isoformat())
    except Exception as e:
        logger.exception("Startup catch-up failed: %s", e)

    while True:
        try:
            now_ist = _ist_now()
            current_date = now_ist.date()
            current_time = now_ist.time()
            today_str = current_date.isoformat()

            # JOB 1: Daily EOD — append today’s 1D bar after NSE close (~15:30 IST); data usually ready by ~15:45 IST
            # Mon–Fri only; first loop after EOD_SYNC_IST_* where we haven’t succeeded today.
            # If the Fyers token is expired, eod_sync exits 0 and prints an "EOD_SYNC_RESULT
            # skipped reason=token_expired" marker. We detect that here and back off for
            # EOD_TOKEN_RETRY_MINUTES — but if access_token.txt mtime changes (operator dropped
            # a fresh token) we retry right away.
            if now_ist.weekday() < 5 and current_time >= eod_after:
                if _read_date_flag(".eod_last_ok_date") != today_str:
                    skip_due_to_backoff = False
                    if last_token_skip_ts > 0:
                        now_ts = time.time()
                        try:
                            cur_mtime = os.path.getmtime(
                                os.getenv("FYERS_ACCESS_TOKEN_PATH")
                                or os.path.join(_ROOT, "stock_scanner_sovereign", "access_token.txt")
                            )
                        except OSError:
                            cur_mtime = 0.0
                        token_refreshed = cur_mtime > last_token_skip_mtime
                        backoff_elapsed = (now_ts - last_token_skip_ts) >= token_retry_min * 60
                        if not token_refreshed and not backoff_elapsed:
                            skip_due_to_backoff = True

                    if not skip_due_to_backoff:
                        logger.info(
                            f"📥 [Scheduler] Daily EOD sync (IST ≥ {eod_h:02d}:{eod_m:02d}, append today)..."
                        )
                        ok, stdout = run_script_verbose(os.path.join("scripts", "eod_sync.py"))
                        if "reason=token_expired" in stdout:
                            logger.warning(
                                "🔐 EOD skipped: access token expired. "
                                "Drop a fresh token into access_token.txt — next tick will retry. "
                                "(Backoff: %d min if token file unchanged.)",
                                token_retry_min,
                            )
                            last_token_skip_ts = time.time()
                            try:
                                last_token_skip_mtime = os.path.getmtime(
                                    os.getenv("FYERS_ACCESS_TOKEN_PATH")
                                    or os.path.join(_ROOT, "stock_scanner_sovereign", "access_token.txt")
                                )
                            except OSError:
                                last_token_skip_mtime = 0.0
                        elif ok:
                            _write_date_flag(".eod_last_ok_date", today_str)
                            last_token_skip_ts = 0.0
                            last_token_skip_mtime = 0.0

            # JOB 1b: Monthly RSI2 snapshot (DBeaver / Excel) — own IST clock, default 15:00 pre-close; not tied to EOD
            snap_enabled = os.getenv(
                "MONTHLY_RSI2_SNAPSHOT_ENABLED",
                os.getenv("MONTHLY_RSI2_SNAPSHOT_AFTER_EOD", "1"),
            ).lower() not in ("0", "false", "no")
            if (
                snap_enabled
                and now_ist.weekday() < 5
                and current_time >= snap_after
                and _read_date_flag(".monthly_rsi2_snapshot_ok_date") != today_str
            ):
                snap_py = _monthly_rsi2_snapshot_script_path()
                if snap_py:
                    logger.info("📋 [Scheduler] monthly_rsi2_lt2_snapshot (populate_monthly_rsi2_snapshot.py)...")
                    snap_ok, _ = run_python_file(snap_py)
                    if snap_ok:
                        _write_date_flag(".monthly_rsi2_snapshot_ok_date", today_str)
                else:
                    logger.warning(
                        "Monthly RSI2 snapshot script not found "
                        "(mount stock_scanner_sovereign in pipeline or run from repo root)."
                    )

            # JOB 2: Deep backfill — narrow IST window (sleep=30s can skip a single minute)
            if current_time.hour == bf_h and bf_m <= current_time.minute < bf_m + 5:
                if _read_date_flag(".backfill_last_ok_date") != today_str:
                    logger.info(f"🚀 [Scheduler] Deep backfill ({bf_h:02d}:{bf_m:02d} IST window)...")
                    if run_script(os.path.join("scripts", "backfill.py")):
                        _write_date_flag(".backfill_last_ok_date", today_str)

            # Fyers auth: eod_sync / backfill load the token in their own subprocess (see ConnectionManager there).

            time.sleep(30)

        except KeyboardInterrupt:
            logger.info("🛑 Service stopping...")
            break
        except Exception as e:
            logger.exception(f"Unexpected error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
