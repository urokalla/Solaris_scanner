import mmap
import numpy as np
import os
import sys

# Add path to utils
sys.path.append('/home/udai/RS_PROJECT/stock_scanner_sovereign')

from utils.constants import SIGNAL_DTYPE, BENCHMARK_MAP

SHM_PATH = "/home/udai/RS_PROJECT/stock_scanner_sovereign/scanner_results.mmap"

def debug_shm():
    if not os.path.exists(SHM_PATH):
        print(f"❌ SHM file not found: {SHM_PATH}")
        return

    with open(SHM_PATH, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        # Assuming max symbols is 5000 as per scanner code
        num_symbols = 5000 
        arr = np.frombuffer(mm, dtype=SIGNAL_DTYPE, count=num_symbols)
        
        print("\n--- SHM BENCHMARK STATUS ---")
        for name, sym in BENCHMARK_MAP.items():
            found = False
            for r in arr:
                r_sym = r['symbol'].decode().strip('\x00')
                if r_sym == sym:
                    print(f"📍 {name} ({sym}): LTP={r['ltp']:.2f}, Change={r['change_pct']:.2f}%, Heartbeat={r['heartbeat']}")
                    found = True
                    break
            if not found:
                print(f"❌ {name} ({sym}) NOT FOUND in SHM index!")

if __name__ == "__main__":
    debug_shm()
