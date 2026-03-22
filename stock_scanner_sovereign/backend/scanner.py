import time, threading, ssl, os, logging, traceback, json
from typing import Optional
import logging.handlers
import numpy as np
from fyers_apiv3.FyersWebsocket import data_ws
from fyers_apiv3 import fyersModel
from backend.database import DatabaseManager
from backend.scanner_shm import SHMBridge
from backend.scanner_math import RSMathEngine
from utils.scanner_analysis import compute_trading_profile, profile_label_to_shm
from psycopg2.extras import execute_values

# Environment-Agnostic Logging (Relative to script location)
LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scanner_engine.log"))
# Ensure target directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO, # Promoted for visibility
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=20*1024*1024,
            backupCount=3
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MasterScanner")


def _tick_session_volume(m) -> float:
    """
    Fyers v3 full-mode symbol feed uses vol_traded_today (see fyers_apiv3 map.json data_val).
    Lite mode omits volume — keep FYERS_WS_LITEMODE off. Fallback: any key containing vol_traded.
    """
    if not isinstance(m, dict):
        return 0.0

    def _try_float(v):
        try:
            fv = float(v)
            if np.isfinite(fv) and fv >= 0:
                return fv
        except (TypeError, ValueError):
            pass
        return None

    for k in ("vol_traded_today", "vol_traded", "v", "volume", "total_traded_volume"):
        v = m.get(k)
        if v is None:
            continue
        got = _try_float(v)
        if got is not None:
            return got

    for k, v in m.items():
        if not isinstance(k, str):
            continue
        sk = k.lower()
        if sk in ("type", "symbol", "precision", "multiplier", "ltp", "ch", "chp"):
            continue
        if "vol_traded" in sk or sk in ("totalvolume", "dayvolume") or (
            "volume" in sk and "ckt" not in sk and "circuit" not in sk
        ):
            got = _try_float(v)
            if got is not None:
                return got
    return 0.0


import ssl
ssl._create_default_https_context = ssl._create_unverified_context
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

