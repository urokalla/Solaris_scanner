import sys
import os
import pandas as pd

# Add the project root to sys.path
sys.path.append("/home/udai/RS_PROJECT/stock_scanner_sovereign")

from utils.pipeline_bridge import PipelineBridge
from config.settings import settings

def test_bridge():
    print("🧪 [Test] Starting Pipeline Bridge Verification...")
    bridge = PipelineBridge()
    
    # Test symbol that is known to exist
    test_sym = "NSE:RELIANCE-EQ"
    print(f"📡 [Test] Fetching data for {test_sym}...")
    
    df = bridge.get_historical_data(test_sym, limit=100)
    
    if df.empty:
        print(f"❌ [Test] Failed to fetch data for {test_sym}. Check if Parquet file exists in {settings.PIPELINE_DATA_DIR}")
        return
    
    print(f"✅ [Test] Successfully fetched {len(df)} rows.")
    print(f"📊 [Test] Columns: {df.columns.tolist()}")
    print(f"📅 [Test] Last 5 rows:\n{df.tail()}")
    
    # Check if 'timestamp' is in normalized format
    if 'timestamp' in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            print("✅ [Test] Timestamp column is datetime64.")
        else:
            print("❌ [Test] Timestamp column is NOT datetime64.")
    else:
        print("❌ [Test] 'timestamp' column missing.")

if __name__ == "__main__":
    test_bridge()
