import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Path to your .env file
ENV_PATH = '/home/udai/RS_PROJECT/fyers_data_pipeline/config/.env'

if not os.path.exists(ENV_PATH):
    print(f"❌ Error: Could not find .env file at {ENV_PATH}")
    exit(1)

# Load credentials
load_dotenv(ENV_PATH)
db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("❌ Error: DATABASE_URL not found in .env file.")
    exit(1)

try:
    engine = create_engine(db_url)
    
    print("\n" + "="*40)
    print("📊 FYERS DATABASE STATUS SUMMARY")
    print("="*40)

    # 1. Show Universe Summary
    print("\n--- Universe Membership ---")
    query_uni = """
    SELECT universe_id, count(*) as stock_count 
    FROM universe_members 
    GROUP BY universe_id
    UNION ALL
    SELECT 'TOTAL UNIQUE SYMBOLS', count(*) FROM symbols
    """
    df_uni = pd.read_sql(query_uni, engine)
    print(df_uni.to_string(index=False))

    # 2. Show Sync Status (Last 5 synced)
    print("\n--- Latest Hist-Data Syncs ---")
    query_sync = """
    SELECT symbol_id, last_historical_sync 
    FROM symbols 
    WHERE last_historical_sync IS NOT NULL 
    ORDER BY last_historical_sync DESC 
    LIMIT 5
    """
    df_sync = pd.read_sql(query_sync, engine)
    if df_sync.empty:
        print("No sync history found yet.")
    else:
        print(df_sync.to_string(index=False))

    # 3. Show a few symbols from Nifty 50
    print("\n--- Sample Nifty 50 Symbols ---")
    query_n50 = """
    SELECT symbols.symbol_id, description 
    FROM symbols 
    JOIN universe_members ON symbols.symbol_id = universe_members.symbol_id 
    WHERE universe_members.universe_id = 'NIFTY_50' 
    LIMIT 5
    """
    df_n50 = pd.read_sql(query_n50, engine)
    if df_n50.empty:
        print("Nifty 50 mapping not found. Run seed_symbols.py first!")
    else:
        print(df_n50.to_string(index=False))
    
    print("\n" + "="*40 + "\n")

except Exception as e:
    print(f"❌ Database Connection Error: {e}")
