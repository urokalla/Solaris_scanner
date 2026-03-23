import time, threading, ssl, os, logging, traceback, json, re
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
        # Master-only: session BUY NOW latch + prior-day mRS cache (dashboard reads SHM written by master)
        self._buy_session_latch: set[str] = set()
        self._last_ist_trading_date = None
        self._mrs_prev_day_cache: dict[str, float] = {}
        self._mrs_prev_day_cache_ts: float = 0.0
        self._eod_snapshot_done_date = None
        self._last_health_log_ts: float = 0.0
        self._last_tick_seen_ts: float = 0.0
        self._last_targeted_resub_ts: float = 0.0
        self._invalid_ws_symbols_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "fyers_invalid_symbols.json")
        )
        self._unresolved_ws_symbols_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "fyers_unresolved_symbols.json")
        )
        self._invalid_ws_symbols: set[str] = set()
        self._load_invalid_ws_symbols()

    def _normalize_ws_symbol(self, s: str) -> str:
        x = str(s or "").strip().upper()
        return x if ":" in x else f"NSE:{x}"

    def _load_invalid_ws_symbols(self):
        try:
            if not os.path.isfile(self._invalid_ws_symbols_path):
                self._invalid_ws_symbols = set()
                return
            with open(self._invalid_ws_symbols_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            arr = payload if isinstance(payload, list) else payload.get("symbols", [])
            self._invalid_ws_symbols = {self._normalize_ws_symbol(s) for s in arr if str(s).strip()}
            if self._invalid_ws_symbols:
                logger.info("Loaded %s auto-blocked WS symbols.", len(self._invalid_ws_symbols))
        except Exception as e:
            logger.warning("Failed loading invalid WS symbols list: %s", e)
            self._invalid_ws_symbols = set()

    def _save_invalid_ws_symbols(self):
        try:
            data = sorted(self._invalid_ws_symbols)
            with open(self._invalid_ws_symbols_path, "w", encoding="utf-8") as f:
                json.dump({"symbols": data}, f, ensure_ascii=True, indent=2)
        except Exception as e:
            logger.warning("Failed persisting invalid WS symbols list: %s", e)

    def _record_invalid_ws_symbols(self, symbols):
        try:
            norm = {self._normalize_ws_symbol(s) for s in (symbols or []) if str(s).strip()}
            if not norm:
                return
            before = len(self._invalid_ws_symbols)
            self._invalid_ws_symbols.update(norm)
            if len(self._invalid_ws_symbols) > before:
                logger.warning(
                    "Auto-blocking %s new invalid WS symbols (total blocked=%s).",
                    len(self._invalid_ws_symbols) - before,
                    len(self._invalid_ws_symbols),
                )
                self._save_invalid_ws_symbols()
        except Exception as e:
            logger.warning("Failed recording invalid WS symbols: %s", e)

    def _save_unresolved_ws_symbols(self, unresolved, tokens, expected):
        """Persist unresolved subscribe symbols for manual triage even without explicit invalid_symbols errors."""
        try:
            payload = {
                "timestamp": int(time.time()),
                "tokens": int(tokens),
                "expected": int(expected),
                "missing": int(len(unresolved or [])),
                "symbols": sorted({self._normalize_ws_symbol(s) for s in (unresolved or []) if str(s).strip()}),
            }
            with open(self._unresolved_ws_symbols_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=True, indent=2)
        except Exception as e:
            logger.warning("Failed writing unresolved WS symbols file: %s", e)

    def _resolved_symbols_from_token_map(self, m) -> set[str]:
        """SDK-safe extraction for symbol_token map (supports key/value inverted layouts)."""
        out = set()
        if not isinstance(m, dict):
            return out
        for k, v in m.items():
            ks = str(k).upper()
            vs = str(v).upper()
            if ":" in ks:
                out.add(ks)
            if ":" in vs:
                out.add(vs)
        return out

    def _current_ws_target_symbols(self) -> list[str]:
        self._load_invalid_ws_symbols()
        blocked = set(self._invalid_ws_symbols)
        syms = list({self._to_fyers_symbol(f"NSE:{s}-EQ" if ":" not in s else s) for s in self.symbols})
        return [s for s in syms if str(s).upper() not in blocked]

    def _maybe_resubscribe_unresolved_symbols(self):
        """
        Runtime healing: periodically retry unresolved symbols while socket is alive.
        This avoids waiting for a full restart when a few symbols miss initial mapping.
        """
        try:
            if self.ws is None or not self.ws.is_connected():
                return
            now = time.time()
            interval = float(os.getenv("FYERS_WS_TARGETED_RESUB_SEC", "90"))
            if (now - self._last_targeted_resub_ts) < interval:
                return
            self._last_targeted_resub_ts = now

            target = self._current_ws_target_symbols()
            expect = len(target)
            if expect <= 0:
                return
            tok_map = getattr(self.ws, "symbol_token", {}) or {}
            resolved = self._resolved_symbols_from_token_map(tok_map)
            unresolved = [s for s in target if str(s).upper() not in resolved] if resolved else []
            self._save_unresolved_ws_symbols(unresolved, len(tok_map), expect)
            if not unresolved:
                return

            max_retry = max(20, min(300, int(os.getenv("FYERS_WS_TARGETED_RESUB_MAX", "120"))))
            batch = max(5, min(40, int(os.getenv("FYERS_WS_TARGETED_RESUB_BATCH", "20"))))
            retry_syms = unresolved[:max_retry]
            for i in range(0, len(retry_syms), batch):
                b = retry_syms[i : i + batch]
                try:
                    self.ws.subscribe(symbols=b, data_type=os.getenv("FYERS_WS_DATA_TYPE", "SymbolUpdate"))
                except Exception:
                    pass
                time.sleep(0.20)
            logger.info(
                "🎯 [Resub] Retried %s unresolved symbols (tokens=%s/%s)",
                len(retry_syms), len(tok_map), expect,
            )
        except Exception as e:
            logger.debug("Targeted unresolved resubscribe skipped: %s", e)

    def _log_tick_health(self):
        """
        Periodic observability for live subscription quality.
        Logs token coverage, stale heartbeat count, and unresolved tick mappings.
        """
        try:
            now = time.time()
            interval = float(os.getenv("SCANNER_HEALTH_LOG_SEC", "10"))
            if (now - self._last_health_log_ts) < interval:
                return
            self._last_health_log_ts = now
            n = min(len(self.symbols), len(self.shm.arr))
            if n <= 0:
                return
            hb = np.asarray(self.shm.arr["heartbeat"][:n], dtype=np.float64)
            stale_sec = float(os.getenv("SCANNER_STALE_HEARTBEAT_SEC", "120"))
            stale_n = int(np.sum((hb <= 0) | ((now - hb) > stale_sec)))
            tok_n = len(getattr(self.ws, "symbol_token", {}) or {}) if self.ws is not None else 0
            unresolved = int(getattr(self, "_tick_unresolved", 0))
            lag = (now - float(self._last_tick_seen_ts)) if self._last_tick_seen_ts > 0 else None
            logger.info(
                "📈 [TickHealth] tokens=%s/%s stale>%ss=%s unresolved=%s last_tick_age=%s",
                tok_n,
                n,
                int(stale_sec),
                stale_n,
                unresolved,
                f"{lag:.1f}s" if lag is not None else "never",
            )
        except Exception as e:
            logger.debug("TickHealth log skipped: %s", e)

    def on_ws_error(self, message):
        """Capture Fyers WS invalid_symbols and persist as auto-exclude list."""
        try:
            payload = message
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {"message": payload}
            if isinstance(payload, dict):
                invalid = payload.get("invalid_symbols")
                if isinstance(invalid, list) and invalid:
                    self._record_invalid_ws_symbols(invalid)
            logger.error("Fyers WS error: %s", payload)
        except Exception as e:
            logger.error("Fyers WS error (unparsed): %s | parse_err=%s", message, e)

    def _maybe_roll_new_trading_day_ist(self):
        """Clear BUY NOW latch on each new calendar day (Asia/Kolkata)."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        d = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        if self._last_ist_trading_date is None:
            self._last_ist_trading_date = d
            return
        if d != self._last_ist_trading_date:
            self._buy_session_latch.clear()
            self._last_ist_trading_date = d
            logger.info("New IST trading day: cleared BUY NOW session latch")

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
        BUY NOW: session-latched after weekly mRS crosses above 0, or first day above 0 vs prior EOD <= 0.
        Stays BUY NOW for the day until mRS <= 0 or new IST day (latch cleared). TRENDING: mRS > 0 and prior EOD already > 0.
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
            return b"BUY NOW"
        if p <= 0:
            self._buy_session_latch.add(sym)
            return b"BUY NOW"
        if mrs_prev_day is not None and mrs_prev_day > 0:
            return b"TRENDING"
        if mrs_prev_day is not None and mrs_prev_day <= 0:
            self._buy_session_latch.add(sym)
            return b"BUY NOW"
        return b"TRENDING"

    def _resolve_tick_idx(self, sym) -> Optional[int]:
        """
        Map Fyers tick `symbol` to SHM row index. idx_map keys are canonical (e.g. NSE:RELIANCE-EQ).
        """
        if not sym:
            return None
        idx_map = getattr(self, "sym_to_idx", None) or self.shm.idx_map
        def _idx(k: str):
            return idx_map.get(str(k))
        s = re.sub(r"\s+", "", str(sym).strip())
        idx = _idx(s)
        if idx is not None:
            return idx
        su = s.upper()
        if su != s:
            idx = _idx(su)
            if idx is not None:
                return idx
        if ":" not in s:
            return None
        tail = s.split(":", 1)[-1].strip()
        # EQ: map RELIANCE / BAJAJ-AUTO → NSE:…-EQ (idx_map never uses bare ticker)
        if tail.endswith("-EQ"):
            idx = _idx(f"NSE:{tail}")
            if idx is not None:
                return idx
        if tail.endswith("-INDEX"):
            idx = _idx(f"NSE:{tail}")
            if idx is not None:
                return idx
        if not tail.endswith("-EQ") and "-INDEX" not in tail.upper():
            idx = _idx(f"NSE:{tail}-EQ")
            if idx is not None:
                return idx
        # Fyers uses '-' in many EQ names; DB can still contain '_' legacy IDs.
        if tail.endswith("-EQ"):
            head = tail[:-3]
            if "-" in head:
                idx = _idx(f"NSE:{head.replace('-', '_')}-EQ")
                if idx is not None:
                    return idx
        elif tail.endswith("-INDEX"):
            head = tail[:-6]
            if "-" in head:
                idx = _idx(f"NSE:{head.replace('-', '_')}-INDEX")
                if idx is not None:
                    return idx
        # Index alias compatibility (legacy DB IDs vs Fyers feed symbols).
        _idx_alias_rev = {
            "NSE:NIFTYMIDCAP100-INDEX": "NSE:MIDCAP100-INDEX",
            "NSE:NIFTYSMLCAP100-INDEX": "NSE:SMALLCAP100-INDEX",
        }
        back = _idx_alias_rev.get(su)
        if back:
            idx = _idx(back)
            if idx is not None:
                return idx
        return None

    def _to_fyers_symbol(self, s: str) -> str:
        """
        Canonicalize DB/legacy symbols to Fyers WS symbols for subscribe().
        Keep SHM/internal symbol IDs unchanged; only normalize the outbound WS list.
        """
        x = str(s or "").strip().upper()
        if not x:
            return x
        if x.endswith("_INDEX.PARQUET"):
            # e.g. NSE:NIFTY50_INDEX.PARQUET -> NSE:NIFTY50-INDEX
            x = x.replace("_INDEX.PARQUET", "-INDEX")
        if not x.startswith("NSE:"):
            x = f"NSE:{x}"
        _idx_alias = {
            "NSE:MIDCAP100-INDEX": "NSE:NIFTYMIDCAP100-INDEX",
            "NSE:SMALLCAP100-INDEX": "NSE:NIFTYSMLCAP100-INDEX",
        }
        x = _idx_alias.get(x, x)
        if x.endswith("-EQ"):
            head = x[4:-3]
            # Legacy DB symbols like BAJAJ_AUTO/NAM_INDIA must be hyphenated for Fyers.
            head = head.replace("_", "-")
            x = f"NSE:{head}-EQ"
        return x

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
            # Iterate canonical symbol indices only — NOT full shm.arr (10k rows). Scanning all rows
            # can duplicate tickers (e.g. benchmark mirror slots 9001+ vs primary index row), so one
            # symbol could appear twice with different LTP/heartbeat and "fixing" one row broke another.
            data = []
            search_val = filters.get("search")
            search_q = str(search_val).upper().strip() if search_val else ""
            status_f = str(filters.get("status", "ALL")).upper()
            profile_f = str(filters.get("profile", "ALL")).upper()
            n_sym = len(self.symbols)
            for i in range(min(n_sym, len(self.shm.arr))):
                sym = self.symbols[i]
                if sym not in valid_symbols:
                    continue
                r = self.shm.arr[i]
                
                # --- UNIVERSAL SEARCH & DASHBOARD FILTERING ---
                if search_q and search_q not in sym.upper():
                    continue
                
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
                if profile_f != "ALL" and profile_f not in pf.upper():
                    continue
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
                # Benchmark not in fixed slots (e.g. uncommon index): read primary row
                b_idx = self.shm.get_idx(bench_sym)
                if b_idx is not None:
                    b_r = self.shm.arr[b_idx]
                    if b_r['ltp'] > 0:
                        bench_ltp = f"₹{b_r['ltp']:.2f}"
                        bench_change = f"{float(b_r['change_pct']):.2f}%"
                        bench_up = bool(float(b_r['change_pct']) >= 0)

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
                pp = float(self.math.price_matrix_d[i, -2])
                if pp > 0:
                    self.math.prev_close_day[i] = pp
                prev_price = float(self.math.prev_close_day[i])
                
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
            # fyers_apiv3 SymbolConversion only maps EQ scrips when data_type is "SymbolUpdate".
            # Using "symbolData" breaks conversion (silent failure / empty subs).
            _ws_dtype = os.getenv("FYERS_WS_DATA_TYPE", "SymbolUpdate")
            try:
                data_ws.FyersDataSocket._instance = None
            except Exception:
                pass
            self._logged_first_tick = False
            self._tick_unresolved = 0
            self.ws = data_ws.FyersDataSocket(
                access_token=token,
                on_message=self.on_tick,
                on_error=self.on_ws_error,
                litemode=_lite,
            )
            
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
            _timeout = float(os.getenv("FYERS_WS_CONNECT_TIMEOUT_SEC", "120"))
            _deadline = time.time() + _timeout
            while not self.ws.is_connected() and time.time() < _deadline:
                time.sleep(0.25)
            if not self.ws.is_connected():
                raise ConnectionError(
                    f"Fyers WebSocket not ready after {_timeout:.0f}s; check token, network, or Fyers status."
                )
            time.sleep(1.5)
            formatted_symbols = list(
                {self._to_fyers_symbol(f"NSE:{s}-EQ" if ":" not in s else s) for s in self.symbols}
            )
            # Unified invalid/unwanted symbols source: persisted auto-blocklist file.
            _ws_exclude = set()
            self._load_invalid_ws_symbols()
            _ws_exclude |= set(self._invalid_ws_symbols)
            formatted_symbols = [s for s in formatted_symbols if str(s).upper() not in _ws_exclude]
            if len(formatted_symbols) > 5000:
                logger.warning(
                    "Capping WebSocket subscription at 5000 symbols (have %s).",
                    len(formatted_symbols),
                )
                formatted_symbols = formatted_symbols[:5000]
            _batch = max(50, min(500, int(os.getenv("FYERS_WS_SUB_BATCH", "200"))))
            _sub_sleep = float(os.getenv("FYERS_WS_SUB_BATCH_SLEEP_SEC", "0.80"))
            logger.info(
                f"Subscribing to {len(formatted_symbols)} symbols in batches of {_batch} (data_type={_ws_dtype})..."
            )
            for i in range(0, len(formatted_symbols), _batch):
                batch = formatted_symbols[i : i + _batch]
                try:
                    self.ws.subscribe(symbols=batch, data_type=_ws_dtype)
                except Exception as e:
                    logger.error("Fyers subscribe batch %s-%s failed: %s", i, i + len(batch), e)
                    raise ConnectionError(f"Fyers subscribe batch failed: {e}") from e
                time.sleep(_sub_sleep)
            tok_map = getattr(self.ws, "symbol_token", {}) or {}
            _n_tok = len(tok_map)
            # Defensive replay pass: on unstable sessions, only part of batched subscriptions can stick.
            # Replay the full list once in smaller batches if initial token coverage is too low.
            try:
                expect = len(formatted_symbols)
                if expect > 0 and _n_tok < int(expect * 0.80):
                    r_batch = max(50, min(200, int(os.getenv("FYERS_WS_RESUB_BATCH", "150"))))
                    logger.warning(
                        "Fyers partial subscribe: %s/%s tokens. Replaying full subscription once...",
                        _n_tok, expect,
                    )
                    for i in range(0, expect, r_batch):
                        batch = formatted_symbols[i : i + r_batch]
                        try:
                            self.ws.subscribe(symbols=batch, data_type=_ws_dtype)
                        except Exception as ex:
                            logger.warning("Fyers resubscribe batch %s-%s failed: %s", i, i + len(batch), ex)
                        time.sleep(_sub_sleep)
                    tok_map = getattr(self.ws, "symbol_token", {}) or {}
                    _n_tok = len(tok_map)
            except Exception:
                pass
            # Recovery phase: isolate unresolved symbols in smaller batches so a few invalid symbols
            # do not suppress a large portion of otherwise valid subscriptions.
            try:
                expect = len(formatted_symbols)
                recover_min = float(os.getenv("FYERS_WS_RECOVER_MIN_RATIO", "0.98"))
                if expect > 0 and (_n_tok / max(expect, 1)) < recover_min:
                    def _resolved_symbols_from_token_map(m):
                        # SDK versions differ: symbol_token can be {symbol: token} OR {token: symbol}.
                        out = set()
                        if not isinstance(m, dict):
                            return out
                        for k, v in m.items():
                            ks = str(k).upper()
                            vs = str(v).upper()
                            if ":" in ks:
                                out.add(ks)
                            if ":" in vs:
                                out.add(vs)
                        return out

                    resolved_syms = _resolved_symbols_from_token_map(tok_map)
                    if not resolved_syms:
                        logger.warning(
                            "Skipping recovery pass: could not infer resolved symbols from symbol_token shape (entries=%s).",
                            _n_tok,
                        )
                    pending = [s for s in formatted_symbols if str(s).upper() not in resolved_syms] if resolved_syms else []
                    if pending and self.ws.is_connected():
                        r2_batch = max(10, min(50, int(os.getenv("FYERS_WS_RECOVER_BATCH", "25"))))
                        r2_passes = max(1, min(8, int(os.getenv("FYERS_WS_RECOVER_PASSES", "3"))))
                        logger.warning(
                            "Fyers token coverage low (%s/%s). Recovery for %s unresolved symbols (batch=%s passes=%s)...",
                            _n_tok, expect, len(pending), r2_batch, r2_passes,
                        )
                        for p in range(r2_passes):
                            if not pending or not self.ws.is_connected():
                                break
                            for i in range(0, len(pending), r2_batch):
                                batch = pending[i : i + r2_batch]
                                try:
                                    self.ws.subscribe(symbols=batch, data_type=_ws_dtype)
                                except Exception as ex:
                                    logger.warning(
                                        "Fyers recovery pass=%s batch %s-%s failed: %s",
                                        p + 1, i, i + len(batch), ex,
                                    )
                                time.sleep(max(_sub_sleep, 0.35))
                            tok_map = getattr(self.ws, "symbol_token", {}) or {}
                            _n_tok = len(tok_map)
                            resolved_syms = _resolved_symbols_from_token_map(tok_map)
                            pending = [s for s in formatted_symbols if str(s).upper() not in resolved_syms] if resolved_syms else []
                            logger.info(
                                "Fyers recovery progress pass=%s tokens=%s/%s pending=%s",
                                p + 1, _n_tok, expect, len(pending),
                            )
                            # Final stretch: try single-symbol subscribe for stubborn leftovers.
                            if pending and len(pending) <= 120 and self.ws.is_connected():
                                for s in list(pending):
                                    try:
                                        self.ws.subscribe(symbols=[s], data_type=_ws_dtype)
                                    except Exception:
                                        pass
                                    time.sleep(0.12)
                                tok_map = getattr(self.ws, "symbol_token", {}) or {}
                                _n_tok = len(tok_map)
                                resolved_syms = _resolved_symbols_from_token_map(tok_map)
                                pending = [s for s in formatted_symbols if str(s).upper() not in resolved_syms] if resolved_syms else []
                        tok_map = getattr(self.ws, "symbol_token", {}) or {}
                        _n_tok = len(tok_map)
                        resolved_syms = _resolved_symbols_from_token_map(tok_map)
                        unresolved = [s for s in formatted_symbols if str(s).upper() not in resolved_syms] if resolved_syms else []
                        self._save_unresolved_ws_symbols(unresolved, _n_tok, expect)
                        if unresolved:
                            sample = ", ".join(unresolved[:20])
                            logger.warning(
                                "Fyers unresolved symbols after recovery: %s (showing up to 20): %s",
                                len(unresolved), sample,
                            )
                    else:
                        self._save_unresolved_ws_symbols([], _n_tok, expect)
            except Exception:
                pass
            logger.info("Fyers WS symbol_token entries after subscribe: %s", _n_tok)
            self._log_tick_health()
            if _n_tok == 0:
                raise ConnectionError(
                    "Fyers subscribe produced zero symbol_token entries (symbol conversion failed or silent SDK error). "
                    "Check token, api-t1.fyers.in from this container, and FYERS_WS_DATA_TYPE=SymbolUpdate."
                )
            self.last_flush = time.time()

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
                                # Header / sidebar read benchmark from fixed BENCH_SLOTS (9001+), not from
                                # the primary index row. Mirror the live row so CHG% matches ticks + on_tick.
                                src = self.shm.arr[original_idx]
                                r['ltp'] = float(src['ltp'])
                                r['change_pct'] = float(src['change_pct'])
                                r['price_up'] = int(src['price_up'])
                                r['price_down'] = int(src['price_down'])
                                r['heartbeat'] = float(src['heartbeat'])
                                r['symbol'] = b_sym.encode()
                                if r['ltp'] <= 0:
                                    price = float(self.math.price_matrix_d[original_idx, -1])
                                    if price == 0:
                                        price = 0.0001
                                    r['ltp'] = price
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
                                # Never overwrite live LTP from historical matrix during periodic RS flush.
                                # If no live tick ever arrived for this row, warm it once from matrix.
                                lp = float(r["ltp"])
                                if lp <= 0:
                                    lp = float(self.math.price_matrix_d[i, -1])
                                    if lp > 0:
                                        r["ltp"] = lp
                                pp = float(self.math.prev_close_day[i])
                                if pp <= 0:
                                    pp = float(self.math.price_matrix_d[i, -2])
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
                self._log_tick_health()
                self._maybe_resubscribe_unresolved_symbols()
                
                time.sleep(5)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error in Scanner start: {e}")
            import traceback; traceback.print_exc()

    def on_tick(self, m):
        """
        Fyers fires at high frequency; never let mRS/RVOL/profile failures drop LTP + CHG%.
        """
        try:
            if not isinstance(m, dict):
                return
            sym = m.get("symbol")
            if isinstance(sym, bytes):
                sym = sym.decode("utf-8", errors="ignore")
            price = m.get("ltp")
            vol = _tick_session_volume(m)
            if sym is None or (isinstance(sym, str) and not sym.strip()) or price is None:
                return
            try:
                fp = float(price)
            except (TypeError, ValueError):
                return
            if not getattr(self, "_logged_first_tick", False):
                logger.info("First live tick received: symbol=%r ltp=%s", sym, fp)
                self._logged_first_tick = True
            self._last_tick_seen_ts = time.time()
            idx = self._resolve_tick_idx(sym)
            if idx is None:
                missed = getattr(self, "_tick_unresolved", 0)
                self._tick_unresolved = missed + 1
                if missed < 5:
                    logger.warning("Tick dropped — could not map symbol %r (check idx_map vs Fyers)", sym)
                return
            n_sym, n_math = len(self.symbols), self.math.n
            if idx < 0 or idx >= n_sym or idx >= n_math:
                if getattr(self, "_tick_idx_bad_logged", 0) < 3:
                    logger.warning(
                        "on_tick idx out of range: idx=%s n_sym=%s n_math=%s sym=%r",
                        idx, n_sym, n_math, sym,
                    )
                    self._tick_idx_bad_logged = getattr(self, "_tick_idx_bad_logged", 0) + 1
                return
            canon_sym = self.symbols[idx]
            pcp = m.get("prev_close_price")
            try:
                self.math.update_tick(canon_sym, fp, vol, prev_close=pcp)
            except Exception:
                pass
            if vol > 0:
                try:
                    self.math.day_vol[idx] = float(vol)
                except Exception:
                    pass
            target = self.shm.arr[idx]
            target["ltp"] = fp
            target["heartbeat"] = time.time()
            try:
                # Prefer broker CHG% (fyers_apiv3 adds chp when prev_close_price + ltp exist). Matrix [-2] is
                # often wrong or zero when daily parquet is short — that forced change_pct=0 → grey PRICE/CHG.
                ch = None
                if m.get("chp") is not None:
                    try:
                        v = float(m["chp"])
                        if np.isfinite(v):
                            ch = v
                    except (TypeError, ValueError):
                        pass
                if ch is None:
                    try:
                        pcp_f = float(pcp) if pcp is not None else 0.0
                    except (TypeError, ValueError):
                        pcp_f = 0.0
                    if pcp_f > 0:
                        ch = (fp - pcp_f) / pcp_f * 100.0
                    else:
                        prev = float(self.math.prev_close_day[idx])
                        if prev <= 0:
                            prev = float(self.math.price_matrix_d[idx, -2])
                        ch = ((fp - prev) / prev * 100.0) if prev > 0 else 0.0
                target["change_pct"] = float(ch)
                target["price_up"] = 1 if ch > 0 else 0
                target["price_down"] = 1 if ch < 0 else 0
            except Exception:
                pass

            try:
                self._maybe_roll_new_trading_day_ist()
                self._refresh_mrs_prev_day_cache()
                full_sym = target["symbol"].decode("utf-8", errors="ignore").strip("\x00").strip()
                prev_mrs = float(target["mrs"])
                instant_mrs = self.math.get_instant_mrs(canon_sym, fp)
                mpd = self._mrs_prev_day_cache.get(full_sym)
                target["status"] = self._compute_grid_status(full_sym, prev_mrs, instant_mrs, mpd)
                target["mrs"] = instant_mrs
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
                target["rv"] = float(self.math.compute_rvol(idx))
            except Exception:
                pass
        except Exception:
            pass

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
