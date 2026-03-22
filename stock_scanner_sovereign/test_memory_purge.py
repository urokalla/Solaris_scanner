import pandas as pd
import numpy as np
import time
import os
import resource
import sys

def get_mem():
    # Get memory usage in MB
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

def test_memory_savings():
    count = 2500
    rows = 1250
    print(f"📡 Simulating {count} symbols with {rows} rows each...")
    
    base_mem = get_mem()
    print(f"💾 Base Memory: {base_mem:.2f} MB")
    
    # 1. Create DataFrames (The memory hog)
    print("🔴 Creating 2500 DataFrames...")
    dfs = {f"SYM_{i}": pd.DataFrame(np.random.rand(rows, 6), columns=['open','high','low','close','volume','oi']) for i in range(count)}
    mem_with_dfs = get_mem()
    print(f"💾 Memory with DataFrames: {mem_with_dfs:.2f} MB (Delta: {mem_with_dfs - base_mem:.2f} MB)")
    
    # 2. Convert to Numpy RingBuffers (simulated)
    print("🟢 Converting to Raw Numpy Buffers...")
    buffers = {s: df.values for s, df in dfs.items()}
    
    # 3. PURGE DataFrames
    print("🧹 Purging DataFrames...")
    del dfs
    import gc
    gc.collect()
    
    mem_after_purge = get_mem()
    print(f"💾 Memory after Purge: {mem_after_purge:.2f} MB (Delta from Base: {mem_after_purge - base_mem:.2f} MB)")
    print(f"🏆 SAVINGS: {mem_with_dfs - mem_after_purge:.2f} MB")

if __name__ == "__main__":
    test_memory_savings()
