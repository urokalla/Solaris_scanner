import os, mmap, numpy as np; import sys; sys.path.append('.')
from backend.scanner_shm import SHMBridge

def distribution_audit():
    shm = SHMBridge()
    shm.setup(is_master_hint=False)
    arr = shm.arr
    
    pos, neg, zero = 0, 0, 0
    total = 0
    for i in range(len(arr)):
        r = arr[i]
        sym = r['symbol'].decode('utf-8', errors='ignore').strip('\x00').strip()
        if not sym: continue
        
        total += 1
        mrs = float(r['mrs'])
        if mrs > 0: pos += 1
        elif mrs < 0: neg += 1
        else: zero += 1

    print(f"--- mRS Distribution Audit (Total: {total}) ---")
    print(f"Positive (>0): {pos} ({pos/total:.1%})")
    print(f"Negative (<0): {neg} ({neg/total:.1%})")
    print(f"Exactly Zero: {zero} ({zero/total:.1%})")

if __name__ == '__main__':
    distribution_audit()
