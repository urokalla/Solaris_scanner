import os
import logging
from fyers_apiv3.fyers_data_socket import FyersDataSocket
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FyersWebSocket:
    """
    Handles real-time data streaming from Fyers.
    """
    def __init__(self, access_token: str, client_id: str):
        self.access_token = access_token
        self.client_id = client_id
        self.fs = None

    def on_message(self, message):
        """Callback for received messages."""
        logger.info(f"Message received: {message}")

    def on_error(self, message):
        """Callback for errors."""
        logger.error(f"Error: {message}")

    def on_open(self):
        """Callback for connection open."""
        logger.info("Connection opened")
        # Example subscription
        symbols = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX"]
        self.fs.subscribe(symbols=symbols, data_type="SymbolUpdate")

    def on_close(self):
        """Callback for connection close."""
        logger.info("Connection closed")

    def connect(self):
        """Initializes and connects the data socket."""
        self.fs = FyersDataSocket(
            access_token=self.access_token,
            log_path=os.path.join(os.getcwd(), "logs"),
            litemode=False,
            rewrite_log=True,
            reconnect=True,
            on_connect=self.on_open,
            on_close=self.on_close,
            on_error=self.on_error,
            on_message=self.on_message
        )
        self.fs.connect()

if __name__ == "__main__":
    load_dotenv("config/.env")
    token_path = os.getenv("FYERS_ACCESS_TOKEN_PATH", "access_token.txt")
    
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()
        
        client_id = os.getenv("FYERS_CLIENT_ID")
        ws = FyersWebSocket(token, client_id)
        ws.connect()
    else:
        print("Access token not found. Please run authentication first.")
