import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    FYERS_CLIENT_ID = os.getenv("FYERS_CLIENT_ID")
    FYERS_SECRET_KEY = os.getenv("FYERS_SECRET_KEY")
    FYERS_USERNAME = os.getenv("FYERS_USERNAME")
    FYERS_PIN = os.getenv("FYERS_PIN")
    FYERS_TOTP_KEY = os.getenv("FYERS_TOTP_KEY")
    FYERS_REDIRECT_URL = os.getenv("FYERS_REDIRECT_URL", "https://trade.fyers.in/api-login/redirect-uri/index.html")
    # Prioritize container path, then fallback to host-local path
    FYERS_ACCESS_TOKEN_PATH = os.getenv(
        "FYERS_ACCESS_TOKEN_PATH", 
        "/app/stock_scanner_sovereign/access_token.txt" if os.path.exists("/app") else "/home/udai/RS_PROJECT/stock_scanner_sovereign/access_token.txt"
    )

    PIPELINE_DATA_DIR = os.getenv(
        "PIPELINE_DATA_DIR",
        "/app/fyers_data_pipeline/data/historical" if os.path.exists("/app") else "/home/udai/RS_PROJECT/fyers_data_pipeline/data/historical"
    )
    
    # Scanner Settings
    RECONNECT_ATTEMPTS = 5
    SCAN_INTERVAL = 10 # Seconds
    DATA_SOURCE = os.getenv("DATA_SOURCE", "PIPELINE") # Options: PIPELINE, FYERS, YFINANCE

    # Breakout / MRS signal windows (see docs/quant_rs_accuracy.md)
    BREAKOUT_MRS_SIGNAL_PERIOD = int(os.getenv("BREAKOUT_MRS_SIGNAL_PERIOD", "30"))
    BREAKOUT_PIVOT_HIGH_WINDOW = int(os.getenv("BREAKOUT_PIVOT_HIGH_WINDOW", "20"))
    BREAKOUT_MIN_INTRADAY_BARS = int(os.getenv("BREAKOUT_MIN_INTRADAY_BARS", "100"))

settings = Settings()
