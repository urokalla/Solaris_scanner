import time, numpy as np, pandas as pd
import sys

def fast_ema_np(data, span):
    alpha = 2 / (span + 1)
    output = np.zeros_like(data)
    output[0] = data[0]
    for i in range(1, len(data)):
        output[i] = (data[i] * alpha) + (output[i-1] * (1 - alpha))
    return output

def benchmark():
    N = 1000 # Typical history length
    data = np.random.random(N)
    df = pd.DataFrame({'close': data})
    
    # 1. Pandas Benchmark
    start = time.perf_counter()
    for _ in range(100):
        res = df['close'].ewm(span=50, adjust=False).mean()
    pandas_time = (time.perf_counter() - start) / 100
    
    # 2. Numpy Benchmark
    start = time.perf_counter()
    for _ in range(100):
        res = fast_ema_np(data, 50)
    numpy_time = (time.perf_counter() - start) / 100
    
    print(f"📊 Micro-Benchmark (N={N}):")
    print(f"  Pandas EMA: {pandas_time*1000:.4f} ms")
    print(f"  Numpy EMA:  {numpy_time*1000:.4f} ms")
    print(f"  Speedup:    {pandas_time/numpy_time:.1f}x")
    
    # 3. Memory Estimate
    df_size = sys.getsizeof(df) + df.memory_usage(deep=True).sum()
    np_size = data.nbytes
    print(f"💾 Memory Footprint:")
    print(f"  Pandas DataFrame: {df_size / 1024:.1f} KB")
    print(f"  Numpy Array:     {np_size / 1024:.1f} KB")
    print(f"  Memory Savings:  {(1 - np_size/df_size)*100:.1f}%")

if __name__ == "__main__":
    benchmark()
