import sys
import os
sys.path.insert(0, "/home/udai/RS_PROJECT/stock_scanner_sovereign")

from utils.pipeline_bridge import PipelineBridge

pb = PipelineBridge()
df1 = pb.get_historical_data("NSE:RELIANCE-EQ")
print("Response RELIANCE:", len(df1))

df2 = pb.get_historical_data("NSE:AARTIIND-EQ")
print("Response AARTIIND:", len(df2))
