import pandas as pd
import sys
import numpy as np
sys.path.insert(0, "/home/udai/RS_PROJECT/stock_scanner_sovereign")

from backend.scanner import StockScanner
from utils.pipeline_bridge import PipelineBridge
from utils.scanner_analysis import align_numpy

pb = PipelineBridge()
df1 = pb.get_historical_data("NSE:RELIANCE-EQ")
df2 = pb.get_historical_data("NSE:NIFTY50-INDEX")

# Use exact same logic as scanner.py
def to_epoch(df):
    return (pd.to_datetime(df['timestamp']).dt.tz_localize(None) - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')

df1['timestamp'] = to_epoch(df1)
df2['timestamp'] = to_epoch(df2)

cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
s_arr = df1[cols].values.astype(np.float64)
b_arr = df2[cols].values.astype(np.float64)

s_sync, b_sync = align_numpy(s_arr, b_arr)

print("S_ARR TS HEAD:", s_arr[:5, 0])
print("B_ARR TS HEAD:", b_arr[:5, 0])
print("S_SYNC LEN:", len(s_sync))
print("B_SYNC LEN:", len(b_sync))
