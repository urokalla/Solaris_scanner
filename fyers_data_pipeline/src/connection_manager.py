import os
import logging
import threading
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

# Configure logging
from .utils import setup_logging
logger = setup_logging("pipeline_service.src")

class ConnectionManager:
    _lock = threading.Lock()
    """
    Manages connections to Fyers API, including authentication and session persistence.
    """
    def __init__(self, config_path: str = None):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        load_dotenv(config_path or os.path.join(project_root, 'config/.env'))
        self.client_id = os.getenv("FYERS_CLIENT_ID")
        self.secret_key = os.getenv("FYERS_SECRET_KEY")
        self.redirect_url = os.getenv("FYERS_REDIRECT_URL")
        self.access_token_path = os.getenv("FYERS_ACCESS_TOKEN_PATH", "access_token.txt")
        self.fyers = None
        self.log_dir = os.path.join(project_root, "logs")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
        self.request_log_path = os.path.join(self.log_dir, "api_requests.txt")
        self.max_daily_requests = 80000 

    def _load_access_token(self):
        """Loads access token from local file, prioritizing unified container path."""
        # Check environment variable first (best for Docker)
        env_path = os.getenv("FYERS_ACCESS_TOKEN_PATH")
        if env_path and os.path.exists(env_path):
            with open(env_path, 'r') as f:
                token = f.read().strip()
                if token:
                    logger.info(f"Loaded token from ENV path: {env_path}")
                    return token

        # Centralized container path fallback
        central_path = "/app/stock_scanner_sovereign/access_token.txt"
        if os.path.exists(central_path):
            with open(central_path, 'r') as f:
                token = f.read().strip()
                if token:
                    logger.info(f"Loaded token from CENTRAL PATH: {central_path}")
                    return token
        
        # Original logic fallback
        if os.path.exists(self.access_token_path):
            with open(self.access_token_path, 'r') as f:
                token = f.read().strip()
                if token:
                    logger.info(f"Loaded token from REQ path: {self.access_token_path}")
                    return token
        return None

    def _increment_request_count(self):
        """Persistent counter for API requests (Daily approx)."""
        with self._lock:
            count = 0
            if os.path.exists(self.request_log_path):
                with open(self.request_log_path, 'r') as f:
                    try:
                        count = int(f.read().strip())
                    except: count = 0
            
            count += 1
            with open(self.request_log_path, 'w') as f:
                f.write(str(count))
            return count

    def get_request_count(self):
        """Returns the current recorded request count."""
        if not os.path.exists(self.request_log_path):
            return 0
        with open(self.request_log_path, 'r') as f:
            try:
                return int(f.read().strip())
            except: return 0

    def connect(self):
        """Initializes the Fyers model with a valid access token."""
        access_token = self._load_access_token()
        if not access_token:
            logger.error("Access token not found. Please run authentication script.")
            return False
        
        try:
            token_prefix = f"{access_token[:10]}..." if access_token else "NONE"
            logger.info(f"Attempting Fyers connection with client_id: {self.client_id}, token: {token_prefix}")
            
            self.fyers = fyersModel.FyersModel(
                client_id=self.client_id, 
                token=access_token
            )
            # Verify connection with a simple profile call
            # 30-YEAR ENGINEER FIX: Fyers V3 sometimes returns -99 for get_profile while /history works.
            # We relax this check to allow the pipeline to proceed if history capability is confirmed.
            profile = self.fyers.get_profile()
            if profile.get('s') == 'ok' or profile.get('code') == 200:
                logger.info(f"Connected successfully as {profile.get('data', {}).get('name', 'Unknown User')}")
                return True
            else:
                # Fallback: Try a single symbol check
                logger.warning(f"Profile check failed ({profile.get('code')}). Trying historical data fallback...")
                test_hist = self.fyers.history({"symbol":"NSE:NIFTY50-INDEX","resolution":"1D","date_format":"1","range_from":"2026-03-18","range_to":"2026-03-19","cont_flag":"1"})
                if test_hist.get('s') == 'ok':
                    logger.info("✅ Pipeline Authentication Verified via Historical Data Fallback.")
                    return True
                
                logger.error(f"Failed to connect: {profile.get('message', 'Unknown Error')} (Code: {profile.get('code')})")
                return False
        except Exception as e:
            logger.exception(f"Exception during connection: {e}")
            return False

    def get_history(self, symbol: str, range_from: str, range_to: str, resolution: str = "1D"):
        """Wrapper for historical data fetching."""
        if not self.fyers:
            raise ConnectionError("Not connected to Fyers API")
        
        if self.get_request_count() >= self.max_daily_requests:
            logger.error("API Request Limit Reached (Safeguard). Stopping.")
            return {"s": "error", "message": "Safeguard: Daily Request Limit Reached", "code": -100}

        data = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "1",
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "1"
        }
        self._increment_request_count()
        return self.fyers.history(data=data)
