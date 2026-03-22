import os, time, logging
logger = logging.getLogger(__name__)
from fyers_apiv3 import fyersModel
from config.settings import settings; from .auth_headless import run_automated_login

class FyersAuthenticator:
    def __init__(self):
        self.client_id, self.secret_key, self.username = settings.FYERS_CLIENT_ID, settings.FYERS_SECRET_KEY, settings.FYERS_USERNAME
        self.pin, self.totp_key, self.redirect_url = settings.FYERS_PIN, settings.FYERS_TOTP_KEY, settings.FYERS_REDIRECT_URL
        self.token_file = settings.FYERS_ACCESS_TOKEN_PATH

    def get_access_token(self):
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f:
                if (token := f.read().strip()): return token
        return None

    def get_fyers_client(self):
        token = self.get_access_token()
        if not token:
            logger.info("Attempting automated login...")
            try: token = run_automated_login(self)
            except Exception as e: logger.error(f"Login fail: {e}"); return None
        return fyersModel.FyersModel(client_id=self.client_id, token=token, is_async=False, log_path="logs")

if __name__ == "__main__":
    auth = FyersAuthenticator(); token = auth.get_access_token()
    logger.info(f"Token: {token[:10]}..." if token else "No token")
