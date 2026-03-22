import sys
sys.path.insert(0, "/home/udai/RS_PROJECT/stock_scanner_sovereign")
from utils.symbols import get_nifty_symbols
from utils.pipeline_bridge import PipelineBridge

pb = PipelineBridge()
symbols = get_nifty_symbols("Nifty 500")
existing = [s for s in symbols if pb.exists(s)]

print(f"Total symbols in Nifty 500 CSV: {len(symbols)}")
print(f"Total symbols found in storage: {len(existing)}")

missing = [s for s in symbols if s not in existing]
if missing:
    print(f"First 10 missing: {missing[:10]}")
