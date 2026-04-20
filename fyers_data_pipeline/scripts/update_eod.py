import sys
import os
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

logger = setup_logging("update_eod", "eod.log")

def update_symbol_eod(conn, pq_manager, symbol):
    """Fetches and appends today's data for a symbol."""
    today = datetime.now().strftime("%Y-%m-%d")
    # For EOD, we usually just need the last 1-2 days to ensure we have the latest closed candle
    from_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    try:
        response = conn.get_history(symbol, from_date, today, resolution="1D")
        
        if response.get('s') == 'ok':
            candles = response.get('candles', [])
            if candles:
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                
                # Append logic handled by ParquetManager (includes de-duplication)
                pq_manager.save_data(symbol, df, overwrite=False)
                return True
            else:
                logger.info(f"No new data for {symbol} today.")
        else:
            logger.error(f"Error fetching EOD data for {symbol}: {response}")
            
    except Exception as e:
        logger.exception(f"Exception during EOD update for {symbol}: {e}")
    
    return False

def main():
    conn = ConnectionManager()
    if not conn.connect():
        logger.error("Failed to connect to Fyers API. Exiting.")
        return

    db = DatabaseManager()
    db.ensure_symbols_pipeline_columns()
    pq_manager = ParquetManager()
    
    with db.Session() as session:
        # Get active symbols that were previously synced
        result = session.execute(text("SELECT symbol_id FROM symbols WHERE is_active = TRUE AND last_historical_sync IS NOT NULL")).fetchall()
        symbols = [r[0] for r in result]

    logger.info(f"EOD Update: Processing {len(symbols)} symbols.")
    
    for symbol in symbols:
        success = update_symbol_eod(conn, pq_manager, symbol)
        if success:
            with db.Session() as session:
                session.execute(text("""
                    UPDATE symbols 
                    SET last_historical_sync = :now 
                    WHERE symbol_id = :sid
                """), {"now": datetime.now(), "sid": symbol})
                session.commit()
    
    logger.info("EOD Update complete.")

if __name__ == "__main__":
    main()