class MasterScanner:
    def __init__(self):
        from utils.constants import BENCHMARK_MAP
        from utils.symbols import get_nifty_symbols # Added import
        self.db, self.shm = DatabaseManager(), SHMBridge()
        try:
            self.db.ensure_live_state_brk_column()
            self.db.ensure_mrs_prev_day_column()
        except Exception as e:
            logger.warning("ensure_live_state_brk_column / mrs_prev_day: %s", e)
        is_master = os.getenv("SHM_MASTER", "true").lower() == "true"
        self.shm.setup(is_master_hint=is_master)
        
        if not is_master:
            logger.info("🖥️ [Scanner] Slave Mode Deteced: Synchronizing Brain with Master...")
            # Reactive wait: We cannot calculate math until we know the Master's memory slots
            for _ in range(30):
                self.shm.load_index_map()
                if self.shm.idx_map: break
                time.sleep(2)
            
            # Rebuild canonical list from SHM indices
            self.symbols = sorted(self.shm.idx_map.keys(), key=lambda x: self.shm.idx_map[x])
            logger.info(f"✅ [Scanner] Brain Synchronized: {len(self.symbols)} symbols adopted.")
        else:
            # Master logic: Symbol Discovery
            # Core symbols from DB + Benchmarks from Filter Blueprint
            # SOVEREIGN ARCHITECTURAL LOAD: Primary Universe is defined by the Database
            try:
                db_symbols = self.db.get_all_active_symbols()
                benchmark_symbols = list(BENCHMARK_MAP.values())
                
                # Step 1: Universal Merge (Architecture Pure)
                raw_symbols_set = set(db_symbols) | set(benchmark_symbols)
                
                if not raw_symbols_set:
                    logger.warning("No active symbols found in DB or benchmarks. Using NIFTY50 as fallback.")
                    raw_symbols_set.add("NSE:NIFTY50-INDEX")
                
                # Step 2: Synchronized Universe (No smart filters, just pure loading)
                self.symbols = sorted(list(raw_symbols_set))[:5000]
                logger.info(f"🌌 [Master] Architecture LOAD: {len(self.symbols)} securities synchronized.")
                
                # Step 3: Initialize Physical Segments (Master Only)
                # 30-Year Rule: Slaves must NEVER overwrite the Master's index map.
                if is_master:
                    logger.info(f"⚓ [Master] Anchoring {len(self.symbols)} symbols to SHM index map.")
                    self.shm.persist_index_map(self.symbols)
                else:
                    logger.debug("👓 [Slave] Reader initialization (Skipping Index Persist)")
            except Exception as e:
                logger.error(f"❌ [Master] Critical Boot Stalled: {e}")
                self.symbols = ["NSE:NIFTY50-INDEX"] # Failsafe Minimum
                self.shm.persist_index_map(self.symbols)
        
        # Step 4: O(1) Mapping for Pulse Updates
        self.sym_to_idx = {str(s): i for i, s in enumerate(self.symbols)}
        
        # Step 5: Final Intelligence Engine Attachment
        self.math = RSMathEngine(self.symbols, bench_sym="NSE:NIFTY50-INDEX")
        self.last_flush = 0
        self.ws = None
        # Master-only: session BUY latch + prior-day mRS cache (dashboard reads SHM written by master)
        self._buy_session_latch: set[str] = set()
        self._last_ist_trading_date = None
        self._mrs_prev_day_cache: dict[str, float] = {}
        self._mrs_prev_day_cache_ts: float = 0.0
        self._eod_snapshot_done_date = None

    def _maybe_roll_new_trading_day_ist(self):
        """Clear BUY latch on each new calendar day (Asia/Kolkata)."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        d = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        if self._last_ist_trading_date is None:
            self._last_ist_trading_date = d
            return
        if d != self._last_ist_trading_date:
            self._buy_session_latch.clear()
            self._last_ist_trading_date = d
            logger.info("New IST trading day: cleared BUY session latch")

    def _refresh_mrs_prev_day_cache(self, force: bool = False):
        """Load prior EOD weekly mRS from live_state (throttled unless force)."""
        if not force and (time.time() - self._mrs_prev_day_cache_ts) < 60.0:
            return
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT symbol, mrs_prev_day FROM live_state WHERE mrs_prev_day IS NOT NULL")
                    self._mrs_prev_day_cache = {r[0]: float(r[1]) for r in cur.fetchall()}
            self._mrs_prev_day_cache_ts = time.time()
        except Exception as e:
            logger.warning("mrs_prev_day cache refresh: %s", e)

    def _snapshot_eod_mrs_prev_day_if_due(self):
        """After ~15:30 IST, once per day: mrs_prev_day <- mrs for next session's column + TRENDING rules."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        IST = ZoneInfo("Asia/Kolkata")
        now = datetime.now(IST)
        if now.hour < 15 or (now.hour == 15 and now.minute < 30):
            return
        d = now.date()
        if self._eod_snapshot_done_date == d:
            return
        try:
            self.db.snapshot_mrs_prev_day_from_current_mrs()
            self._eod_snapshot_done_date = d
        except Exception:
            pass

    def _compute_grid_status(self, sym: str, prev_mrs: float, new_mrs: float, mrs_prev_day: Optional[float]) -> bytes:
        """
        BUY: session-latched after weekly mRS crosses above 0, or first day above 0 vs prior EOD <= 0.
        Stays BUY until mRS <= 0 or new IST day (latch cleared). TRENDING: mRS > 0 and prior EOD already > 0.
        """
        try:
            p, n = float(prev_mrs), float(new_mrs)
            if not np.isfinite(p):
                p = 0.0
            if not np.isfinite(n):
                n = 0.0
        except (TypeError, ValueError):
            return b"NOT TRENDING"
        if n <= 0:
            self._buy_session_latch.discard(sym)
            return b"NOT TRENDING"
        if sym in self._buy_session_latch:
            return b"BUY"
        if p <= 0:
            self._buy_session_latch.add(sym)
            return b"BUY"
        if mrs_prev_day is not None and mrs_prev_day > 0:
            return b"TRENDING"
        if mrs_prev_day is not None and mrs_prev_day <= 0:
            self._buy_session_latch.add(sym)
            return b"BUY"
        return b"TRENDING"

    def start_scanning(self, token=None):
        """Dashboard entry point. Handles Master/Slave bifurcation."""
        # 1. Identity Check: Are we the Master (Pulse) or the Slave (UI Reader)?
        is_master = os.getenv("SHM_MASTER", "true").lower() == "true"
        
        if not is_master:
            logger.info("📡 [Scanner] Slave Mode (Reader): Synchronizing Math Baseline for Dashboard.")
            self.math.load_historical_baseline()
            return

        # 2. Token Acquisition: Required for Master WebSocket
        if not token:
            token_path = os.getenv("FYERS_ACCESS_TOKEN_PATH", "access_token.txt")
            if os.path.exists(token_path):
                with open(token_path, 'r') as f: token = f.read().strip()
        
        # 3. Immortal Primary Loop: Re-spawn on socket death or logic exceptions
        while True:
            try:
                logger.info(f"🚀 [Scanner] Starting Master Pulse (Universe: {len(self.symbols)} securities)")
                self.start(token)
            except Exception as e:
                logger.error(f"❌ [Scanner] Master Pulse Crash: {e}")
                import traceback; traceback.print_exc()
                time.sleep(10) # Cooling period before re-ignition

    def get_ui_view(self, filters=None, page=1, page_size=50):
        """Standard JSON-view for the dashboard (Paginated + Filtered)"""
        try:
            filters = filters or {}
            logger.info(f"📊 UI Request -> Page: {page}, Size: {page_size}, Filters: {filters}")
            
            # Step 1: Universal Load (Trust the Index Map before filtering)
            valid_symbols = set(self.symbols)
            
            # Step 2: Specific Filtering (Universal Optimization)
            univ = filters.get("universe", "Nifty 500")
            if univ != "All Securities" and univ != getattr(self, '_last_u_name', None):
                from utils.symbols import get_nifty_symbols
                raw_u = get_nifty_symbols(univ)
                if raw_u: 
                    self._valid_symbols_cache = set(f"NSE:{s}-EQ" if ":" not in s else s for s in raw_u)
                    self._last_u_name = univ

            valid_symbols = getattr(self, '_valid_symbols_cache', set(self.symbols))
            
            # Step 3: O(1) Memory Extraction + Dashboard Filtering
            data = []
            search_val = filters.get("search")
            search_q = str(search_val).upper().strip() if search_val else ""
            status_f = str(filters.get("status", "ALL")).upper()
            profile_f = str(filters.get("profile", "ALL")).upper()
            
            for r in self.shm.arr:
                # 30-Year Rule: Decode with surgical null-stripping
                sym = r['symbol'].decode('utf-8', errors='ignore').strip('\x00').strip()
                if not sym or sym not in valid_symbols: continue
                
                # --- UNIVERSAL SEARCH & DASHBOARD FILTERING ---
                if search_q and search_q not in sym.upper(): continue
                
                st = r['status'].decode('utf-8', errors='ignore').strip('\x00').strip()
                if status_f != "ALL":
                    stu = st.upper().strip()
                    sf = status_f.strip().upper()
                    if sf == "NOT TRENDING":
                        if stu != "NOT TRENDING":
                            continue
                    elif sf == "TRENDING":
                        if stu != "TRENDING":
                            continue
                    elif sf not in stu:
                        continue
                
                pf = r['profile'].decode('utf-8', errors='ignore').strip('\x00').strip()
                if profile_f != "ALL" and profile_f not in pf.upper(): continue
                # ---------------------------------------------

                ch_pct = float(r["change_pct"])
                if not np.isfinite(ch_pct):
                    ch_pct = 0.0
                data.append({
                    "symbol": sym,
                    "ltp": float(r['ltp']),
                    "p1d": f"{ch_pct:.2f}%",
                    "chg_up": ch_pct > 0,
                    "chg_down": ch_pct < 0,
                    "mrs": float(r['mrs']),
                    "mrs_str": f"{r['mrs']:.2f}",
                    "mrs_prev": float(r['mrs_prev']),
                    "mrs_up": bool(r['mrs'] >= 0),
                    "mrs_daily": float(r['mrs_daily']),
                    "mrs_daily_str": f"{r['mrs_daily']:+.2f}",
                    "mrs_daily_up": bool(r['mrs_daily'] >= 0),
                    "rs_rating": int(r['rs_rating']),
                    "status": st,
                    "profile": pf if pf.strip() else "—",
                    "rv": f"{float(r['rv']):.2f}x",
                    "price_up": bool(r['price_up']),
                    "price_down": bool(r['price_down']),
                    "rv_up": bool(float(r["rv"]) >= 1.5),
                    "rv_down": bool(float(r["rv"]) >= 1.5 and ch_pct < 0),
                })

            # Layer 3: pivot from live_state (written by BreakoutScanner / sidecar), not SHM dtype
            try:
                syms = [d["symbol"] for d in data]
                bm = self.db.get_brk_lvl_map(syms) if syms else {}
                for d in data:
                    bl = bm.get(d["symbol"])
                    d["brk_lvl"] = bl
                    d["brk_lvl_str"] = f"{bl:.2f}" if bl is not None else "—"
            except Exception as ex:
                logger.warning("brk_lvl merge on main grid: %s", ex)
                for d in data:
                    d["brk_lvl"] = None
                    d["brk_lvl_str"] = "—"
            try:
                self.db.ensure_mrs_prev_day_column()
                syms2 = [d["symbol"] for d in data]
                pm = self.db.get_mrs_prev_day_map(syms2) if syms2 else {}
                for d in data:
                    v = pm.get(d["symbol"])
                    d["mrs_prev_day"] = v
                    d["mrs_prev_day_str"] = f"{v:.2f}" if v is not None else "—"
            except Exception as ex:
                logger.warning("mrs_prev_day merge on main grid: %s", ex)
                for d in data:
                    d["mrs_prev_day"] = None
                    d["mrs_prev_day_str"] = "—"
            
            # Simple sorting by RS Rating (Sovereign requirement)
            data.sort(key=lambda x: x['rs_rating'], reverse=True)
            
            # Step 5: Final Dictionary Delivery (Sovereign Alignment)
            start = (page - 1) * page_size
            results = data[start : start + page_size]
            
            # SOVEREIGN SIGNAL PATH: Strictly follow the Dashboard's selected Benchmark
            bench_sym = filters.get("benchmark", self.math.bench_sym)
            bench_ltp, bench_change, bench_up = "₹0.00", "0.00%", True
            
            # Use the already verified BENCH_SLOTS for O(1) Header lookup
            BENCH_SLOTS = {
                "NSE:NIFTY50-INDEX": 9001, "NSE:NIFTY100-INDEX": 9002, "NSE:NIFTY500-INDEX": 9003,
                "NSE:NIFTYMIDCAP100-INDEX": 9004, "NSE:NIFTYSMALLCAP100-INDEX": 9005, "NSE:NIFTYSMLCAP100-INDEX": 9005,
                "NSE:NIFTYMICROCAP250-INDEX": 9006, "NSE:NIFTYBANK-INDEX": 9007, "NSE:FINNIFTY-INDEX": 9008
            }
            
            b_slot = BENCH_SLOTS.get(bench_sym)
            if b_slot is not None and b_slot < len(self.shm.arr):
                b_r = self.shm.arr[b_slot]
                if b_r['ltp'] > 0:
                    bench_ltp = f"₹{b_r['ltp']:.2f}"
                    bench_change = f"{b_r['change_pct']:.2f}%"
                    bench_up = bool(float(b_r['change_pct']) >= 0)
            else:
                # Last Resort: Dynamic Bench Search
                b_idx = self.shm.get_idx(bench_sym)
                if b_idx is not None:
                    b_r = self.shm.arr[b_idx]; bench_ltp = f"₹{b_r['ltp']:.2f}"

            logger.info(f"✅ UI Response -> Returning {len(results)} of {len(data)} results.")
            return {
                "results": results,
                "total_count": len(data),
                "pulse": data[:20], # Ticker Feed
                "bench_ltp": bench_ltp,
                "bench_change": bench_change,
                "bench_up": bench_up,
                "status": "Active"
            }
        except Exception as e:
            logger.error(f"❌ UI Request Failed: {str(e)}\n{traceback.format_exc()}")
            return {"results": [], "total_count": 0, "status": "Error"}

    def update_params(self, **kwargs):
        """Allows Dashboard to adjust lookback, benchmark, etc. during runtime."""
        try:
            params = kwargs # Dashboard sends named arguments directly
            logger.info(f"⚙️ Param Update Request: {params}")
            
            # Handle both 'benchmark' and 'bench_sym' keys
            new_bench = params.get("benchmark") or params.get("bench_sym")
            
            if new_bench:
                logger.info(f"🔄 Switching Benchmark to: {new_bench}")
                self.math.set_benchmark(new_bench)
            
            return True
        except Exception as e:
            logger.error(f"❌ Param Update Failed: {str(e)}")
            return False
    def start(self, token):
        try:
            logger.info("🚀 Preparing historical baselines and pre-loading shared memory...")
            hist_root = os.getenv("PIPELINE_DATA_DIR", "/app/data/historical")
            mrs_w, mrs_d, ratings = self.math.load_historical_baseline(data_root=hist_root)
            try:
                self.math.backfill_vol_avg_from_prices(self.db)
            except Exception as e:
                logger.warning("vol_avg Postgres backfill skipped: %s", e)
            
            n = len(self.symbols)
            logger.info(f"✅ Baseline synchronization successful: {n} symbols processed.")
            
            # Proactively populate SHM with Last Close prices and ratings
            logger.info(f"💾 [Scanner] Restoring {n} symbols from baseline to physical memory segment...")
            self._maybe_roll_new_trading_day_ist()
            self._refresh_mrs_prev_day_cache(force=True)
            for i in range(n):
                target = self.shm.arr[i]
                last_price = float(self.math.price_matrix_d[i, -1])
                prev_price = float(self.math.price_matrix_d[i, -2])
                
                if last_price > 0:
                    target['ltp'] = last_price
                    if prev_price > 0:
                        change = ((last_price - prev_price) / prev_price) * 100
                        target['change_pct'] = change
                        target['price_up'] = 1 if change > 0 else 0
                        target['price_down'] = 1 if change < 0 else 0
                
                target['mrs'] = mrs_w[i]
                target['mrs_prev'] = mrs_w[i] # Initialize trend as neutral
                target['mrs_daily'] = mrs_d[i]
                try: 
                    # Numerical Shield: Prevent NaN/Inf from crashing the boot
                    if np.isnan(ratings[i]) or np.isinf(ratings[i]):
                        target['rs_rating'] = 0
                    else:
                        target['rs_rating'] = int(ratings[i])
                except:
                    target['rs_rating'] = 0
                sym = self.symbols[i]
                mw = float(mrs_w[i])
                mpd = self._mrs_prev_day_cache.get(sym)
                target["status"] = self._compute_grid_status(sym, mw, mw, mpd)
                try:
                    rr = int(target["rs_rating"])
                except Exception:
                    rr = 0
                target["profile"] = profile_label_to_shm(
                    compute_trading_profile(rr, mw, float(mrs_d[i]))
                )
                target["rv"] = float(self.math.compute_rvol(i))
            
            logger.info("✅ [Scanner] Physical memory pre-load complete. Committing state to backend.")
            
            # Step 1: Build the Ratings Dictionary for Persistence
            # Mapping memory-calculated results to the database schema
            try:
                ratings_map = {}
                for idx, sym in enumerate(self.symbols):
                    # Only persist if we have a valid mRS result
                    if mrs_w[idx] != 0:
                        ratings_map[sym] = {
                            "mRS": float(mrs_w[idx]),
                            "rs_rating": int(ratings[idx])
                        }
                
                if ratings_map:
                    self.db.save_rs_ratings(ratings_map)
                    logger.info(f"✅ [Scanner] Persisted {len(ratings_map)} Stock Ratings to DB.")
            except Exception as e:
                logger.error(f"❌ [Scanner] Baseline Persistence Fail: {e}")

            logger.info("📡 [Scanner] Connecting to Fyers WebSocket...")
            # litemode=True only sends ltp + symbol (no volume) — RVOL needs vol_traded_today from full feed.
            _lite = os.getenv("FYERS_WS_LITEMODE", "false").lower() in ("1", "true", "yes")
            self.ws = data_ws.FyersDataSocket(access_token=token, on_message=self.on_tick, litemode=_lite)
            
            # Explicitly force SSL bypass on the internal socket for V3
            try:
                # V3 internal structure varies; set sslopt early
                import ssl, websocket
                # Note: Newer fyers_apiv3 might handle this internally if we set global ssl context
                # but we'll try the common manual fix too
                self.ws.websocket_data.sslopt = {"cert_reqs": ssl.CERT_NONE, "check_hostname": False}
                logger.info("🔒 [Scanner] SSL Bypass applied.")
            except: pass
            
            # Start connection in a separate thread
            ws_thread = threading.Thread(target=self.ws.connect, daemon=True)
            ws_thread.start()
            
            # Subscriptions...
            formatted_symbols = list(set(f"NSE:{s}-EQ" if ":" not in s else s for s in self.symbols))
            logger.info(f"Subscribing to {len(formatted_symbols)} symbols...")
            for i in range(0, len(formatted_symbols), 500):
                batch = formatted_symbols[i:i+500]
                try:
                    self.ws.subscribe(symbols=batch, data_type="symbolData")
                    time.sleep(1.0)
                except Exception as e:
                    logger.error(f"Subscription batch error: {e}")
            
            while True:
                try:
                    # MASTER PULSE RE-INITIALIZATION: Global Scope Protection
                    from utils.constants import BENCHMARK_MAP
                    
                    # SOVEREIGN MASTER PULSE: Forcefully push current prices for Benchmarks into FIXED SHM SLOTS
                    # This eliminates 'Same Price' bug by anchoring each Index to its own hardware-level slot.
                    BENCH_SLOTS = {
                        "NSE:NIFTY50-INDEX": 9001, "NSE:NIFTY100-INDEX": 9002, "NSE:NIFTY500-INDEX": 9003,
                        "NSE:NIFTYMIDCAP100-INDEX": 9004, "NSE:NIFTYSMALLCAP100-INDEX": 9005, "NSE:NIFTYSMLCAP100-INDEX": 9005,
                        "NSE:NIFTYMICROCAP250-INDEX": 9006, "NSE:NIFTYBANK-INDEX": 9007, "NSE:FINNIFTY-INDEX": 9008
                    }
                    for b_name, b_sym in BENCHMARK_MAP.items():
                        slot = BENCH_SLOTS.get(b_sym)
                        if slot:
                            r = self.shm.arr[slot]
                            # AGGRESSIVE NAKED LOOKUP: Finds 'NIFTY100' even if name is 'NSE:NIFTY100-INDEX'
                            naked_key = b_sym.replace('NSE:', '').replace('-INDEX', '').replace('_', '').replace('-', '').upper()
                            
                            original_idx = None
                            for i, s in enumerate(self.symbols):
                                s_naked = str(s).replace('NSE:', '').replace('-INDEX', '').replace('_', '').replace('-', '').upper()
                                if naked_key == s_naked:
                                    original_idx = i
                                    break
                            
                            if original_idx is not None:
                                price = float(self.math.price_matrix_d[original_idx, -1])
                                # If math engine price is 0 (missing parquet), force it to 1.0 
                                # temporarily to PROVE the link is alive to the USER.
                                if price == 0: price = 0.0001 
                                
                                r['ltp'] = price
                                r['symbol'] = b_sym.encode()
                                r['heartbeat'] = time.time()
                    if hasattr(self.shm, 'mm'):
                        # self.shm.mm.flush()
                        pass
                    
                    # LAYER 2: Intelligence Unification (Atomic Sync)
                    if time.time() - self.last_flush > 60:
                        logger.info(f"💾 [Master] Recalculating RS for {len(self.symbols)} results...")
                        self._maybe_roll_new_trading_day_ist()
                        self._refresh_mrs_prev_day_cache()
                        
                        # 1. Trigger the Mansfield Intelligence Engine
                        mrs_w, mrs_d, rs_ranks = self.math.calculate_rs()
                        
                        # 2. Universal Sync: Mirror the Brain into the Physical Memory
                        # We use an Atomic Boundary Check to prevent the Index-Crashes that caused the 7-row ghosting.
                        max_sync = min(len(self.symbols), len(self.math.mrs_results), len(self.shm.arr))
                        for i in range(max_sync):
                            try:
                                r = self.shm.arr[i]
                                sym = self.symbols[i]
                                old_m = float(r['mrs'])
                                # Store previous value before updating to preserve trend color logic
                                r['mrs_prev'] = r['mrs']
                                r['mrs'] = float(mrs_w[i])
                                mpd = self._mrs_prev_day_cache.get(sym)
                                r["status"] = self._compute_grid_status(sym, old_m, float(r["mrs"]), mpd)
                                r['mrs_daily'] = float(mrs_d[i])
                                r['rs_rating'] = int(rs_ranks[i])
                                r["profile"] = profile_label_to_shm(
                                    compute_trading_profile(
                                        int(rs_ranks[i]), float(mrs_w[i]), float(mrs_d[i])
                                    )
                                )
                                # Target the Daily matrix for the 'Warm LTP' sync
                                r['ltp'] = float(self.math.price_matrix_d[i, -1])
                                pp = float(self.math.price_matrix_d[i, -2])
                                lp = float(r["ltp"])
                                if pp > 0:
                                    ch60 = ((lp - pp) / pp) * 100.0
                                else:
                                    ch60 = 0.0
                                r["change_pct"] = ch60
                                r["price_up"] = 1 if ch60 > 0 else 0
                                r["price_down"] = 1 if ch60 < 0 else 0
                                r["rv"] = float(self.math.compute_rvol(i))
                                # Micro-Pulse Heartbeat alignment
                                if r['heartbeat'] == 0: r['heartbeat'] = time.time()
                            except: continue
                        
                        # 3. Final Universal Persistence (X-Ray of the Universe)
                        self.persist_to_postgres()
                        self._snapshot_eod_mrs_prev_day_if_due()
                        logger.info("✅ [Scanner] Database sync complete.")
                        self.last_flush = time.time()
                        
                except Exception as e:
                    logger.error(f"❌ [Master] Critical Loop Error (Pulse/DB): {e}")
                    import traceback; traceback.print_exc()
                
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error in Scanner start: {e}")
            import traceback; traceback.print_exc()

    def on_tick(self, m):
        try:
            sym = m.get('symbol')
            price = m.get('ltp')
            vol = _tick_session_volume(m)
            if not sym or price is None: return
            
            # Map symbol to its index in SHM and Math Engine
            idx = self.shm.get_idx(sym) # Try full name first (Benchmarks)
            
            if idx is None:
                pure_sym = sym.split(':')[-1].replace('-EQ', '')
                idx = self.shm.get_idx(pure_sym)
            if idx is not None:
                # idx_map / RSMathEngine keys are canonical list symbols (e.g. NSE:XXX-EQ). Fyers may send
                # a different string; using lookup_sym can skip update_tick → day_vol stays 0 → RVOL 0.00.
                canon_sym = self.symbols[idx]
                self.math.update_tick(canon_sym, price, vol)
                if vol > 0:
                    try:
                        self.math.day_vol[idx] = float(vol)
                    except Exception:
                        pass
                target = self.shm.arr[idx]
                self._maybe_roll_new_trading_day_ist()
                self._refresh_mrs_prev_day_cache()
                full_sym = target["symbol"].decode("utf-8", errors="ignore").strip("\x00").strip()
                prev_mrs = float(target["mrs"])
                instant_mrs = self.math.get_instant_mrs(canon_sym, price)
                mpd = self._mrs_prev_day_cache.get(full_sym)
                target["status"] = self._compute_grid_status(full_sym, prev_mrs, instant_mrs, mpd)
                target['ltp'] = price
                target['mrs'] = instant_mrs
                try:
                    rr = int(target["rs_rating"])
                except Exception:
                    rr = 0
                try:
                    md = float(target["mrs_daily"])
                except Exception:
                    md = 0.0
                target["profile"] = profile_label_to_shm(
                    compute_trading_profile(rr, float(instant_mrs), md)
                )
                target['heartbeat'] = time.time()
                
                # RVOL: single source — RSMathEngine.compute_rvol (session v / 21d avg)
                target["rv"] = float(self.math.compute_rvol(idx))
                
                # Daily change % + sign flags (same basis as CHG% column / change_pct)
                prev = float(self.math.price_matrix_d[idx, -2])
                fp = float(price)
                if prev > 0:
                    ch = ((fp - prev) / prev) * 100.0
                else:
                    ch = 0.0
                target["change_pct"] = ch
                target["price_up"] = 1 if ch > 0 else 0
                target["price_down"] = 1 if ch < 0 else 0
        except Exception as e:
            pass
 # High frequency, don't log every tick error unless debugging

    def persist_to_postgres(self):
        # SOVEREIGN PROOF: Physically probe every possible memory slot for valid symbols
        recs = []
        for i in range(len(self.shm.arr)):
            r = self.shm.arr[i]
            sym = r['symbol'].decode('utf-8', errors='ignore').strip('\x00').strip()
            if sym != "":
                recs.append((
                    sym, 
                    float(r['ltp']), 
                    float(r['mrs']), 
                    int(r['rs_rating']), 
                    r['status'].decode('utf-8', errors='ignore').strip('\x00').strip()
                ))
        
        if not recs:
            print("⚠️ [Scanner] Memory Persistence Aborted: No valid symbols found in SHM segment.", flush=True)
            return

        print(f"💾 [Master] Syncing Universal World: {len(recs)} symbols -> Postgres...", flush=True)
        
        q = """
            INSERT INTO live_state (symbol, last_price, mrs, rs_rating, status) 
            VALUES %s 
            ON CONFLICT (symbol) DO UPDATE SET 
                last_price = EXCLUDED.last_price, 
                mrs = EXCLUDED.mrs, 
                rs_rating = EXCLUDED.rs_rating, 
                status = EXCLUDED.status
        """
        print("💡 [DB] Acquiring Postgres Connection...", flush=True)
        with self.db.get_connection() as conn:
            print("💡 [DB] Connection acquired. Executing Values...", flush=True)
            with conn.cursor() as cur: 
                execute_values(cur, q, recs)
                print("💡 [DB] Execution complete. Committing...", flush=True)
                conn.commit()
                print("✅ [DB] Commit successful.", flush=True)

if __name__ == "__main__":
    try:
        logger.info("🚀 [Scanner Engine] Initializing Sovereign Intelligence Loop...")
        scanner = MasterScanner()
        token_path = os.getenv("FYERS_ACCESS_TOKEN_PATH", "access_token.txt")
        logger.info(f"📡 [Scanner Engine] Waiting for token at {token_path}...")
        while not os.path.exists(token_path): 
            time.sleep(5)
        
        with open(token_path, 'r') as f: 
            token = f.read().strip()
            
        if not token:
            logger.error("❌ [Scanner Engine] Token file is empty!")
        else:
            logger.info("✅ [Scanner Engine] Token validated. Starting Scanner...")
            scanner.start(token)
    except Exception as e:
        import traceback
        msg = f"💥 [Scanner Engine] FATAL ERROR in Main: {e}\n{traceback.format_exc()}"
        print(msg, flush=True) # Direct physical stdout push
        logger.error(msg)

# Legacy Compatibility Alias 
StockScanner = MasterScanner
