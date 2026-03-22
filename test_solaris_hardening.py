import sys, time, numpy as np
sys.path.insert(0, "/home/udai/RS_PROJECT/stock_scanner_sovereign")
from backend.scanner import StockScanner
from backend.breakout_engine import BreakoutScanner

print("🚀 Starting Solaris End-to-End Verification...")

# 1. Init Scanners
# We use is_master=True for the test to ensure SHM is initialized
master = StockScanner(is_master=True)
breakout = BreakoutScanner()

# 2. Test Callback Registry
master.add_callback(breakout.on_message)
print(f"✅ Callback Registry hooked. Count: {len(master.callbacks)}")

# 3. Test Deterministic Indexing
# Using a symbol that definitely exists in the synced master
sym = "NSE:SBIN-EQ"
idx = master.get_idx(sym)
b_idx = breakout.sym_to_idx.get(sym)

if idx is None:
    print(f"❌ Symbol {sym} not found in index. Symbols in index: {len(master.sym_to_idx)}")
    # Try another one
    sym = list(master.sym_to_idx.keys())[0] if master.sym_to_idx else None
    if not sym: raise Exception("No symbols in index!")
    idx = master.get_idx(sym)
    b_idx = breakout.sym_to_idx.get(sym)

print(f"✅ Symbol for test: {sym}")
print(f"✅ Master Index: {idx}")
print(f"✅ Breakout Index: {b_idx}")
assert idx == b_idx, "Indexing Collision detected!"

# 4. Test Live Data Flow & Heartbeat
mock_tick = {'symbol': sym, 'lp': 750.55, 'v': 5000}
master.on_message(mock_tick)

# Check Master SHM
# Structured array element access
row = master.arr[idx]
ltp = float(row['ltp'])
heartbeat = float(row['heartbeat'])

print(f"✅ SHM Updated: LTP={ltp}, Heartbeat={heartbeat}")
assert ltp == 750.55, f"SHM LTP update failed! Got {ltp}"
assert heartbeat > 0, "Master Heartbeat failed!"

# Check Breakout Pending
with breakout.lock:
    is_pending = sym in breakout.pending_tasks
print(f"✅ Breakout Task Pending: {is_pending}")
assert is_pending, "Sidecar callback chain broken!"

print("\n⭐⭐⭐ SOLARIS SOVEREIGN HARDENING VERIFIED ⭐⭐⭐")
