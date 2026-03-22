import sys
import pandas as pd

f = "/home/udai/RS_PROJECT/fyers_data_pipeline/data/historical/NSE_RELIANCE_EQ.parquet"
df = pd.read_parquet(f)
print("Raw Parquet Length:", len(df))
