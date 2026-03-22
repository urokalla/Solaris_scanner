import os, sys, time, pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor

# Add project and package root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../stock_scanner_sovereign")))

from stock_scanner_sovereign.utils.pipeline_bridge import PipelineBridge
from stock_scanner_sovereign.utils.scanner_analysis import calculate_signals as calc_signals_pandas
# We will define calc_signals_numpy here or import it after we rename things
# For now, we capture current "Pandas" baseline

def validate_parity_deep(symbols):
    bridge = PipelineBridge()
    bench_sym = "NSE:NIFTY50-INDEX"
    bench_df = bridge.get_historical_data(bench_sym)
    params = {"ma_length": 50, "sig_length": 30, "universe": "Nifty 500"}
    
    results = []
    print(f"🔬 starting Deep Parity Audit for {len(symbols)} symbols...")
    
    for s in symbols:
        df = bridge.get_historical_data(s)
        if df.empty or bench_df.empty: continue
        
        # 1. Capture Pandas Result
        res_pd = calc_signals_pandas(s, df.copy(), bench_df.copy(), params)
        
        # 2. Capture Numpy Result (The new code)
        res_np = calc_signals_pandas(s, df.values, bench_df.values, params)
        
        if not res_pd or not res_np:
            print(f"  ⚠️ {s}: Missing results in one engine.")
            continue
            
        # 3. Field-by-Field Comparison
        mismatches = []
        for key in ["rs_rating", "mrs", "ltp", "status"]:
            v_pd, v_np = res_pd.get(key), res_np.get(key)
            
            if isinstance(v_pd, (int, float)):
                if not np.isclose(v_pd, v_np, atol=1e-5):
                    mismatches.append(f"{key}: {v_pd} != {v_np}")
            elif v_pd != v_np:
                mismatches.append(f"{key}: {v_pd} != {v_np}")
                
        if mismatches:
            print(f"  ❌ {s} FAILED: " + ", ".join(mismatches))
        else:
            print(f"  ✅ {s} PASSED (Precision: 1e-5)")

if __name__ == "__main__":
    test_universe = [
        "NSE:RELIANCE-EQ",  # Large Cap
        "NSE:TCS-EQ",       # Tech
        "NSE:NIFTYBANK-INDEX", # Index fallback
        "NSE:ZOMATO-EQ"     # New stock (less history)
    ]
    validate_parity_deep(test_universe)
