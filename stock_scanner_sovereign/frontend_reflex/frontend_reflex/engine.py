import threading
import fcntl
import os
from backend.scanner import MasterScanner as StockScanner
from config.settings import settings
from utils.symbols import get_nifty_symbols

scanner_instance = None
scanner_lock = threading.Lock()
master_lock_file = None
scanner_thread = None

def get_scanner(symbols=None, universe=None):
    global scanner_instance, scanner_thread
    with scanner_lock:
        # Hard singleton guard: never spawn another MasterScanner while one thread is alive.
        # Previous stale-reset logic could spawn multiple writers because MasterScanner
        # has no stop_scanning(), causing concurrent SHM writes and symbol flicker.
        if scanner_instance is None or scanner_thread is None or not scanner_thread.is_alive():
            from backend.database import DatabaseManager
            db_count = len(DatabaseManager().get_all_active_symbols())
            print(f"📡 [Engine] Initializing Solaris (Index Size: {db_count})")
            scanner_instance = StockScanner()
            if symbols: scanner_instance.symbols = symbols
            scanner_thread = threading.Thread(target=scanner_instance.start_scanning, daemon=True)
            scanner_thread.start()
        elif symbols and hasattr(scanner_instance, "update_active_symbols"):
            scanner_instance.update_active_symbols(symbols)
    return scanner_instance
