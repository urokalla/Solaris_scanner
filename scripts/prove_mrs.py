import os
import sys
import datetime
import pandas as pd
import numpy as np
import logging
from fyers_apiv3.fyersModel import FyersModel

# Setup path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../stock_scanner_sovereign"))
if root_dir not in sys.path: sys.path.append(root_dir)

from config.settings import settings
from backend.auth import FyersAuthenticator
from utils.breakout_math import aggregate_weekly_np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Proof")

def prove_benchmark_and_mrs():
    auth = FyersAuthenticator()
    token = auth.get_access_token()
    fyers = FyersModel(client_id=settings.FYERS_CLIENT_ID, token=token, log_path="logs", is_async=False)
    
    # 1. Verify Benchmark Data from Fyers
    benchmarks = ["NSE:NIFTY50-INDEX", "NSE:NIFTY500-INDEX"]
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    print("\n--- [Step 1] Verifying Benchmark Values from Fyers API ---")
    bench_data = {}
    for b in benchmarks:
        res = fyers.history({"symbol": b, "resolution": "D", "date_format": "1", "range_from": today, "cont_flag": "1"})
        if res and res.get("s") == "ok" and res.get("candles"):
            last_price = res["candles"][-1][4]
            print(f"✅ {b} -> LTP: {last_price}")
            bench_data[b] = res["candles"]
        else:
            print(f"❌ Failed to get {b}: {res}")

    # 2. Prove mRS Calculation (Single Stock: RELIANCE vs NIFTY50)
    print("\n--- [Step 2] Proving mRS Calculation (RELIANCE vs Nifty 50) ---")
    stock = "NSE:RELIANCE-EQ"
    benchmark = "NSE:NIFTY50-INDEX"
    
    # Get 1 year of history for both
    start_date = (datetime.datetime.now() - datetime.timedelta(days=450)).strftime("%Y-%m-%d")
    
    def get_hist(sym):
        r = fyers.history({"symbol": sym, "resolution": "D", "date_format": "1", "range_from": start_date, "cont_flag": "1"})
        return np.array(r["candles"]) if r.get("s") == "ok" else None

    s_data = get_hist(stock)
    b_data = get_hist(benchmark)
    
    if s_data is None or b_data is None:
        print("❌ Could not fetch historical data for proof.")
        return

    # Align Data
    s_dates = {datetime.fromtimestamp(r[0]).date(): r for r in s_data}
    b_dates = {datetime.fromtimestamp(r[0]).date(): r for r in b_data}
    common = sorted(list(set(s_dates.keys()) & set(b_dates.keys())))
    s_aligned = np.array([s_dates[d] for d in common])
    b_aligned = np.array([b_dates[d] for d in common])
    
    print(f"📊 Aligned Data Length: {len(common)} days")
    
    # Aggregate to Weekly
    sw = aggregate_weekly_np(s_aligned)
    bw = aggregate_weekly_np(b_aligned)
    print(f"🗓️ Weekly Bars: {len(sw)}")
    
    # Calculate Ratio
    ratio = sw[:, 4] / bw[:, 4]
    
    # Mansfield RS (52-week MA)
    window = 52
    if len(ratio) >= window:
        ma = np.mean(ratio[-window:])
        mrs = (ratio[-1] / ma - 1) * 10
        
        print("\n--- MANSFIELD CALCULATION BREAKDOWN ---")
        print(f"1. Last Stock Price (Weekly): {sw[-1][4]}")
        print(f"2. Last Benchmark Price (Weekly): {bw[-1][4]}")
        print(f"3. Current Ratio (Stock / Bench): {ratio[-1]:.6f}")
        print(f"4. 52-Week MA of Ratio: {ma:.6f}")
        print(f"5. Formula: (({ratio[-1]:.6f} / {ma:.6f}) - 1) * 10")
        print(f"👉 mRS Result: {mrs:.2f}")
        
        if mrs > 0:
            print("🚀 STATUS: Stronger than Benchmark (Stage 2 Potential)")
        else:
            print("📉 STATUS: Weaker than Benchmark (Stage 1 or 4)")

if __name__ == "__main__":
    prove_benchmark_and_mrs()
