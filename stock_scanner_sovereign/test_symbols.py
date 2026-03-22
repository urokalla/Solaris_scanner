import sys
sys.path.insert(0, "/home/udai/RS_PROJECT/stock_scanner_sovereign")
from utils.symbols import get_nifty_symbols

symbols = get_nifty_symbols("Nifty 500")
print(f"Index: Nifty 500 | Symbols found: {len(symbols)}")
if len(symbols) > 0:
    print(f"Sample: {symbols[:5]}")
