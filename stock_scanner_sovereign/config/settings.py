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

    # Sidecar CPU: main breakout loop sleeps this long between full universe passes (default 0.5s was heavy on laptops).
    SIDECAR_LOOP_SLEEP_SEC = float(os.getenv("SIDECAR_LOOP_SLEEP_SEC", "0.5"))
    # Parallel symbol history fetch on sidecar startup (was hard-coded 20).
    SIDECAR_SYNC_WORKERS = max(1, min(32, int(os.getenv("SIDECAR_SYNC_WORKERS", "8"))))

    # Pine-style daily strategy (sidecar): EMA9/21 + Donchian + ATR trail (see utils/pine_udai_long.py)
    SIDECAR_UDAI_PINE = os.getenv("SIDECAR_UDAI_PINE", "").strip().lower() in ("1", "true", "yes")
    UDAI_EMA_FAST = int(os.getenv("UDAI_EMA_FAST", "9"))
    UDAI_EMA_SLOW = int(os.getenv("UDAI_EMA_SLOW", "21"))
    UDAI_BREAKOUT_PERIOD = int(os.getenv("UDAI_BREAKOUT_PERIOD", "20"))
    UDAI_ATR_PERIOD = int(os.getenv("UDAI_ATR_PERIOD", "9"))
    UDAI_ATR_MULT = float(os.getenv("UDAI_ATR_MULT", "3"))
    UDAI_RISK_PCT = float(os.getenv("UDAI_RISK_PCT", "1.0"))
    UDAI_ACCOUNT_EQUITY = float(os.getenv("UDAI_ACCOUNT_EQUITY", "1000000"))
    UDAI_REFRESH_SEC = float(os.getenv("UDAI_REFRESH_SEC", "60"))

    # Main Reflex dashboard: how often to pull get_ui_view (higher = lower CPU, slower UI refresh).
    DASHBOARD_POLL_INTERVAL_SEC = float(os.getenv("DASHBOARD_POLL_INTERVAL_SEC", "2.5"))

    # Main dashboard: weekly Wilder RSI(2) on Friday-week closes (IST); Parquet + optional LTP blend.
    DASHBOARD_W_RSI2 = os.getenv("DASHBOARD_W_RSI2", "1").strip().lower() in ("1", "true", "yes")
    DASHBOARD_W_RSI2_REFRESH_SEC = float(os.getenv("DASHBOARD_W_RSI2_REFRESH_SEC", "180"))
    DASHBOARD_W_RSI2_LIVE_IST_HOUR = int(os.getenv("DASHBOARD_W_RSI2_LIVE_IST_HOUR", "14"))
    DASHBOARD_W_RSI2_LIVE_IST_MINUTE = int(os.getenv("DASHBOARD_W_RSI2_LIVE_IST_MINUTE", "45"))

    # Monthly Wilder RSI(2) on month-end closes: sidecar column blends live LTP into “today” from this IST time (weekdays only).
    SIDECAR_M_RSI2 = os.getenv("SIDECAR_M_RSI2", "1").strip().lower() in ("1", "true", "yes")
    SIDECAR_M_RSI2_REFRESH_SEC = float(os.getenv("SIDECAR_M_RSI2_REFRESH_SEC", "60"))
    SIDECAR_M_RSI2_LIVE_IST_HOUR = int(os.getenv("SIDECAR_M_RSI2_LIVE_IST_HOUR", "14"))
    SIDECAR_M_RSI2_LIVE_IST_MINUTE = int(os.getenv("SIDECAR_M_RSI2_LIVE_IST_MINUTE", "45"))

    # Daily "pre-thrust" indicators (your missing setup bucket):
    # Computed from yesterday's daily OHLCV in Parquet / PipelineBridge history,
    # and persisted so you can check at a fixed IST time (default 14:30).
    SIDECAR_PRE_THRUST_ENABLED = os.getenv("SIDECAR_PRE_THRUST_ENABLED", "1").strip().lower() in ("1", "true", "yes")
    SIDECAR_PRE_THRUST_IST_HOUR = int(os.getenv("SIDECAR_PRE_THRUST_IST_HOUR", "14"))
    SIDECAR_PRE_THRUST_IST_MINUTE = int(os.getenv("SIDECAR_PRE_THRUST_IST_MINUTE", "30"))

    # Thresholds for yesterday features
    SIDECAR_PRE_THRUST_Y_VOL_X20_MIN = float(os.getenv("SIDECAR_PRE_THRUST_Y_VOL_X20_MIN", "2.0"))
    SIDECAR_PRE_THRUST_Y_RNG_ATR14_MIN = float(os.getenv("SIDECAR_PRE_THRUST_Y_RNG_ATR14_MIN", "1.5"))
    SIDECAR_PRE_THRUST_SCORE_MIN = int(os.getenv("SIDECAR_PRE_THRUST_SCORE_MIN", "6"))

    # Multi-year window for "near highs"
    SIDECAR_PRE_THRUST_MULTIYEAR_YEARS = int(os.getenv("SIDECAR_PRE_THRUST_MULTIYEAR_YEARS", "3"))

    # Only run the analysis for symbols currently moving big (live change_pct from SHM).
    SIDECAR_PRE_THRUST_LIVE_CHG_PCT_MIN = float(os.getenv("SIDECAR_PRE_THRUST_LIVE_CHG_PCT_MIN", "10.0"))
    SIDECAR_PRE_THRUST_MAX_MOVERS = int(os.getenv("SIDECAR_PRE_THRUST_MAX_MOVERS", "30"))

settings = Settings()
