import time, numpy as np, pandas as pd
import pickle, sys

def benchmark_overhead():
    # Simulate a single stock's history (OHLCV)
    N = 1000
    data = np.random.random((N, 6)) # [ts, o, h, l, c, v]
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    # 1. Object Initialization & Pickling (Simulating IPC)
    # Pandas
    start = time.perf_counter()
    for _ in range(100):
        df = pd.DataFrame(data, columns=cols)
        _pv = pickle.dumps(df)
    pandas_ipc = (time.perf_counter() - start) / 100
    
    # Numpy
    start = time.perf_counter()
    for _ in range(100):
        # In actual Zero-Pandas, we pass the view/array directly
        _nv = pickle.dumps(data)
    numpy_ipc = (time.perf_counter() - start) / 100

    # 2. Alignment (pd.merge vs numpy mask)
    b_data = np.random.random((N, 6))
    b_df = pd.DataFrame(b_data, columns=cols)
    s_df = pd.DataFrame(data, columns=cols)

    start = time.perf_counter()
    for _ in range(100):
        _m = pd.merge(s_df, b_df[['timestamp', 'close']], on='timestamp', how='inner')
    pandas_merge = (time.perf_counter() - start) / 100

    start = time.perf_counter()
    for _ in range(100):
        # Simplified align_numpy logic
        s_ts = data[:, 0]
        b_ts = b_data[:, 0]
        mask = np.isin(s_ts, b_ts)
        _res_s = data[mask]
        _res_b = b_data[np.isin(b_ts, s_ts)]
    numpy_align = (time.perf_counter() - start) / 100

    print(f"🏢 Enterprise Benchmarks (500 Stocks Scan Simulation):")
    print(f"  IPC Handover (Pickling):")
    print(f"    Pandas: {pandas_ipc*1000:.3f}ms | Numpy: {numpy_ipc*1000:.3f}ms")
    print(f"    Savings: {((pandas_ipc-numpy_ipc)/pandas_ipc)*100:.1f}%")
    
    print(f"\n  Alignment (Joining Data):")
    print(f"    Pandas Merge: {pandas_merge*1000:.3f}ms | Numpy Mask: {numpy_align*1000:.3f}ms")
    print(f"    Speedup: {pandas_merge/numpy_align:.1f}x")

    print(f"\n💾 Memory Bloat Factor:")
    print(f"  Pandas Overhead: ~{sys.getsizeof(s_df)/1024:.1f} KB per stock")
    print(f"  Numpy Overhead:  ~{sys.getsizeof(data)/1024:.1f} KB per stock")

if __name__ == "__main__":
    benchmark_overhead()
