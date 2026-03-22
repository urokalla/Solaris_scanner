import numpy as np
import datetime
from backend.auth import FyersAuthenticator

def local_fetch(ticker, period="1y", interval="1d"):
    """Sovereign Numpy Fetcher: Absolute Speed. Zero Pandas."""
    try:
        auth = FyersAuthenticator()
        fyers = auth.get_fyers_client()
        if not fyers: return np.empty((0, 6))
        
        to_date = datetime.date.today()
        # 30-YEAR-ENGINEER: Fixed 365 days for 1y.
        from_date = to_date - datetime.timedelta(days=365 if "1y" in period else 30)
        
        data = {
            "symbol": ticker,
            "resolution": "D",
            "date_format": "1",
            "range_from": from_date.strftime("%Y-%m-%d"),
            "range_to": to_date.strftime("%Y-%m-%d"),
            "cont_flag": "1"
        }
        res = fyers.history(data=data)
        if res.get("s") == "ok":
            # [ts, o, h, l, c, v]
            return np.array(res.get("candles", []), dtype='f8')
        return np.empty((0, 6))
    except Exception: return np.empty((0, 6))
