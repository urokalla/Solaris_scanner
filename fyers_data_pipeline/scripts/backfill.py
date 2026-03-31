import sys
import os
import time
import random
import pandas as pd
from datetime import datetime, timedelta
import logging
from sqlalchemy import text
from tqdm import tqdm

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.connection_manager import ConnectionManager
from src.db_manager import DatabaseManager
from src.parquet_manager import ParquetManager
from src.utils import setup_logging, get_date_range, chunk_date_range

logger = setup_logging("backfill", "backfill.log")

# Fyers throttles hard; space out REST calls and back off when the API says slow down.
_DEFAULT_REQUEST_GAP_S = 1.25
_MAX_RATE_LIMIT_BACKOFF_S = 180.0


def _normalize_fyers_symbol(sym: str) -> str:
    """Align universe CSV with Fyers (hyphens in tickers, e.g. BAJAJ_AUTO -> BAJAJ-AUTO)."""
    s = (sym or "").strip().upper()
    if not s.startswith("NSE:"):
        return s
    body = s[4:]
    if body.endswith("-EQ") and "_" in body:
        return "NSE:" + body.replace("_", "-")
    return s


def _is_bad_symbol_history(response: dict) -> bool:
    """True when the API rejects this ticker — do not retry; move to next symbol."""
    if not isinstance(response, dict):
        return False
    if response.get("s") in ("ok", "no_data"):
        return False
    msg = str(response.get("message", "")).lower()
    needles = (
        "invalid symbol",
        "incorrect symbol",
        "symbol not",
        "not available",
        "delist",
        "no data for symbol",
        "unknown symbol",
        "wrong symbol",
    )
    return any(n in msg for n in needles)


def _is_rate_limited(response: dict) -> bool:
    """Only real throttling — not -99 / generic errors (saves monthly API quota)."""
    if not isinstance(response, dict):
        return False
    code = response.get("code")
    if code == -99:
        return False
    if code == -300:
        return True
    msg = str(response.get("message", "")).lower()
    phrases = (
        "rate limit",
        "too many requests",
        "throttle",
        "try again later",
        "quota exceeded",
        "request limit",
    )
    return any(p in msg for p in phrases)


