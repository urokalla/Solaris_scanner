import sys
import os
import time
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

def backfill_symbol(conn, pq_manager, symbol, years=5, max_retries=10):
    """Expert Incremental Logic: Fills gaps in both directions (past to reach 'years', future to catch up)."""
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
    for chunk_start, chunk_end in chunks:
        retries = 0
        chunk_success = False
        while retries < max_retries:
            try:
                response = conn.get_history(symbol, chunk_start, chunk_end, resolution="1D")
                
                if response.get('s') == 'ok':
                    candles = response.get('candles', [])
                    if candles:
                        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                        all_data.append(df)
                    chunk_success = True
                    break 
                elif response.get('s') == 'no_data':
                    chunk_success = True
                    break
                elif response.get('code') == -300 or "limit" in str(response.get('message', '')).lower(): 
                    wait_time = 15 # Production safety for rate limit recovery
                    logger.warning(f"⚠️ [Limit] Rate hit for {symbol}. {wait_time}s safeguard...")
                    time.sleep(wait_time)
                else:
                    break 
                    
                retries += 1
            except:
                retries += 1
                time.sleep(2)
        if not chunk_success:
            logger.error(f"Failed to backfill {symbol} chunk starting {chunk_start}. Continuing with other chunks...")
            continue

    if all_data:
        final_df = pd.concat(all_data).drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        # Use overwrite=False to merge with existing_df in ParquetManager
        pq_manager.save_data(symbol, final_df, overwrite=False)
        # 0.5-second stagger for rate limit mitigation
        time.sleep(0.5)
        return True
    return True # Success if we processed chunks, even if no new data was found

from concurrent.futures import ThreadPoolExecutor

def main():
    conn = ConnectionManager()
    if not conn.connect():
        logger.error("Failed to connect to Fyers API. Ensure access_token.txt exists.")
        return

    db = DatabaseManager()
    pq_manager = ParquetManager()
    
    with db.Session() as session:
        # PROFESSIONAL FILTER: Only process real Stocks (-EQ) and Indices (-INDEX)
        # This automatically skips 'mislabeled symbols' and Gold Bond/Debt noise.
        today = datetime.now().date()
        query = text("""
            SELECT s.symbol_id 
            FROM symbols s
            LEFT JOIN universe_members um ON s.symbol_id = um.symbol_id AND um.universe_id = 'NIFTY_500'
            WHERE s.is_active = TRUE 
            AND (s.symbol_id LIKE '%-EQ' OR s.symbol_id LIKE '%-INDEX')
            AND (s.last_historical_sync IS NULL OR s.last_historical_sync < :today)
            ORDER BY 
                CASE WHEN s.symbol_id LIKE '%INDEX%' OR s.symbol_id LIKE '%IDX%' THEN 0 ELSE 1 END ASC,
                CASE WHEN um.universe_id IS NOT NULL THEN 0 ELSE 1 END ASC,
                s.last_historical_sync ASC NULLS FIRST
        """)
        result = session.execute(query, {"today": today}).fetchall()
        symbols = [r[0] for r in result]

    logger.info(f"Backfill: Processing {len(symbols)} symbols in parallel.")
    
    def process_symbol(symbol):
        try:
            # We want to be stubborn for stocks but fast for indices
            retry_count = 1 if ("INDEX" in symbol or "IDX" in symbol) else 10
            success = backfill_symbol(conn, pq_manager, symbol, years=5, max_retries=retry_count)
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

    # High-Performance Parallel Mode (Match original 2-min speed)
    with ThreadPoolExecutor(max_workers=5) as executor:
        list(tqdm(executor.map(process_symbol, symbols), total=len(symbols), desc="5-Year Heavy Sync"))

if __name__ == "__main__":
    main()
