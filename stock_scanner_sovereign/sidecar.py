import time, os, logging
from backend.breakout_engine import BreakoutScanner

if __name__ == "__main__":
    # The Sidecar is a SLAVE analyzer that writes signals back to SHM
    univ = os.getenv("UNIVERSE", "Nifty 500")
    print(f"🚀 [Sidecar] Initializing Pro Edition Analyzer for {univ}...")
    
    # 1. Initialize the heavy-duty scanner
    scanner = BreakoutScanner(universe=univ)
    
    # 2. Attach Pro Parameters (Signal Line, etc.)
    # Note: These values are optimized for the Weinstein Pro logic
    scanner.update_params()
    
    # 3. Start the immortal analytical loop
    try:
        scanner.start_scanning()
        print("✅ [Sidecar] Real-time Analysis Loop Active.")
        while True:
            time.sleep(10) # Keep thread alive while workers run
    except KeyboardInterrupt:
        scanner.stop_scanning()
        print("🛑 [Sidecar] Analysis Stopped.")
