import os, mmap, numpy as np; import sys; sys.path.append('.')
from backend.scanner_shm import SHMBridge

def final_audit():
    try:
        shm = SHMBridge()
        shm.setup(is_master_hint=False)
        arr = shm.arr
        
        print(f"--- Final Signal Audit ---")
        stats = {}
        total_symbols = 0
        
        for i in range(len(arr)):
            r = arr[i]
            sym = r['symbol'].decode('utf-8', errors='ignore').strip('\x00').strip()
            if not sym: continue
            
            total_symbols += 1
            st = r['status'].decode('utf-8', errors='ignore').strip('\x00').strip()
            stats[st] = stats.get(st, 0) + 1
            
            if st in ["BUY NOW", "BREAKOUT"]:
                print(f"🔥 SIGNAL: {sym} | status: {st} | mrs: {r['mrs']:.4f}")

        print(f"\nSummary (Total Symbols: {total_symbols}):")
        for st, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            print(f" - {st}: {count} ({count/total_symbols:.1%})")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    final_audit()
