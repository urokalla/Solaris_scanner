import os
import threading
from backend.breakout_engine import BreakoutScanner
from .engine import get_scanner

breakout_instance = None
breakout_lock = threading.Lock()


def _dashboard_runs_loop() -> bool:
    """Whether this process should run `BreakoutScanner.main_loop_helper` (the heavy per-tick
    cycle / EMA / SHM-copy loop).

    When the dedicated `sovereign_sidecar` container has `SIDECAR_RUN_ANALYZER=1`, it already
    runs that loop and writes brk_lvl → Postgres. In that case the dashboard only needs an
    in-process `BreakoutScanner` for `get_ui_view` (on-demand cycle hydration for visible rows
    + SHM refresh). Set `DASHBOARD_BREAKOUT_LOOP=0` to skip `start_scanning()` here and free
    the dashboard's 1 CPU for Reflex / web traffic.
    """
    return os.getenv("DASHBOARD_BREAKOUT_LOOP", "1").strip().lower() not in ("0", "false", "no")


def get_breakout_scanner(symbols=None, universe=None):
    global breakout_instance
    with breakout_lock:
        if breakout_instance is None:
            get_scanner()
            u = universe if universe is not None else "Nifty 500"
            breakout_instance = BreakoutScanner(symbols=symbols, universe=u)
            if _dashboard_runs_loop():
                print("📡 [Sidecar] Initializing Breakout Engine (running main loop in dashboard)...")
                breakout_instance.start_scanning()
            else:
                # Loop is owned by the sidecar container; the dashboard's BreakoutScanner only
                # serves `get_ui_view` (lazy hydration + SHM refresh). Saves ~60% dashboard CPU.
                print(
                    "📡 [Sidecar] Initializing Breakout Engine (lazy mode — loop delegated to "
                    "sidecar container; set DASHBOARD_BREAKOUT_LOOP=1 to run it here instead)..."
                )
        return breakout_instance
