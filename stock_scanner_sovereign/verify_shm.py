import numpy as np
import os
import zlib

SIGNAL_DTYPE = [
    ('symbol', 'S20'), ('ltp', 'f8'), ('profile', 'S20'), ('rs_rating', 'i4'),
    ('mrs', 'f8'), ('mrs_up', 'i1'), ('mrs_daily', 'f8'), ('mrs_daily_up', 'i1'),
    ('mrs_1m', 'f8'), ('mrs_3m', 'f8'), ('mrs_6m', 'f8'), ('mrs_1y', 'f8'),
    ('ema_ok', 'i1'), ('ema_cross_ok', 'i1'), ('rv', 'f8'), ('rv_val', 'f8'),
    ('rv_up', 'i1'), ('rv_down', 'i1'), ('p1d', 'S10'), ('p1w', 'S10'),
    ('p1m', 'S10'), ('p3m', 'S10'), ('status', 'S25'), ('change_pct', 'f8'), ('h52w', 'f8')
]

shm_path = "scanner_results.mmap"
if not os.path.exists(shm_path):
    print(f"❌ {shm_path} missing!")
    exit(1)

arr = np.memmap(shm_path, dtype=SIGNAL_DTYPE, mode='r', shape=(10000,))
active = arr[np.char.strip(arr['symbol']) != b'']

print(f"📊 Found {len(active)} active symbols in SHM.")
for row in active[:10]:
    print(f"  - {row['symbol'].decode()}: LTP={row['ltp']:.2f}, RS={row['rs_rating']}, status={row['status'].decode()}")
