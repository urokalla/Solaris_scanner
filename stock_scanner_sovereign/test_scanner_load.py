import sys, time
sys.path.insert(0, "/home/udai/RS_PROJECT/stock_scanner_sovereign")
from frontend_reflex.frontend_reflex.engine import get_scanner

sc = get_scanner()
print(f"📡 Waiting for scanner to load {len(sc.symbols)} symbols...")
for _ in range(30):
    if len(sc.buffers) > 0:
        print(f"✅ Partially loaded: {len(sc.buffers)} buffers")
    if len(sc.buffers) >= len(sc.symbols):
        break
    time.sleep(1)

print(f"Final Buffers: {len(sc.buffers)}")
if len(sc.buffers) < len(sc.symbols):
    # Print some that failed
    all_s = set(sc.symbols)
    loaded_s = set(sc.buffers.keys())
    missing = list(all_s - loaded_s)
    print(f"❌ Missing {len(missing)} symbols in buffers!")
    print(f"Sample missing: {missing[:10]}")
    
    # Test one missing
    if missing:
        from utils.pipeline_bridge import PipelineBridge
        pb = PipelineBridge()
        df = pb.get_historical_data(missing[0])
        print(f"Manual check for {missing[0]}: df len = {len(df)}")
