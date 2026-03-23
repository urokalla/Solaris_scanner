import time, threading, os, ssl, logging
logger = logging.getLogger(__name__)
from concurrent.futures import ThreadPoolExecutor
from .scanner_math import update_signals_vectorized; from fyers_apiv3.FyersWebsocket import data_ws
ssl._create_default_https_context = ssl._create_unverified_context
def materialization_loop_helper(self):
    while True:
        try:
            bench_h = self.db.get_historical_data(self.bench_sym, "1d", limit=400)
            with ThreadPoolExecutor(max_workers=10) as exe:
                for s in list(self.symbols): exe.submit(update_signals_vectorized, self, s, self.db.get_historical_data(s, "1d", limit=400), bench_h)
            self._write_health("running")
        except: pass
        time.sleep(300)
def start_scanning_helper(self):
    if not self.is_master: return
    self.symbols = sorted(self.db.get_all_active_symbols())[:4950]
    self.sync_official()
    threading.Thread(target=self._materialization_loop, daemon=True).start()
    try:
        self.ws = data_ws.FyersDataSocket(access_token=self.auth.get_access_token(), on_message=self.on_message, litemode=True)
        # Force SSL bypass in websocket-client
        if hasattr(self.ws, 'websocket_data'): self.ws.websocket_data.sslopt = {"cert_reqs": ssl.CERT_NONE}
        threading.Thread(target=self.ws.connect, daemon=True).start()
        time.sleep(5); self._write_health("running")
        if hasattr(self.ws, 'subscribe'):
            try:
                syms = self.symbols[:5000]
                self.ws.subscribe(symbols=syms, data_type="SymbolUpdate")
            except Exception as e:
                logger.warning(f"⚠️ [WS] Sub Error: {e}")
    except Exception as e: logger.error(f"❌ [WS] Init Error: {e}")
