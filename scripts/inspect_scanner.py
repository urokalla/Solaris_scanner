import sys
import os
import time

# Add the project roots to sys.path
sys.path.append("/home/udai/RS_PROJECT/stock_scanner_sovereign")
sys.path.append("/home/udai/RS_PROJECT/stock_scanner_sovereign/frontend_reflex")

from frontend_reflex.engine import get_scanner

def inspect_scanner():
    print("🔍 [Inspect] Checking Scanner Singleton State...")
    sc = get_scanner()
    
    # Wait for active status AND at least one RS rating (from the background thread)
    timeout = 60
    start = time.time()
    while (time.time() - start) < timeout:
        if sc.status_message == "✅ Active" and any(r.get('rs_rating') for r in sc.scanner_results.values()):
            break
        print(f"⏳ [Inspect] Waiting for active state and ratings... Status: {sc.status_message}")
        time.sleep(5)
        
    print(f"📊 [Inspect] Final Status: {sc.status_message}")
    
    # Sync shared results manually for inspection
    with sc.lock:
        shared = dict(sc.shared_results)
        for sym, res in shared.items():
            sc.scanner_results.setdefault(sym, {}).update(res)

    results = sc.scanner_results
    print(f"📈 [Inspect] Total Results in scanner_results: {len(results)}")
    
    # Sample some symbols (excluding indices for cleaner output)
    samples = [s for s in results.keys() if "-INDEX" not in s][:10]
    for sym in samples:
        r = results[sym]
        print(f"🔹 [Inspect] {sym:20} | RS: {r.get('rs_rating', 'N/A'):3} | Profile: {r.get('profile', 'N/A'):15} | Status: {r.get('status', 'N/A')}")

    # Check indices
    print("\n📈 [Inspect] Checking Pulse (Indices):")
    for idx in ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX"]:
        r = results.get(idx, {})
        print(f"🔸 [Inspect] {idx:20} | LTP: {r.get('ltp', 0):>8} | RS: {r.get('rs_rating', 'N/A')}")

if __name__ == "__main__":
    inspect_scanner()
