import os
import sys
import datetime
import pandas as pd
import numpy as np
import logging

# Ensure stock_scanner_sovereign is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../stock_scanner_sovereign"))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from fyers_apiv3.fyersModel import FyersModel
from config.settings import settings
from backend.auth import FyersAuthenticator
from utils.symbols import get_nifty_symbols
from utils.constants import SYMBOL_GROUPS, BENCHMARK_MAP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForceSync")

def force_sync_today():
    auth = FyersAuthenticator()
    token = auth.get_access_token()
    if not token:
        logger.error("❌ No access token found.")
        return

    fyers = FyersModel(client_id=settings.FYERS_CLIENT_ID, token=token, log_path="logs", is_async=False)
    
    # Target all universes AND all benchmarks
    universes = list(SYMBOL_GROUPS.keys())
    all_symbols = []
    for u in universes:
        all_symbols.extend(get_nifty_symbols(u))
        
    # Add all unique benchmarks from the mapping
    all_symbols.extend(list(BENCHMARK_MAP.values()))
    
    all_symbols = list(set(all_symbols)) # Unique
    
    parquet_dir = settings.PIPELINE_DATA_DIR
    today_dt = pd.Timestamp.now().normalize()
    
    logger.info(f"🚀 Starting Force Sync for {len(all_symbols)} symbols to {parquet_dir}")
    
    success_count = 0
    for sym in all_symbols:
        clean_sym = sym.replace(":", "_").replace("-", "_")
        file_path = os.path.join(parquet_dir, f"{clean_sym}.parquet")
        
        # Fallback to dash version if underscore doesn't exist but dash does
        if not os.path.exists(file_path):
             dash_path = os.path.join(parquet_dir, f"{sym.replace(':', '_')}.parquet")
             if os.path.exists(dash_path):
                 file_path = dash_path
        
        if not os.path.exists(file_path):
            continue

        try:
            # Fetch today's data from Fyers
            data = {
                "symbol": sym,
                "resolution": "D",
                "date_format": "1",
                "range_from": today_dt.strftime("%Y-%m-%d"),
                "range_to": today_dt.strftime("%Y-%m-%d"),
                "cont_flag": "1"
            }
            
            response = fyers.history(data=data)
            if response and response.get("s") == "ok" and response.get("candles"):
                candle = response["candles"][0] # [TS, O, H, L, C, V]
                
                # Convert to DataFrame row
                today_row = pd.DataFrame([{
                    "timestamp": pd.to_datetime(candle[0], unit='s').normalize(),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                }])
                
                # Load existing history
                hist_df = pd.read_parquet(file_path)
                hist_df.columns = [c.lower() for c in hist_df.columns]
                if 'timestamp' in hist_df.columns:
                    hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp']).dt.tz_localize(None).dt.normalize()
                
                # Remove today if exists
                hist_df = hist_df[hist_df['timestamp'] != today_dt]
                
                # Append and Save
                final_df = pd.concat([hist_df, today_row], ignore_index=True).sort_values('timestamp')
                final_df.tail(2000).to_parquet(file_path)
                success_count += 1
                if success_count % 50 == 0:
                    logger.info(f"✅ Progress: {success_count} symbols synced...")
            
        except Exception as e:
            logger.error(f"⚠️ Error syncing {sym}: {e}")

    logger.info(f"🏁 Force Sync Complete. {success_count} files updated.")

if __name__ == "__main__":
    force_sync_today()
