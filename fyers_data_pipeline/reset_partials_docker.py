import pandas as pd
import os
from sqlalchemy import text
from src.db_manager import DatabaseManager

def reset_partials():
    nifty500_path = '/app/stock_scanner_sovereign/data/nifty500.csv'
    hist_dir = '/app/data/historical'
    
    if not os.path.exists(nifty500_path):
        print(f"Error: {nifty500_path} not found in container.")
        return
        
    symbols_df = pd.read_csv(nifty500_path)
    symbols = symbols_df['Symbol'].tolist()
    target_date = pd.Timestamp.now() - pd.Timedelta(days=5*365 + 10)
    
    to_reset = []
    for s in symbols:
        p = os.path.join(hist_dir, f"NSE_{s}_EQ.parquet")
        if os.path.exists(p):
            df = pd.read_parquet(p)
            min_ts = pd.to_datetime(df.timestamp.min())
            if min_ts > target_date:
                to_reset.append(f"NSE:{s}-EQ")
    
    if not to_reset:
        print("No partial symbols found to reset.")
        return

    print(f"Found {len(to_reset)} symbols to reset.")
    db = DatabaseManager()
    
    with db.Session() as session:
        query = text("UPDATE symbols SET last_historical_sync = NULL WHERE symbol_id = ANY(:sids)")
        result = session.execute(query, {"sids": to_reset})
        session.commit()
        print(f"Successfully reset {result.rowcount} symbols in DB.")

if __name__ == "__main__":
    reset_partials()
