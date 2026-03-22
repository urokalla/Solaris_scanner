import contextlib, os, time, logging
logger = logging.getLogger(__name__)
def sync_official_helper(self):
    logger.info("📡 [Sync] Start..."); 
    if not self.fyers: logger.error("❌ [Sync] No Fyers Client"); return
    try:
        stocks = list(self.symbols); logger.info(f"📦 [Sync] Symbols: {len(stocks)}")
        import requests, urllib3; urllib3.disable_warnings() 
        def patch_req(orig_func):
            def wrapper(*a, **kw):
                u = str(a[1]) if len(a)>1 else kw.get("url", "")
                if "fyers.in" in u: kw["verify"], kw["timeout"] = False, 10
                return orig_func(*a, **kw)
            return wrapper
        requests.Session.request = patch_req(requests.Session.request)
        try:
            logger.info(f"🔗 [Sync] Fetching {len(stocks)} quotes...")
            # Chunk the quotes request (limit 50 per call)
            for i in range(0, len(stocks), 50):
                batch = stocks[i:i+50]
                quotes = self.fyers.quotes({"symbols": ",".join(batch)})
                if quotes and quotes.get("code") == 200:
                    for q in quotes.get("d", []):
                        v = q.get("v", {})
                        s = v.get("symbol")
                        if not s or (idx := self.get_idx(s)) is None: continue
                        if (lp := float(v.get("lp", 0))) > 0: self.arr[idx]['ltp'] = lp
                        self.arr[idx]['change_pct'] = float(v.get("pcho", 0))
                        self.arr[idx]['p1d'] = f"{float(v.get('pcho', 0)):+.2f}%".encode()
                        self.arr[idx]['heartbeat'] = time.time()
                        self.pc_cache[s] = float(v.get("pc", 0)) if v.get("pc") else lp
                        self.av_cache[s] = float(v.get("v", 0)) / 10 if v.get("v") else 1000000 
            logger.info("✅ [Sync] Processing Complete.")
        except Exception as e: logger.error(f"❌ [Sync] Error: {e}")
    except Exception as e: logger.error(f"⚠️ [Sync] Error: {e}")