def backfill_symbol(
    conn,
    pq_manager,
    symbol,
    years=5,
    max_retries=8,
    max_rate_limit_retries=5,
    request_gap_s: float = _DEFAULT_REQUEST_GAP_S,
):
    """Expert Incremental Logic: Fills gaps in both directions (past to reach 'years', future to catch up)."""
    raw_sym = symbol
    symbol = _normalize_fyers_symbol(symbol)
    if symbol != raw_sym.strip().upper():
        logger.info("Normalized symbol %r -> %r", raw_sym, symbol)

    existing_df = pq_manager.read_data(symbol)
    now = datetime.now()
    target_from, target_to = get_date_range(years)
    target_from_dt = datetime.strptime(target_from, "%Y-%m-%d")
    
    chunks = []
    
    if existing_df.empty:
        # 1. Full 5-Year Initial Backfill
        logger.info(f"🚀 [Sync] Deep {years}-Year Initial Backfill for {symbol}...")
        chunks = list(chunk_date_range(target_from, target_to, chunk_days=365))
    else:
        # Existing data range
        ts = pd.to_datetime(existing_df['timestamp'])
        start_date = ts.min()
        end_date = ts.max()
        
        # A) Check if we need to fill the PAST (to reach targets)
        if start_date > target_from_dt + timedelta(days=7): # 7-day buffer for holidays/weekends
             logger.info(f"🔙 [Sync] Gap in PAST for {symbol}: {target_from} -> {start_date.date()}")
             chunks.extend(list(chunk_date_range(target_from, start_date.strftime("%Y-%m-%d"), chunk_days=365)))
             
        # B) Check if we need to fill the FUTURE (to catch up to today)
        if (now - end_date).days >= 1:
             # Ensure we start 1 day before the last date to catch partials
             from_future = end_date - timedelta(days=1)
             logger.info(f"🔜 [Sync] Gap in FUTURE for {symbol}: {from_future.date()} -> {now.date()}")
             chunks.extend(list(chunk_date_range(from_future.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"), chunk_days=365)))

    if not chunks:
        return True
    
    all_data = []
    any_chunk_failed = False
    skip_entire_symbol = False
    for chunk_start, chunk_end in chunks:
        if skip_entire_symbol:
            break
        retries = 0
        chunk_success = False
        rate_limit_streak = 0
        rate_limit_hits = 0
        while retries < max_retries:
            try:
                if request_gap_s > 0:
                    time.sleep(request_gap_s)
                response = conn.get_history(symbol, chunk_start, chunk_end, resolution="1D")

                if response.get("s") == "ok":
                    candles = response.get("candles", [])
                    if candles:
                        df = pd.DataFrame(
                            candles,
                            columns=["timestamp", "open", "high", "low", "close", "volume"],
                        )
                        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
                        all_data.append(df)
                    chunk_success = True
                    break
                if response.get("s") == "no_data":
                    chunk_success = True
                    break
                if _is_bad_symbol_history(response):
                    logger.warning(
                        "⏭️ Skipping %s — not on Fyers / bad ticker (%s). Next symbol.",
                        symbol,
                        response.get("message"),
                    )
                    skip_entire_symbol = True
                    chunk_success = True
                    break
                if _is_rate_limited(response):
                    rate_limit_hits += 1
                    if rate_limit_hits > max_rate_limit_retries:
                        logger.error(
                            "Stopping %s after %d rate-limit waits (save API quota). "
                            "Raise --request-gap or run off-peak.",
                            symbol,
                            max_rate_limit_retries,
                        )
                        break
                    rate_limit_streak += 1
                    base = min(
                        _MAX_RATE_LIMIT_BACKOFF_S,
                        12.0 * (1.65 ** min(rate_limit_streak - 1, 12)),
                    )
                    wait_time = base + random.uniform(0, 1.5)
                    logger.warning(
                        "⚠️ [Limit] Rate hit for %s (attempt %d/%d, rl %d/%d). %.1fs backoff...",
                        symbol,
                        retries + 1,
                        max_retries,
                        rate_limit_hits,
                        max_rate_limit_retries,
                        wait_time,
                    )
                    time.sleep(wait_time)
                else:
                    logger.warning(
                        "Non-OK history for %s chunk %s–%s: %s",
                        symbol,
                        chunk_start,
                        chunk_end,
                        response,
                    )
                    break

                retries += 1
            except Exception as e:
                retries += 1
                logger.warning("Exception fetching %s chunk %s: %s", symbol, chunk_start, e)
                time.sleep(min(30.0, 2.0 * retries))
        if skip_entire_symbol:
            break
        if not chunk_success:
            any_chunk_failed = True
            logger.error(
                "Failed to backfill %s chunk starting %s. Continuing with other chunks...",
                symbol,
                chunk_start,
            )
            continue

    if skip_entire_symbol:
        return True

    if any_chunk_failed:
        return False

    if all_data:
        final_df = pd.concat(all_data).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
        # Use overwrite=False to merge with existing_df in ParquetManager
        pq_manager.save_data(symbol, final_df, overwrite=False)
        # Stagger after a full symbol write
        time.sleep(0.5)
        return True
    return True

from concurrent.futures import ThreadPoolExecutor

def main():
    conn = ConnectionManager()
    if not conn.connect():
        logger.error("Failed to connect to Fyers API. Ensure access_token.txt exists.")
        return

    years = int(os.environ.get("BACKFILL_YEARS", "5"))
    force_rescan = os.environ.get("BACKFILL_FORCE", "").strip().lower() in ("1", "true", "yes")
    nifty500_only = os.environ.get("BACKFILL_NIFTY500_ONLY", "").strip().lower() in ("1", "true", "yes")

    db = DatabaseManager()
    pq_manager = ParquetManager()
    
    with db.Session() as session:
        # PROFESSIONAL FILTER: Only process real Stocks (-EQ) and Indices (-INDEX)
        # This automatically skips 'mislabeled symbols' and Gold Bond/Debt noise.
        today = datetime.now().date()
        sync_filter = (
            ""
            if force_rescan
            else "AND (s.last_historical_sync IS NULL OR s.last_historical_sync < :today)"
        )
        join_sql = (
            "INNER JOIN universe_members um ON s.symbol_id = um.symbol_id AND um.universe_id = 'NIFTY_500'"
            if nifty500_only
            else "LEFT JOIN universe_members um ON s.symbol_id = um.symbol_id AND um.universe_id = 'NIFTY_500'"
        )
        query = text(f"""
            SELECT s.symbol_id 
            FROM symbols s
            {join_sql}
            WHERE s.is_active = TRUE 
            AND (s.symbol_id LIKE '%-EQ' OR s.symbol_id LIKE '%-INDEX')
            {sync_filter}
            ORDER BY 
                CASE WHEN s.symbol_id LIKE '%INDEX%' OR s.symbol_id LIKE '%IDX%' THEN 0 ELSE 1 END ASC,
                CASE WHEN um.universe_id IS NOT NULL THEN 0 ELSE 1 END ASC,
                s.last_historical_sync ASC NULLS FIRST
        """)
        params = {} if force_rescan else {"today": today}
        result = session.execute(query, params).fetchall()
        symbols = [r[0] for r in result]

    logger.info(
        "Backfill: %d symbols | years=%d | NIFTY500_only=%s | force_rescan=%s",
        len(symbols),
        years,
        nifty500_only,
        force_rescan,
    )
    
    def process_symbol(symbol):
        try:
            # One connection + Fyers limits: parallel workers multiply throttle hits; keep low.
            retry_count = 1 if ("INDEX" in symbol or "IDX" in symbol) else 8
            success = backfill_symbol(
                conn,
                pq_manager,
                symbol,
                years=years,
                max_retries=retry_count,
                max_rate_limit_retries=5,
            )
            if success:
                # Use a new session for each thread to avoid race conditions
                with db.Session() as session:
                    session.execute(text("""
                        UPDATE symbols 
                        SET last_historical_sync = :now 
                        WHERE symbol_id = :sid
                    """), {"now": datetime.now(), "sid": symbol})
                    session.commit()
            return success
        except Exception as e:
            logger.error(f"Error on {symbol}: {e}")
            return False

    # Fyers REST history is aggressively rate-limited; 5 workers routinely trips limits.
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(
            tqdm(
                executor.map(process_symbol, symbols),
                total=len(symbols),
                desc=f"{years}y Heavy Sync",
            )
        )

if __name__ == "__main__":
    main()
