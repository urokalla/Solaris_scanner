import os, sys, time, pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor

# Add project and package root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../stock_scanner_sovereign")))

from stock_scanner_sovereign.utils.pipeline_bridge import PipelineBridge
from stock_scanner_sovereign.utils.scanner_analysis import calculate_signals
from stock_scanner_sovereign.utils.rs_rating import compute_rs_ratings

def validate_parity(symbols=None):
    print("🧪 [Parity Test] Starting Mathematical Regression Audit...")
    bridge = PipelineBridge()
    if not symbols:
        symbols = ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX"]

    # 1. Capture "Baseline" Results (Old Logic)
    baseline_signals = {}
    print(f"📡 Loading baseline data for {len(symbols)} symbols...")
    
    bench_sym = "NSE:NIFTY50-INDEX"
    bench_df = bridge.get_historical_data(bench_sym)
    
    for s in symbols:
        df = bridge.get_historical_data(s)
        if not df.empty and not bench_df.empty:
            res = calculate_signals(s, df, bench_df, {"ma_length": 50, "sig_length": 30})
            if res:
                baseline_signals[s] = res

    print(f"✅ Baseline captured for {len(baseline_signals)} symbols.")
    
    # Returning baseline for now to confirm script works
    # This script will be expanded as we implement optimizations
    return baseline_signals

if __name__ == "__main__":
    res = validate_parity()
    for s, data in res.items():
        print(f"📊 {s}: LTP={data['ltp']}, RS={data['rs_rating']}, status={data['status']}")
