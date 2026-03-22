import os, mmap, numpy as np; import sys; sys.path.append('.')
from backend.scanner_shm import SHMBridge
from utils.constants import SIGNAL_DTYPE

def audit_shm():
    try:
        shm = SHMBridge()
        shm.setup(is_master_hint=False)
        arr = shm.arr
        
        print(f"--- SHM Audit (Total: 10000 slots) ---")
        found = 0
        for i in range(len(arr)):
            r = arr[i]
            sym = r['symbol'].decode('utf-8', errors='ignore').strip('\x00').strip()
            if not sym: continue
            
            st = r['status'].decode('utf-8', errors='ignore').strip('\x00').strip()
            mrs = float(r['mrs'])
            mrs_p = float(r['mrs_prev'])
            
            # Check if condition for BUY NOW is met: mrs > 0 and mrs_p <= 0
            if mrs > 0 and mrs_p <= 0:
                print(f"🎯 COND MET: {sym} | mrs: {mrs:.4f} | mrs_prev: {mrs_p:.4f} | status: '{st}'")
                found += 1
            elif st == "BUY NOW":
                print(f"✅ STATUS EXISTS: {sym} | mrs: {mrs:.4f} | mrs_prev: {mrs_p:.4f} | status: '{st}'")
                found += 1
            elif st == "RS_CROSSOVER":
                 print(f"⚠️ LEGACY STATUS: {sym} | mrs: {mrs:.4f} | mrs_prev: {mrs_p:.4f} | status: '{st}'")
                 found += 1

        if found == 0:
            print("❌ No stocks currently meet the BUY NOW criteria or have the status set.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    audit_shm()
