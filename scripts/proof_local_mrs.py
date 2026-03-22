import os
import sys
import datetime
import pandas as pd
import numpy as np

# Setup path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../stock_scanner_sovereign"))
if root_dir not in sys.path: sys.path.append(root_dir)

from config.settings import settings
from utils.breakout_math import aggregate_weekly_np, calculate_breakout_signals

def proof_local_mrs():
    parquet_dir = settings.PIPELINE_DATA_DIR
    
    # 1. Load Local Data (Try TATAMOTORS for better momentum proof)
    stock_file = os.path.join(parquet_dir, "NSE_TATAMOTORS_EQ.parquet")
    if not os.path.exists(stock_file): stock_file = os.path.join(parquet_dir, "NSE_RELIANCE_EQ.parquet")
    bench_file = os.path.join(parquet_dir, "NSE_NIFTY50_INDEX.parquet")
    
    if not os.path.exists(stock_file) or not os.path.exists(bench_file):
        print(f"❌ Missing files: {stock_file} or {bench_file}")
        return

    s_df = pd.read_parquet(stock_file)
    b_df = pd.read_parquet(bench_file)
    
    # Normalize Columns
    s_df.columns = [c.lower() for c in s_df.columns]
    b_df.columns = [c.lower() for c in b_df.columns]
    
    # 2. Prepare Array Format [TS, O, H, L, C, V]
    def to_np(df):
        # datetime64[ms] -> int64 is milliseconds. Scale to seconds.
        ts = df['timestamp'].values.astype(np.int64) // 1000
        return np.column_stack([ts, df['open'], df['high'], df['low'], df['close'], df['volume']])

    s_arr = to_np(s_df)
    b_arr = to_np(b_df)
    
    print(f"📊 RELIANCE: {len(s_arr)} bars, NIFTY50: {len(b_arr)} bars.")
    
    # 3. Step-by-Step Manual mRS
    # Align
    s_dates = {datetime.date.fromtimestamp(r[0]): r for r in s_arr}
    b_dates = {datetime.date.fromtimestamp(r[0]): r for r in b_arr}
    common = sorted(list(set(s_dates.keys()) & set(b_dates.keys())))
    s_aligned = np.array([s_dates[d] for d in common])[-400:]
    b_aligned = np.array([b_dates[d] for d in common])[-400:]
    
    # Weekly Aggregation
    sw = aggregate_weekly_np(s_aligned)
    bw = aggregate_weekly_np(b_aligned)
    
    # Mansfield Logic
    ratio = sw[:, 4] / bw[:, 4]
    window = 52
    ma = np.mean(ratio[-window:])
    mrs = (ratio[-1] / ma - 1) * 10
    
    print("\n--- [MANUAL] STEP-BY-STEP PROOF ---")
    print(f"1. Date: {datetime.date.fromtimestamp(sw[-1, 0])}")
    print(f"2. Stock (RELIANCE) Close: {sw[-1, 4]}")
    print(f"3. Bench (NIFTY 50) Close: {bw[-1, 4]}")
    print(f"4. Current Ratio: {ratio[-1]:.6f}")
    print(f"5. 52-Week Mean Ratio: {ma:.6f}")
    print(f"6. Weinstein mRS Formula: ((Ratio/Mean) - 1) * 10")
    print(f"✅ Resulting mRS: {mrs:.2f}")

    # 4. Compare with Engine Output
    print("\n--- [ENGINE] CROSS-VERIFICATION ---")
    params = {"ema_fast": 9, "ema_slow": 21, "breakout_period": 10, "timeframe": "D"}
    res = calculate_breakout_signals("NSE:RELIANCE-EQ", s_arr, b_arr, params)
    
    print(f"👉 Engine mRS Output: {res.get('mrs')}")
    print(f"👉 Profile Assigned: {res.get('profile')}")
    
    if round(mrs, 2) == round(res.get('mrs', 0), 2):
        print("\n✅ PROOF SUCCESSFUL: Manual calculation matches Engine output 100%.")
    else:
        print(f"\n❌ PARITY ERROR: {mrs:.2f} vs {res.get('mrs')}")

if __name__ == "__main__":
    proof_local_mrs()
