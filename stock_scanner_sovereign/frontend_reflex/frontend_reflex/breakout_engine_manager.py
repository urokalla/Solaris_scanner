import os
import threading
from backend.breakout_engine import BreakoutScanner
from .engine import get_scanner

breakout_instances: dict[str, BreakoutScanner] = {}
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


def get_breakout_scanner(symbols=None, universe=None, role: str = "strategy"):
    role_key = "timing" if str(role or "").strip().lower() == "timing" else "strategy"
    with breakout_lock:
        inst = breakout_instances.get(role_key)
        if inst is None:
            get_scanner()
            u = universe if universe is not None else "Nifty 500"
            inst = BreakoutScanner(symbols=symbols, universe=u)
            breakout_instances[role_key] = inst
            # Isolation: only strategy instance runs the heavy loop in dashboard mode.
            if role_key == "strategy" and _dashboard_runs_loop():
                print("📡 [Sidecar] Initializing Breakout Engine (strategy loop in dashboard)...")
                inst.start_scanning()
            else:
                # Timing/sidecar lazy mode: isolated instance serving `get_ui_view` only.
                print(
                    "📡 [Sidecar] Initializing Breakout Engine "
                    f"({role_key} lazy mode — loop delegated to sidecar container)..."
                )
        return inst
