import threading
import fcntl
import os
from backend.scanner import MasterScanner as StockScanner
from config.settings import settings
from utils.symbols import get_nifty_symbols

scanner_instance = None
scanner_lock = threading.Lock()
master_lock_file = None

def get_scanner(symbols=None, universe=None):
    global scanner_instance
    with scanner_lock:
        from backend.database import DatabaseManager
        db_count = len(DatabaseManager().get_all_active_symbols())
        is_stale = False
        if scanner_instance is not None:
            if not hasattr(scanner_instance, 'sym_to_idx'): is_stale = True
            else:
                curr_count = len(getattr(scanner_instance, 'sym_to_idx', {}))
                if curr_count > 0 and abs(curr_count - db_count) > 200:
                    print(f"⚠️ [Engine] Stale: {curr_count} vs {db_count}. Resetting...")
                    is_stale = True
        if is_stale:
            try: scanner_instance.stop_scanning()
            except: pass
            scanner_instance = None

        if scanner_instance is None:
            print(f"📡 [Engine] Initializing Solaris (Index Size: {db_count})")
            scanner_instance = StockScanner()
            if symbols: scanner_instance.symbols = symbols
            threading.Thread(target=scanner_instance.start_scanning, daemon=True).start()
        elif symbols:
            scanner_instance.update_active_symbols(symbols)
    return scanner_instance
