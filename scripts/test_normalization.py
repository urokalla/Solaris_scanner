import sys
import os
import pandas as pd

# Add the project roots to sys.path
sys.path.append("/home/udai/RS_PROJECT/stock_scanner_sovereign")

from utils.rs_rating import _load_s, compute_rs_ratings

def test_normalization():
    print("🧪 [Test] Running Symbol Normalization Test...")
    
    # 1. Test _load_s
    syms = _load_s("Nifty 50")
    print(f"✅ _load_s(Nifty 50) returned {len(syms)} symbols.")
    if "NSE:RELIANCE-EQ" in syms:
        print("✅ NSE:RELIANCE-EQ found in Nifty 50")
    else:
        print("❌ NSE:RELIANCE-EQ NOT found in Nifty 50")
        
    # 2. Mock data for compute_rs_ratings
    # Create 50 days of data for RELIANCE and NIFTY50
    dates = pd.date_range(end=pd.Timestamp.now(), periods=255)
    mock_df = pd.DataFrame({
        'timestamp': dates,
        'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 100.0, 'volume': 1000
    })
    
    # Benchmark slightly outperforming
    benchmark_df = pd.DataFrame({
        'timestamp': dates,
        'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 110.0, 'volume': 1000
    })
    
    p_data = {
        "NSE:RELIANCE-EQ": mock_df,
        "NSE:NIFTY50-INDEX": benchmark_df
    }
    
    print("📊 [Test] Running compute_rs_ratings with mock data...")
    # Passing the exact symbols return by _load_s
    results = compute_rs_ratings("Nifty 50", p_data=p_data)
    
    print(f"📈 [Test] Results: {results}")
    
    if "NSE:RELIANCE-EQ" in results:
        print(f"✅ RELIANCE full symbol results found: {results['NSE:RELIANCE-EQ']}")
    else:
        print("❌ RELIANCE NOT found in results (Normalization failed)")

if __name__ == "__main__":
    test_normalization()
