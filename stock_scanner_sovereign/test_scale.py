import os, time, numpy as np
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager

def mock_worker(symbol, data, shared):
    # Simulate signal math
    res = np.mean(data) * 1.5
    shared[symbol] = {"ltp": res, "status": "BUY"}

if __name__ == "__main__":
    count = 2500
    data = np.random.rand(1250, 6)
    manager = Manager()
    shared = manager.dict()
    
    print(f"🚀 Scaling Test: Sending {count} tasks to ProcessPool...")
    start = time.time()
    # On many linux systems, max_workers=os.cpu_count() is best
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        futures = [pool.submit(mock_worker, f"SYM_{i}", data, shared) for i in range(count)]
        for f in futures: f.result()
    
    end = time.time()
    print(f"✅ Executed 2500 math tasks in {end-start:.2f}s")
    
    print(f"🔄 Syncing to main dict...")
    sync_start = time.time()
    # 30-Year Architect Optimized Sync
    updates = dict(shared)
    sync_end = time.time()
    print(f"✅ Sync of 2500 items completed in {sync_end-sync_start:.4f}s")
