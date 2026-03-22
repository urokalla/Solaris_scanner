import threading
from backend.breakout_engine import BreakoutScanner
from .engine import get_scanner

breakout_instance = None
breakout_lock = threading.Lock()

def get_breakout_scanner(symbols=None, universe=None):
    global breakout_instance
    with breakout_lock:
        if breakout_instance is None:
            print(f"📡 [Sidecar] Initializing Breakout Engine...")
            get_scanner()
            u = universe if universe is not None else "Nifty 500"
            breakout_instance = BreakoutScanner(symbols=symbols, universe=u)
            breakout_instance.start_scanning()
        return breakout_instance
