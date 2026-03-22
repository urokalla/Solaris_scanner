import time
import os
import sys
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from stock_scanner_sovereign.utils.symbols import get_nifty_symbols
from stock_scanner_sovereign.utils.pipeline_bridge import PipelineBridge
from stock_scanner_sovereign.utils.scanner_analysis import calculate_signals

# Mock constants if needed or import
try:
    from stock_scanner_sovereign.utils.constants import BENCHMARK_MAP
    from stock_scanner_sovereign.utils.rs_rating import compute_rs_ratings
except ImportError:
    BENCHMARK_MAP = {}
    compute_rs_ratings = lambda x: {}

from concurrent.futures import ThreadPoolExecutor

def benchmark():
    print("🚀 Starting Full Universe Performance Benchmark...")
    
    # 1. Symbol Discovery
    start = time.time()
    symbols = get_nifty_symbols("All NSE Stocks")
    discovery_time = time.time() - start
    print(f"✅ Symbol Discovery (All NSE): {len(symbols)} symbols in {discovery_time:.4f}s")
    
    # Pre-seed RS Rating Cache (Institutional Pattern)
    print("⏳ Pre-seeding RS Rating Cache...")
    start_rs = time.time()
    compute_rs_ratings("All NSE Stocks")
    print(f"✅ RS Ratings Cached in {time.time() - start_rs:.2f}s")
    
    bridge = PipelineBridge()
    if not symbols:
        print("❌ No symbols found.")
        return

    # 2. Parallel Data Loading
    print(f"⏳ Loading data for {len(symbols)} symbols (Parallel)...")
    start = time.time()
    with ThreadPoolExecutor(24) as executor:
        loaded = list(executor.map(lambda s: (s, bridge.get_historical_data(s)), symbols))
    
    data = {s: df for s, df in loaded if not df.empty}
    load_time = time.time() - start
    print(f"✅ Data Loading: {len(data)} files in {load_time:.4f}s ({load_time/len(symbols):.4f}s/file avg)")

    # 3. Vectorized Signal Calculation
    if data:
        bench_sym = "NSE:NIFTY50-INDEX"
        bench_df = bridge.get_historical_data(bench_sym)
        if bench_df.empty:
            bench_sym, bench_df = next(iter(data.items()))

        print(f"⏳ Calculating signals for {len(data)} symbols...")
        start = time.time()
        # Vectorized calculation is already fast, but we can parallelize the loop for even more speed if needed
        # However, calculate_signals itself is vectorized so the overhead is small. 
        # For 2400+ symbols, a loop might take 1-2s.
        results = [calculate_signals(s, df, bench_df, {"ma_length": 50, "sig_length": 30}) for s, df in data.items()]
        calc_time = time.time() - start
        print(f"✅ Signal Calculation: {len([r for r in results if r])} results in {calc_time:.4f}s ({calc_time/len(data)*1000:.4f}ms/sym)")

    print("\n📊 Final Performance Summary:")
    print(f"Total Time: {discovery_time + load_time + calc_time:.2f}s for {len(data)} stocks")

if __name__ == "__main__":
    benchmark()
