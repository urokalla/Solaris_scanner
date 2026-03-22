import sys
sys.path.insert(0, "/home/udai/RS_PROJECT/stock_scanner_sovereign")
from frontend_reflex.frontend_reflex.engine import get_scanner

sc = get_scanner()
print(f"Universe: {sc.universe}")
print(f"Symbols in sc.symbols: {len(sc.symbols)}")
print(f"Items in sc.scanner_results: {len(sc.scanner_results)}")
print(f"Items in sc.buffers: {len(sc.buffers)}")
