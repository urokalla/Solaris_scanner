import os, time, logging, numpy as np; from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text; from utils.parquet_io import save_parquet_vectorized
L = logging.getLogger("Persistence")

class DailyPersistence:
    def __init__(self, fyers, db_url, storage_path="data/historical"):
        self.fyers, self.engine, self.storage_path = fyers, create_engine(db_url), storage_path
        if not os.path.exists(self.storage_path): os.makedirs(self.storage_path)

    def fill_gaps(self, symbols):
        L.info(f"⚡ Starting Vector-Only Persistence...")
        for s in symbols:
            try:
                with self.engine.connect() as conn: last = conn.execute(text("SELECT MAX(timestamp) FROM prices WHERE symbol = :s"), {"s": s}).scalar()
                now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                fr = (last + timedelta(days=1)).strftime("%Y-%m-%d") if last else (now - timedelta(days=30)).strftime("%Y-%m-%d")
                res = self.fyers.history({"symbol": s, "resolution": "1D", "date_format": "1", "range_from": fr, "range_to": now.strftime("%Y-%m-%d"), "cont_flag": "1"})
                if res.get("s") == "ok" and (candles := res.get("candles", [])):
                    data = np.array(candles); save_parquet_vectorized(os.path.join(self.storage_path, f"{s.replace(':','_')}.parquet"), data)
                    rows = [{"s": s, "t": datetime.fromtimestamp(c[0]), "o": c[1], "h": c[2], "l": c[3], "c": c[4], "v": c[5], "tf": '1D'} for c in candles]
                    with self.engine.connect() as conn:
                        conn.execute(text("INSERT INTO prices (symbol, timestamp, open, high, low, close, volume, timeframe) VALUES (:s, :t, :o, :h, :l, :c, :v, :tf)"), rows)
                        conn.commit()
                time.sleep(0.1)
            except Exception as e: L.error(f"Fail {s}: {e}")
