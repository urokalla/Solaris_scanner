import sys
import os
import time
import pandas as pd
from datetime import datetime, timedelta
import logging
from sqlalchemy import text

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.connection_manager import ConnectionManager
from src.db_manager import DatabaseManager
from src.parquet_manager import ParquetManager
from src.utils import setup_logging

logger = setup_logging("eod_sync", "eod_sync.log")

# 7 Benchmarks to ensure are always synced
BENCHMARK_SYMBOLS = [
    "NSE:NIFTY50-INDEX",
    "NSE:NIFTY100-INDEX",
    "NSE:NIFTY500-INDEX",
    "NSE:NIFTYBANK-INDEX",
    "NSE:NIFTYMIDCAP100-INDEX",
    "NSE:NIFTYSMALLCAP100-INDEX",
    "NSE:FINNIFTY-INDEX"
]

def sync_symbol(conn, pq_manager, symbol):
    """Fetches today's 1-day candle and appends to Parquet."""
    try:
        # Fetch only today's data (1D resolution)
        # Using a 2-day range to ensure we capture the latest candle safely
        to_date = datetime.now()
        from_date = to_date - timedelta(days=2)
        
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")
        
        response = conn.get_history(symbol, from_str, to_str, resolution="1D")
        
        if response.get('s') == 'ok':
            candles = response.get('candles', [])
            if candles:
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                # Standardize timestamp to datetime for ParquetManager's append logic
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                
                # Use ParquetManager to handle the append/deduplicate logic
                pq_manager.save_data(symbol, df, overwrite=False)
                return True
        elif response.get('s') == 'no_data':
            return True # Not an error, just no data
        else:
            logger.error(f"Error syncing {symbol}: {response.get('message', 'Unknown Error')}")
            
    except Exception as e:
        logger.exception(f"Exception syncing {symbol}: {e}")
    return False

def main():
    conn = ConnectionManager()
    if not conn.connect():
        logger.error("Failed to connect to Fyers API.")
        return

    db = DatabaseManager()
    pq_manager = ParquetManager()
    
    # 1. Get all active symbols from DB
    with db.Session() as session:
        result = session.execute(text("SELECT symbol_id FROM symbols WHERE is_active = TRUE")).fetchall()
        db_symbols = [r[0] for r in result]

    # 2. Combine with Benchmarks (ensuring uniqueness)
    all_symbols = list(set(db_symbols + BENCHMARK_SYMBOLS))
    
    logger.info(f"📊 [EOD Sync] Starting synchronization for {len(all_symbols)} symbols...")
    
    success_count = 0
    for symbol in all_symbols:
        if sync_symbol(conn, pq_manager, symbol):
            success_count += 1
        # Throttling to stay within Fyers limits (approx 10 symbols/sec)
        time.sleep(0.1)
        
    logger.info(f"✅ [EOD Sync] Completed. Synced {success_count}/{len(all_symbols)} symbols.")

if __name__ == "__main__":
    main()
