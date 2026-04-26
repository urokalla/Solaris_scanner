import os
import time

if __name__ == "__main__":
    # Full analyzer: BRK / EMA30 / breakout loop (heavy). Main RS grid does not need this — it uses
    # MasterScanner SHM + DB merges. Set SIDECAR_RUN_ANALYZER=0 (see docker-compose) to keep the
    # container alive with ~zero CPU. BRK column then stays stale or "—" unless you compute it elsewhere.
    if os.getenv("SIDECAR_RUN_ANALYZER", "1").strip().lower() in ("0", "false", "no"):
        print(
            "💤 [Sidecar] SIDECAR_RUN_ANALYZER=0 — heavy loop disabled (no BRK/EMA30/breakout writes). "
            "Main dashboard: master scanner only."
        )
        while True:
            time.sleep(3600)
        raise SystemExit(0)

    from backend.breakout_engine import BreakoutScanner

    univ = os.getenv("UNIVERSE", "Nifty 500")
    print(f"🚀 [Sidecar] Initializing Pro Edition Analyzer for {univ}...")

    scanner = BreakoutScanner(universe=univ)
    scanner.update_params()

    try:
        scanner.start_scanning()
        print("✅ [Sidecar] Real-time Analysis Loop Active.")
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        scanner.stop_scanning()
        print("🛑 [Sidecar] Analysis Stopped.")
