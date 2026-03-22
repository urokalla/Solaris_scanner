import sys
sys.path.insert(0, "/home/udai/RS_PROJECT/stock_scanner_sovereign")

from utils.pipeline_bridge import PipelineBridge

pb = PipelineBridge()
df1 = pb.get_historical_data("NSE:NIFTY50-INDEX")
print("Response NIFTY50:", len(df1))

df2 = pb.get_historical_data("NSE:NIFTYBANK-INDEX")
print("Response NIFTYBANK:", len(df2))
