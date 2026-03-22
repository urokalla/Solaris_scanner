import sys
sys.path.insert(0, "/home/udai/RS_PROJECT/stock_scanner_sovereign")

from utils.pipeline_bridge import PipelineBridge

pb = PipelineBridge()
df1 = pb.get_historical_data("NSE:RELIANCE-EQ")
print("COLUMNS:")
print(df1.columns)
print("HEAD:")
print(df1.head())
print("LENGTH:", len(df1))
