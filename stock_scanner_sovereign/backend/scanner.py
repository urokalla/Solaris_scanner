import time, threading, ssl, os, logging, traceback, json, re, csv, datetime as dt
from typing import Optional
import logging.handlers
import numpy as np
from pathlib import Path
from fyers_apiv3.FyersWebsocket import data_ws
from fyers_apiv3 import fyersModel
from backend.database import DatabaseManager, _is_deadlock_exception, acquire_live_state_xact_lock
from backend.scanner_shm import SHMBridge
from backend.scanner_math import RSMathEngine
from utils.scanner_analysis import compute_trading_profile, profile_label_to_shm
from utils.constants import BENCHMARK_MAP
from utils.mrs_weekly_dynamics import weekly_mrs_trailing_series, weeks_since_last_mrs_zero_cross_up
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


def _dashboard_sym_key(sym: str) -> str:
    """Normalize `NSE:FOO-EQ`-style symbols to match `screener_eps_snapshot.csv` / A/D CSV keys."""
    t = str(sym or "").upper().strip()
    if ":" in t:
        t = t.split(":", 1)[1]
    t = t.replace("-INDEX", "")
    if "-" in t:
        t = t.rsplit("-", 1)[0]
    return re.sub(r"[^A-Z0-9]", "", t)


def _patch_fyers_ws_safe_send():
    """
    fyers_apiv3 queues outbound frames in __process_message_queue, but __send_message only checks
    that __ws_object is non-None — not that the TCP/WebSocket session is still open. A close
    race raises WebSocketConnectionClosedException and kills the queue thread until process restart.
    """
    try:
        from websocket._exceptions import WebSocketConnectionClosedException
    except ImportError:
        try:
            from websocket import WebSocketConnectionClosedException  # type: ignore
        except ImportError:
            logger.warning("websocket-client exception types not found; Fyers send-patch skipped.")
            return
    cls = data_ws.FyersDataSocket
    if getattr(cls, "_sovereign_safe_send_patched", False):
        return
    orig = getattr(cls, "_FyersDataSocket__send_message", None)
    if not callable(orig):
        logger.warning("FyersDataSocket.__send_message not found; send-patch skipped.")
        return

    def safe_send(self, message):
        try:
            return orig(self, message)
        except WebSocketConnectionClosedException:
            logger.warning(
                "Fyers WS: dropped outbound message — connection already closed "
                "(SDK thread race). Scanner replay / reconnect will recover."
            )
        except BrokenPipeError:
            logger.warning("Fyers WS: dropped outbound message — broken pipe.")

    setattr(cls, "_FyersDataSocket__send_message", safe_send)
    cls._sovereign_safe_send_patched = True
    logger.info("Applied FyersDataSocket closed-socket send guard (queue thread safety).")


_patch_fyers_ws_safe_send()


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


def _tick_ltp_from_message(m: dict) -> Optional[float]:
    """
    Best-effort last price from a Fyers tick dict.
    SymbolUpdate / v3 samples often use ``ltp``; other paths use ``lp`` (see scanner_msg legacy).
    """
    if not isinstance(m, dict):
        return None
    for k in ("ltp", "lp", "last_price"):
        v = m.get(k)
        if v is None:
            continue
        try:
            fv = float(v)
            if np.isfinite(fv) and fv > 0:
                return fv
        except (TypeError, ValueError):
            continue
    return None


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
        from utils.symbols import get_nifty_symbols # Added import
        self.db, self.shm = DatabaseManager(), SHMBridge()
        try:
            self.db.ensure_live_state_brk_column()
            self.db.ensure_mrs_prev_day_column()
            self.db.ensure_live_state_mrs_0_cross_unix_column()
            self.db.ensure_rs_prev_day_column()
            self.db.ensure_w_rsi2_column()
        except Exception as e:
            logger.warning("ensure_live_state_brk_column / mrs_prev_day / rs_prev_day / w_rsi2: %s", e)
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
                
                # Step 2: Synchronized Universe — never truncate index benchmarks (sorted [:5000] alone
                # drops NIFTY50/NIFTY500 etc. when thousands of EQ names sort earlier alphabetically).
                _bset = set(BENCHMARK_MAP.values())
                _bench_first = sorted(_bset & raw_symbols_set)
                _rest = sorted(raw_symbols_set - set(_bench_first))
                _cap = 5000
                _room = max(0, _cap - len(_bench_first))
                self.symbols = _bench_first + _rest[:_room]
                logger.info(
                    f"🌌 [Master] Architecture LOAD: {len(self.symbols)} securities synchronized "
                    f"(benchmark indices reserved: {len(_bench_first)})."
                )
                
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
        if self.math.bench_sym not in self.symbols:
            logger.error(
                "Benchmark %s is missing from the master symbol list — live RS and header index ticks will fail. "
                "Increase FYERS cap or check DB/benchmark merge.",
                self.math.bench_sym,
            )
        self.last_flush = 0
        self.ws = None
        # Master-only: session BUY NOW latch + prior-day mRS cache (dashboard reads SHM written by master)
        self._buy_session_latch: set[str] = set()
        # Last time weekly mRS crossed above 0 (master runtime + live_state.mrs_0_cross_unix for dashboard).
        self._mrs_zero_cross_up_ts: dict[str, float] = {}
        self._last_ist_trading_date = None
        self._mrs_prev_day_cache: dict[str, float] = {}
        self._mrs_prev_day_cache_ts: float = 0.0
        self._eod_snapshot_done_date = None
        self._last_health_log_ts: float = 0.0
        self._last_tick_seen_ts: float = 0.0
        self._last_targeted_resub_ts: float = 0.0
        self._last_stale_resub_ts: float = 0.0
        # Weekly RSI(2) for main dashboard (Parquet + optional LTP blend → live_state.w_rsi2).
        self._w_rsi2_ts: float = 0.0
        self._w_rsi2_thread: Optional[threading.Thread] = None
        self._pipeline_bridge = None
        # A/D snapshot cache (offline script output: data/ad_proxy_snapshot.csv)
        self._ad_cache_ts: float = 0.0
        self._ad_cache_mtime: float = 0.0
        self._ad_map: dict[str, tuple[str, float]] = {}
        self._eps_ca_cache_ts: float = 0.0
        self._eps_ca_cache_mtime: float = 0.0
        # Screener nk -> (C quarterly YoY pass, A annual YoY pass)
        self._eps_ca_map: dict[str, tuple[bool, bool]] = {}
        self._ann_cache_ts: float = 0.0
        self._ann_cache_mtime: float = 0.0
        self._ann_map: dict[str, tuple[str, str]] = {}
        # Short-lived UI DB merge cache (avoids repeated identical live_state queries every poll).
        self._ui_db_cache_ttl_sec: float = max(1.0, float(os.getenv("UI_DB_CACHE_TTL_SEC", "5")))
        self._ui_db_cache = {
            "brk": {"ts": 0.0, "key": None, "val": {}},
            "mrs_prev": {"ts": 0.0, "key": None, "val": {}},
            "rs_prev": {"ts": 0.0, "key": None, "val": {}},
            "w_rsi2": {"ts": 0.0, "key": None, "val": {}},
        }
        # Per-symbol stale resub cooldown to avoid hammering the same illiquid names.
        self._stale_resub_sym_ts: dict[str, float] = {}
        # Last successful full WS subscribe list (Fyers SDK clears symbol_token on reconnect without resubscribing).
        self._ws_full_subscribe_targets: Optional[list[str]] = None
        self._last_full_ws_replay_ts: float = 0.0
        self._invalid_ws_symbols_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "fyers_invalid_symbols.json")
        )
        self._unresolved_ws_symbols_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "fyers_unresolved_symbols.json")
        )
        self._invalid_ws_symbols: set[str] = set()
        self._load_invalid_ws_symbols()
        # Slave dashboard: baseline runs in a daemon thread. If that thread exits, engine.get_scanner()
        # respawns MasterScanner with empty math — only file-based merges (e.g. A/D) would work.
        self._slave_math_ready = threading.Event()
        if is_master:
            self._slave_math_ready.set()

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
            if not tok_map:
                # Empty map after SDK reconnect: `if resolved` was falsy so we used [] and never resubscribed.
                unresolved = list(target)
            else:
                resolved = self._resolved_symbols_from_token_map(tok_map)
                unresolved = [s for s in target if str(s).upper() not in resolved]
            # Token-map shape/SDK quirks can miss symbols that are already ticking; re-subscribing
            # those causes unnecessary churn and can destabilize the session.
            hb_grace = float(os.getenv("FYERS_WS_TARGETED_SKIP_IF_HB_SEC", "90"))
            if tok_map and unresolved and hb_grace > 0:
                filtered = []
                for s in unresolved:
                    idx = self._resolve_tick_idx(s)
                    if idx is None:
                        filtered.append(s)
                        continue
                    try:
                        hb = float(self.shm.arr[idx]["heartbeat"])
                    except Exception:
                        hb = 0.0
                    if hb > 0 and (now - hb) <= hb_grace:
                        continue
                    filtered.append(s)
                unresolved = filtered
            self._save_unresolved_ws_symbols(unresolved, len(tok_map), expect)
            if not unresolved:
                return

            if not tok_map:
                batch = max(50, min(500, int(os.getenv("FYERS_WS_SUB_BATCH", "200"))))
                retry_syms = unresolved
                logger.warning(
                    "🛟 [Resub] symbol_token empty — replaying full subscribe (%s symbols, batch=%s)",
                    len(retry_syms),
                    batch,
                )
            else:
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

    def _maybe_resubscribe_stale_symbols(self):
        """
        Fyers can stop delivering ticks for symbols that still appear in symbol_token.
        Re-issue subscribe() for SHM rows whose heartbeat is very stale while the socket
        is still receiving some ticks (active session).
        """
        try:
            if self.ws is None or not self.ws.is_connected():
                return
            if os.getenv("FYERS_WS_STALE_RESUB_ENABLE", "true").lower() not in ("1", "true", "yes"):
                return
            now = time.time()
            cooldown = float(os.getenv("FYERS_WS_STALE_RESUB_COOLDOWN_SEC", "180"))
            if (now - self._last_stale_resub_ts) < cooldown:
                return
            feed_fresh = float(os.getenv("FYERS_WS_STALE_RESUB_FEED_FRESH_SEC", "120"))
            if self._last_tick_seen_ts <= 0 or (now - self._last_tick_seen_ts) > feed_fresh:
                return
            base_stale = float(os.getenv("SCANNER_STALE_HEARTBEAT_SEC", "120"))
            # Illiquid names often go many minutes without a trade; default well above that so we
            # only resubscribe when a stream likely dropped, not when the stock is quiet.
            _default_min = max(480.0, base_stale * 3.0, base_stale + 300.0)
            min_stale = float(os.getenv("FYERS_WS_STALE_RESUB_MIN_SEC", str(_default_min)))
            n_sym = min(len(self.symbols), len(self.shm.arr))
            if n_sym <= 0:
                return
            stale_idx = []
            for i in range(n_sym):
                try:
                    hb = float(self.shm.arr[i]["heartbeat"])
                except Exception:
                    hb = 0.0
                if hb <= 0 or (now - hb) > min_stale:
                    stale_idx.append(i)
            if not stale_idx:
                return
            # Avoid "subscription thrash": if a large portion of the universe is stale at once
            # (common when many symbols don't tick frequently), re-subscribing can disrupt
            # the feed without improving coverage.
            stale_ratio = float(len(stale_idx)) / float(max(n_sym, 1))
            max_ratio = float(os.getenv("FYERS_WS_STALE_RESUB_MAX_STALE_RATIO", "0.12"))
            if stale_ratio >= max_ratio:
                logger.info(
                    "⏸️ [ResubStale] Skip: too many stale symbols (stale=%s/%s ratio=%.2f >= %.2f)",
                    len(stale_idx),
                    n_sym,
                    stale_ratio,
                    max_ratio,
                )
                return
            self._load_invalid_ws_symbols()
            blocked = set(self._invalid_ws_symbols)
            tok_map = getattr(self.ws, "symbol_token", {}) or {}
            token_resolved = self._resolved_symbols_from_token_map(tok_map)
            sym_cooldown = float(os.getenv("FYERS_WS_STALE_RESUB_PER_SYMBOL_SEC", "900"))
            prune_before = now - max(sym_cooldown * 4.0, 3600.0)
            try:
                dead = {k for k, t in self._stale_resub_sym_ts.items() if t < prune_before}
                for k in dead:
                    self._stale_resub_sym_ts.pop(k, None)
            except Exception:
                pass
            _ws_dtype = os.getenv("FYERS_WS_DATA_TYPE", "SymbolUpdate")
            fyers_syms: list[str] = []
            for i in stale_idx:
                s = self.symbols[i]
                fy = self._to_fyers_symbol(f"NSE:{s}-EQ" if ":" not in str(s) else s)
                fyu = str(fy).upper()
                if fyu in blocked:
                    continue
                # Quiet stocks: no token row and stale HB — ok to try subscribe. If we have a token
                # but no ticks, only resub after per-symbol cooldown (likely illiquid otherwise).
                if token_resolved and fyu in token_resolved and sym_cooldown > 0:
                    last = float(self._stale_resub_sym_ts.get(fyu, 0.0))
                    if last > 0 and (now - last) < sym_cooldown:
                        continue
                fyers_syms.append(fy)
            if not fyers_syms:
                return
            # Dedupe preserve order
            seen: set[str] = set()
            deduped = []
            for x in fyers_syms:
                u = str(x).upper()
                if u not in seen:
                    seen.add(u)
                    deduped.append(x)
            cap = max(10, min(500, int(os.getenv("FYERS_WS_STALE_RESUB_MAX", "80"))))
            to_sub = deduped[:cap]
            batch = max(10, min(80, int(os.getenv("FYERS_WS_STALE_RESUB_BATCH", "40"))))
            bsleep = float(os.getenv("FYERS_WS_STALE_RESUB_BATCH_SLEEP", "0.25"))
            self._last_stale_resub_ts = now
            for j in range(0, len(to_sub), batch):
                b = to_sub[j : j + batch]
                try:
                    self.ws.subscribe(symbols=b, data_type=_ws_dtype)
                except Exception:
                    pass
                for _s in b:
                    self._stale_resub_sym_ts[str(_s).upper()] = now
                time.sleep(bsleep)
            logger.info(
                "🔁 [ResubStale] Re-subscribed %s/%s symbols with heartbeat > %.0fs (feed fresh < %.0fs)",
                len(to_sub),
                len(deduped),
                min_stale,
                feed_fresh,
            )
        except Exception as e:
            logger.debug("Stale resubscribe skipped: %s", e)

    def _maybe_recover_dead_subscription_map(self):
        """
        fyers_apiv3 clears ``symbol_token`` on reconnect but does not call ``subscribe`` again.
        ``is_connected()`` only checks ``__ws_object`` is non-None, so TickHealth can show tokens=0
        with no ticks until we replay subscriptions.
        """
        try:
            if self.ws is None or not self.ws.is_connected():
                return
            tok_map = getattr(self.ws, "symbol_token", None)
            if not tok_map:
                tok_map = {}
            if len(tok_map) > 0:
                return
            now = time.time()
            cooldown = float(os.getenv("FYERS_WS_EMPTY_TOKEN_REPLAY_SEC", "30"))
            if (now - self._last_full_ws_replay_ts) < cooldown:
                return
            targets = self._ws_full_subscribe_targets
            if not targets:
                targets = self._current_ws_target_symbols()
            if not targets:
                return
            self._last_full_ws_replay_ts = now
            _ws_dtype = os.getenv("FYERS_WS_DATA_TYPE", "SymbolUpdate")
            _batch = max(50, min(500, int(os.getenv("FYERS_WS_SUB_BATCH", "200"))))
            _sub_sleep = float(os.getenv("FYERS_WS_SUB_BATCH_SLEEP_SEC", "0.80"))
            logger.error(
                "🔴 [WS] symbol_token empty while socket open — replaying %s subscriptions "
                "(Fyers SDK clears token map on reconnect without auto-resubscribe).",
                len(targets),
            )
            for i in range(0, len(targets), _batch):
                b = targets[i : i + _batch]
                try:
                    self.ws.subscribe(symbols=b, data_type=_ws_dtype)
                except Exception as ex:
                    logger.warning("Empty-token replay batch %s-%s failed: %s", i, i + len(b), ex)
                time.sleep(_sub_sleep)
        except Exception as e:
            logger.debug("Dead subscription map recovery skipped: %s", e)

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
            self.db.snapshot_rs_prev_day_from_current_rs()
            self._eod_snapshot_done_date = d
        except Exception:
            pass

    def _pipeline_bridge_lazy(self):
        if self._pipeline_bridge is None:
            from utils.pipeline_bridge import PipelineBridge

            self._pipeline_bridge = PipelineBridge()
        return self._pipeline_bridge

    def _get_ad_snapshot_map(self) -> dict[str, tuple[str, float]]:
        """
        Load cached A/D snapshot map from data/ad_proxy_snapshot.csv.
        Returns: symbol -> (grade, ratio)
        """
        now = time.time()
        if (now - self._ad_cache_ts) < 30.0 and self._ad_map:
            return self._ad_map
        self._ad_cache_ts = now

        try:
            root = Path(__file__).resolve()
            candidates = [root.parents[2] / "data", root.parents[1] / "data"]
            csv_path = None
            for base in candidates:
                p = (base / "ad_proxy_snapshot.csv").resolve()
                if p.exists():
                    csv_path = p
                    break
            if csv_path is None:
                return self._ad_map

            mtime = float(csv_path.stat().st_mtime)
            if self._ad_map and mtime == self._ad_cache_mtime:
                return self._ad_map
            self._ad_cache_mtime = mtime

            out: dict[str, tuple[str, float]] = {}
            with csv_path.open("r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    sym = str(row.get("symbol") or "").strip()
                    if not sym:
                        continue
                    g = str(row.get("ad_grade") or "").strip().upper()
                    if g not in ("A", "B", "C", "D", "E"):
                        g = "—"
                    try:
                        r = float(str(row.get("ad_ratio") or "0").strip())
                    except ValueError:
                        r = 0.0
                    out[sym] = (g, r)
            self._ad_map = out
            return self._ad_map
        except Exception as ex:
            logger.debug("A/D snapshot load skipped: %s", ex)
            return self._ad_map

    @staticmethod
    def _parse_screener_yoy_pct(raw) -> Optional[float]:
        if raw is None or str(raw).strip() == "":
            return None
        try:
            v = float(str(raw).strip())
        except ValueError:
            return None
        return v if np.isfinite(v) else None

    def _get_screener_eps_canslim_ca_map(self) -> dict[str, tuple[bool, bool]]:
        """
        CANSLIM **C** (current quarter EPS YoY) and **A** (annual EPS YoY) as separate gates
        from `data/screener_eps_snapshot.csv`. No OR shortcut: each must meet the threshold on
        its own field when `fetch_status == ok`.
        """
        now = time.time()
        if (now - self._eps_ca_cache_ts) < 30.0 and self._eps_ca_map:
            return self._eps_ca_map
        self._eps_ca_cache_ts = now
        thr = float(os.getenv("CANSLIM_EPS_YOY_MIN", "25"))
        try:
            root = Path(__file__).resolve()
            candidates = [root.parents[2] / "data", root.parents[1] / "data"]
            csv_path = None
            for base in candidates:
                p = (base / "screener_eps_snapshot.csv").resolve()
                if p.exists():
                    csv_path = p
                    break
            if csv_path is None:
                return self._eps_ca_map

            mtime = float(csv_path.stat().st_mtime)
            if self._eps_ca_map and mtime == self._eps_ca_cache_mtime:
                return self._eps_ca_map
            self._eps_ca_cache_mtime = mtime

            out: dict[str, tuple[bool, bool]] = {}
            with csv_path.open("r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    nk = _dashboard_sym_key(str(row.get("symbol") or ""))
                    if not nk:
                        continue
                    if str(row.get("fetch_status") or "").strip().lower() != "ok":
                        out[nk] = (False, False)
                        continue
                    qv = self._parse_screener_yoy_pct(row.get("q_eps_yoy_pct"))
                    av = self._parse_screener_yoy_pct(row.get("a_eps_yoy_pct"))
                    c_ok = qv is not None and qv >= thr
                    a_ok = av is not None and av >= thr
                    out[nk] = (c_ok, a_ok)
            self._eps_ca_map = out
            return self._eps_ca_map
        except Exception as ex:
            logger.debug("EPS CANSLIM snapshot load skipped: %s", ex)
            return self._eps_ca_map

    def _get_recent_announcements_map(self) -> dict[str, tuple[str, str]]:
        """
        Load announcements CSV and keep only recent rows for quick main-grid action flag.
        Returns: symbol -> (an_dt, desc)
        """
        now = time.time()
        if (now - self._ann_cache_ts) < 30.0 and self._ann_map:
            return self._ann_map
        self._ann_cache_ts = now
        try:
            root = Path(__file__).resolve()
            candidates = [root.parents[2] / "data", root.parents[1] / "data"]
            csv_path = None
            for base in candidates:
                p = (base / "nse_corporate_announcements.csv").resolve()
                if p.exists():
                    csv_path = p
                    break
            if csv_path is None:
                return self._ann_map
            mtime = float(csv_path.stat().st_mtime)
            if self._ann_map and mtime == self._ann_cache_mtime:
                return self._ann_map
            self._ann_cache_mtime = mtime

            def _pdt(s: str) -> dt.datetime:
                x = (s or "").strip()
                if not x:
                    return dt.datetime.min
                for fmt in (
                    "%d-%b-%Y %H:%M:%S",
                    "%d-%b-%Y %H:%M",
                    "%d-%b-%Y",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%d",
                ):
                    try:
                        return dt.datetime.strptime(x, fmt)
                    except ValueError:
                        pass
                return dt.datetime.min

            cutoff = dt.datetime.now() - dt.timedelta(days=3)
            out: dict[str, tuple[str, str]] = {}
            with csv_path.open("r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    sym = str(row.get("symbol") or "").strip().upper()
                    if not sym:
                        continue
                    an_dt = str(row.get("an_dt") or "").strip()
                    desc = str(row.get("desc") or "").strip()
                    when = _pdt(an_dt)
                    if when < cutoff:
                        continue
                    prev = out.get(sym)
                    if prev is None or _pdt(prev[0]) < when:
                        out[sym] = (an_dt, desc)
            self._ann_map = out
            return self._ann_map
        except Exception as ex:
            logger.debug("Announcement map load skipped: %s", ex)
            return self._ann_map

    def _maybe_refresh_w_rsi2_background(self):
        from config.settings import settings

        if not getattr(settings, "DASHBOARD_W_RSI2", True):
            return
        if os.getenv("SHM_MASTER", "true").lower() != "true":
            return
        interval = float(getattr(settings, "DASHBOARD_W_RSI2_REFRESH_SEC", 180))
        thr = getattr(self, "_w_rsi2_thread", None)
        if thr is not None and thr.is_alive():
            return
        now = time.time()
        if self._w_rsi2_ts > 0 and (now - self._w_rsi2_ts) < interval:
            return
        self._w_rsi2_ts = now
        self._w_rsi2_thread = threading.Thread(
            target=self._w_rsi2_refresh_worker,
            daemon=True,
            name="dashboard-w-rsi2",
        )
        self._w_rsi2_thread.start()

    def _w_rsi2_refresh_worker(self):
        from config.settings import settings
        from utils.monthly_rsi2_trade_rules import (
            blend_last_daily_bar_with_ltp,
            daily_close_series_from_ohlcv,
            latest_weekly_rsi2,
            sidecar_live_rsi2_window_ok,
        )

        try:
            live_ok = sidecar_live_rsi2_window_ok(
                hour=settings.DASHBOARD_W_RSI2_LIVE_IST_HOUR,
                minute=settings.DASHBOARD_W_RSI2_LIVE_IST_MINUTE,
            )
            rows: list[tuple[str, float]] = []
            bridge = self._pipeline_bridge_lazy()
            for sym in self.symbols:
                if not str(sym).endswith("-EQ"):
                    continue
                try:
                    d_hist = bridge.get_historical_data(sym, limit=800)
                    if d_hist is None or len(d_hist) < 80:
                        d_hist = self.db.get_historical_data(sym, "1d", limit=800)
                    if d_hist is None or len(d_hist) < 80:
                        continue
                    base = daily_close_series_from_ohlcv(np.asarray(d_hist))
                    if base is None:
                        continue
                    lp = 0.0
                    idx = self.sym_to_idx.get(sym)
                    if idx is not None and 0 <= idx < len(self.shm.arr):
                        lp = float(self.shm.arr[idx]["ltp"])
                    series = base
                    if live_ok and lp > 0:
                        series = blend_last_daily_bar_with_ltp(base, lp)
                    lr = latest_weekly_rsi2(series, period=2)
                    if lr:
                        rows.append((sym, float(lr[1])))
                except Exception:
                    continue
            if rows:
                self.db.upsert_w_rsi2(rows)
                logger.info("📊 [Dashboard] w_rsi2 updated for %s symbols", len(rows))
        except Exception:
            logger.exception("w_rsi2 refresh worker failed")
        finally:
            self._w_rsi2_ts = time.time()

    def _persist_mrs_0_cross_unix(self, sym: str, ts: float) -> None:
        """Dashboard runs SHM_SLAVE — only the master scanner should write cross timestamps to Postgres."""
        if not getattr(self.shm, "is_master", False):
            return
        try:
            self.db.upsert_mrs_0_cross_unix(sym, ts)
        except Exception as ex:
            logger.warning("mrs_0_cross_unix persist failed for %s: %s", sym, ex)

    def _batch_fill_mrs_0_cross_unix_from_weekly_history(self) -> None:
        """
        TRENDING rows rarely hit the tick latch, so live_state stayed NULL and RS_0_CROSS_AGE was all dashes.
        Approximate last weekly mRS>0 cross from the same trailing window as Mansfield math; only fills NULL.
        """
        if not getattr(self.shm, "is_master", False):
            return
        try:
            pm = getattr(self.math, "price_matrix_w", None)
            br = getattr(self.math, "bench_prices_w", None)
            if pm is None or br is None or not hasattr(pm, "shape") or pm.ndim != 2 or br.ndim != 1:
                return
            H = int(pm.shape[1])
            if H < 3:
                return
            K = max(3, min(52, H - 1))
            Y = weekly_mrs_trailing_series(pm, br, K)
            wk = weeks_since_last_mrs_zero_cross_up(Y)
            now_t = time.time()
            n = min(int(pm.shape[0]), len(self.symbols), int(wk.shape[0]))
            rows: list[tuple[str, float]] = []
            for i in range(n):
                w = int(wk[i])
                if w < 0:
                    continue
                rows.append((self.symbols[i], now_t - float(w) * 7.0 * 86400.0))
            if rows:
                self.db.upsert_mrs_0_cross_unix_fill_if_null_batch(rows)
        except Exception as ex:
            logger.warning("batch mrs_0_cross_unix fill from history failed: %s", ex, exc_info=True)

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
            _ts = time.time()
            self._mrs_zero_cross_up_ts[sym] = _ts
            self._persist_mrs_0_cross_unix(sym, _ts)
            self._buy_session_latch.add(sym)
            return b"BUY NOW"
        if mrs_prev_day is not None and mrs_prev_day > 0:
            return b"TRENDING"
        if mrs_prev_day is not None and mrs_prev_day <= 0:
            _ts = time.time()
            self._mrs_zero_cross_up_ts[sym] = _ts
            self._persist_mrs_0_cross_unix(sym, _ts)
            self._buy_session_latch.add(sym)
            return b"BUY NOW"
        return b"TRENDING"

    def _universe_row_index_for_benchmark(self, b_sym: str) -> Optional[int]:
        """
        Index of ``b_sym`` in ``self.symbols`` for mirroring into BENCH_SLOTS.

        Prefer exact / Fyers-canonical keys so we never match a stock row via \"naked\" collapse
        (e.g. NIFTY50 vs an unrelated ticker) when building the 9001+ mirror slots.
        """
        k = str(b_sym).strip()
        idx = self.sym_to_idx.get(k)
        if idx is not None:
            return idx
        fy = self._to_fyers_symbol(k)
        idx = self.sym_to_idx.get(fy)
        if idx is not None:
            return idx
        nk = (
            k.replace("NSE:", "")
            .replace("-INDEX", "")
            .replace("_", "")
            .replace("-", "")
            .upper()
        )
        hits: list[int] = []
        for i, s in enumerate(self.symbols):
            sn = (
                str(s)
                .replace("NSE:", "")
                .replace("-INDEX", "")
                .replace("_", "")
                .replace("-", "")
                .upper()
            )
            if sn == nk:
                hits.append(i)
        if not hits:
            return None
        if len(hits) == 1:
            return hits[0]
        for i in hits:
            if str(self.symbols[i]).upper().endswith("-INDEX"):
                return i
        sample = ", ".join(str(self.symbols[i]) for i in hits[:6])
        logger.warning(
            "Ambiguous benchmark naked-key %r for %s — multiple rows [%s]; using first hit %s",
            nk,
            b_sym,
            sample,
            self.symbols[hits[0]],
        )
        return hits[0]

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
            try:
                hist_root = os.getenv("PIPELINE_DATA_DIR", "/app/data/historical")
                self.math.load_historical_baseline(data_root=hist_root)
            except Exception as ex:
                logger.warning("Slave baseline load failed — CANSLIM L/M/N need Parquet at PIPELINE_DATA_DIR: %s", ex)
            finally:
                self._slave_math_ready.set()
            # Keep daemon thread alive so frontend engine does not create a fresh empty scanner every poll.
            while True:
                time.sleep(3600.0)

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
            logger.debug("📊 UI Request -> Page: %s, Size: %s, Filters: %s", page, page_size, filters)
            if not self._slave_math_ready.is_set():
                self._slave_math_ready.wait(timeout=180.0)

            # Step 1: Universal Load (Trust the Index Map before filtering)
            valid_symbols = set(self.symbols)
            
            # Step 2: Specific Filtering (Universal Optimization)
            univ = filters.get("universe", "Nifty 500")
            if univ != "All Securities" and univ != getattr(self, '_last_u_name', None):
                from utils.symbols import get_nifty_symbols
                raw_u = get_nifty_symbols(univ)
                if raw_u:
                    # Universe CSVs can contain bare symbols while master symbols may carry
                    # different series suffixes (-EQ/-SM/-ST/-BE). Build cache by naked-key
                    # alignment against current scanner symbols so UI rows do not disappear.
                    def _nk(x: str) -> str:
                        t = str(x or "").upper().strip()
                        if ":" in t:
                            t = t.split(":", 1)[1]
                        t = t.replace("-INDEX", "")
                        if "-" in t:
                            t = t.rsplit("-", 1)[0]
                        return t.replace("_", "").replace("-", "")

                    by_nk: dict[str, list[str]] = {}
                    for ss in self.symbols:
                        by_nk.setdefault(_nk(ss), []).append(ss)

                    resolved: set[str] = set()
                    for r in raw_u:
                        key = _nk(r)
                        hits = by_nk.get(key)
                        if hits:
                            for h in hits:
                                resolved.add(h)
                        else:
                            rs = str(r)
                            if ":" in rs:
                                resolved.add(rs)
                            else:
                                # Fallback candidate when the symbol is not currently loaded.
                                resolved.add(f"NSE:{rs}-EQ")
                    self._valid_symbols_cache = resolved
                    self._last_u_name = univ

            valid_symbols = getattr(self, '_valid_symbols_cache', set(self.symbols))

            sector = filters.get("sector", "(All)")
            s_lab = str(sector or "").strip()
            if s_lab and s_lab.upper() not in ("(ALL)", "ALL"):
                from utils.screener_market_symbols import symbol_nks_for_dashboard_sector

                snks = symbol_nks_for_dashboard_sector(s_lab)
                if snks:

                    def _nk_sect(x: str) -> str:
                        t = str(x or "").upper().strip()
                        if ":" in t:
                            t = t.split(":", 1)[1]
                        t = t.replace("-INDEX", "")
                        if "-" in t:
                            t = t.rsplit("-", 1)[0]
                        import re as _re

                        return _re.sub(r"[^A-Z0-9]", "", t)

                    valid_symbols = {s for s in valid_symbols if _nk_sect(s) in snks}
            
            # Step 3: O(1) Memory Extraction + Dashboard Filtering
            # Iterate canonical symbol indices only — NOT full shm.arr (10k rows). Scanning all rows
            # can duplicate tickers (e.g. benchmark mirror slots 9001+ vs primary index row), so one
            # symbol could appear twice with different LTP/heartbeat and "fixing" one row broke another.
            data = []
            search_val = filters.get("search")
            search_q = str(search_val).upper().strip() if search_val else ""
            status_f = str(filters.get("status", "ALL")).upper()
            profile_f = str(filters.get("profile", "ALL")).upper()
            mrs_min_f = str(filters.get("mrs_min", "ALL")).upper()
            rv_min_f = str(filters.get("rv_min", "ALL")).upper()
            n_sym = len(self.symbols)
            # Pull numpy views once per request; avoid repeated getattr inside the tight row loop.
            _s4 = getattr(self.math, "mrs_w_slope_4w", None)
            _ms = getattr(self.math, "mrs_mansfield_slope", None)
            _rc = getattr(self.math, "mrs_w_belowzero_rising", None)
            _rc_l = getattr(self.math, "mrs_w_belowzero_rising_latched", None)
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

                mrs_v = float(r["mrs"])
                if mrs_min_f != "ALL":
                    try:
                        if mrs_v < float(mrs_min_f):
                            continue
                    except ValueError:
                        pass
                rv_v = float(r["rv"])
                if rv_min_f != "ALL":
                    try:
                        if rv_v < float(rv_min_f):
                            continue
                    except ValueError:
                        pass

                ch_pct = float(r["change_pct"])
                if not np.isfinite(ch_pct):
                    ch_pct = 0.0
                slope4 = float(_s4[i]) if _s4 is not None and i < len(_s4) else 0.0
                m_slope = float(_ms[i]) if _ms is not None and i < len(_ms) else 0.0
                if _rc_l is not None and i < len(_rc_l):
                    mrs_rcvr = bool(_rc_l[i])
                else:
                    mrs_rcvr = bool(_rc[i]) if _rc is not None and i < len(_rc) else False
                data.append({
                    "symbol": sym,
                    "ltp": float(r['ltp']),
                    "p1d": f"{ch_pct:.2f}%",
                    "ch_pct": ch_pct,
                    "chg_up": ch_pct > 0,
                    "chg_down": ch_pct < 0,
                    "mrs": mrs_v,
                    "mrs_str": f"{mrs_v:.2f}",
                    "mrs_prev": float(r['mrs_prev']),
                    "mrs_up": bool(mrs_v >= 0),
                    "mrs_daily": float(r['mrs_daily']),
                    "mrs_daily_str": f"{r['mrs_daily']:+.2f}",
                    "mrs_daily_up": bool(r['mrs_daily'] >= 0),
                    "rs_rating": int(r['rs_rating']),
                    "rs_prev_day": None,
                    "rs_delta": None,
                    "rs_delta_str": "—",
                    "rs_delta_up": False,
                    "rs_delta_down": False,
                    "status": st,
                    "profile": pf if pf.strip() else "—",
                    "rv": f"{rv_v:.2f}x",
                    "rv_num": rv_v,
                    "price_up": bool(r['price_up']),
                    "price_down": bool(r['price_down']),
                    # UI: high RVOL on a down day must not use "up" green (rv_up was only rv>=1.5, so it won rv_down).
                    "rv_up": bool(rv_v >= 1.5 and ch_pct > 0),
                    "rv_down": bool(rv_v >= 1.5 and ch_pct < 0),
                    "mrs_slope_4w": slope4,
                    "mrs_mansfield_slope": m_slope,
                    "mrs_rcvr": mrs_rcvr,
                    "mrs_rcvr_str": "↑<0" if mrs_rcvr else "—",
                    "ad_grade": "—",
                    "ad_ratio": 0.0,
                    "ann_has": False,
                    "ann_dt": "",
                    "ann_desc": "",
                    "canslim_score": 0,
                    "canslim_str": "0/6",
                    "canslim_icon": "○",
                    "canslim_tier": "Weak",
                    "canslim_cell": "○ 0/6 · Weak",
                    "canslim_band": "weak",
                    "canslim_tip": "",
                })

            rcvr_f = str(filters.get("mrs_rcvr", "ALL")).strip().upper()
            if rcvr_f in ("YES", "1", "TRUE", "ON", "BELOW0", "BELOW0_RISING"):
                data = [d for d in data if d.get("mrs_rcvr")]

            # Stable key for short-lived live_state merge caches across identical polls.
            syms = [d["symbol"] for d in data]
            cache_key = tuple(syms)
            now_ts = time.time()

            def _ui_cache_get(name: str):
                e = self._ui_db_cache.get(name) if hasattr(self, "_ui_db_cache") else None
                if not e:
                    return None
                if e.get("key") != cache_key:
                    return None
                if (now_ts - float(e.get("ts", 0.0))) > float(getattr(self, "_ui_db_cache_ttl_sec", 5.0)):
                    return None
                return e.get("val")

            def _ui_cache_set(name: str, value):
                if not hasattr(self, "_ui_db_cache"):
                    return
                self._ui_db_cache[name] = {"ts": now_ts, "key": cache_key, "val": value}

            zm = _ui_cache_get("mrs0cross")
            if zm is None:
                zm = self.db.get_mrs_0_cross_unix_map(syms) if syms else {}
                _ui_cache_set("mrs0cross", zm)

            for d in data:
                sym = str(d.get("symbol", ""))
                mem = float(self._mrs_zero_cross_up_ts.get(sym, 0.0) or 0.0)
                dbv = float(zm.get(sym, 0.0) or 0.0)
                ts = max(mem, dbv) if (mem > 0 or dbv > 0) else 0.0
                if ts <= 0:
                    d["zero_cross_age"] = "—"
                    d["zero_cross_age_days"] = None
                else:
                    days_f = max(0.0, (now_ts - ts) / 86400.0)
                    d["zero_cross_age_days"] = float(days_f)
                    days = int(days_f)
                    if days <= 0:
                        d["zero_cross_age"] = "0d"
                    elif days < 7:
                        d["zero_cross_age"] = f"{days}d"
                    else:
                        weeks = days // 7
                        if weeks < 5:
                            d["zero_cross_age"] = f"{weeks}w"
                        else:
                            d["zero_cross_age"] = f"{days}d"

            # Layer 3: pivot from live_state (written by BreakoutScanner / sidecar), not SHM dtype
            try:
                bm = _ui_cache_get("brk")
                if bm is None:
                    bm = self.db.get_brk_lvl_map(syms) if syms else {}
                    _ui_cache_set("brk", bm)
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
                pm = _ui_cache_get("mrs_prev")
                if pm is None:
                    pm = self.db.get_mrs_prev_day_map(syms) if syms else {}
                    _ui_cache_set("mrs_prev", pm)
                for d in data:
                    v = pm.get(d["symbol"])
                    d["mrs_prev_day"] = v
                    d["mrs_prev_day_str"] = f"{v:.2f}" if v is not None else "—"
            except Exception as ex:
                logger.warning("mrs_prev_day merge on main grid: %s", ex)
                for d in data:
                    d["mrs_prev_day"] = None
                    d["mrs_prev_day_str"] = "—"
            try:
                self.db.ensure_rs_prev_day_column()
                rm = _ui_cache_get("rs_prev")
                if rm is None:
                    rm = self.db.get_rs_prev_day_map(syms) if syms else {}
                    _ui_cache_set("rs_prev", rm)
                for d in data:
                    v = rm.get(d["symbol"])
                    d["rs_prev_day"] = v
                    if v is None:
                        d["rs_delta"] = None
                        d["rs_delta_str"] = "—"
                        d["rs_delta_up"] = False
                        d["rs_delta_down"] = False
                    else:
                        cur = int(d.get("rs_rating", 0))
                        delta = cur - int(v)
                        d["rs_delta"] = delta
                        d["rs_delta_str"] = f"{delta:+d}"
                        d["rs_delta_up"] = delta > 0
                        d["rs_delta_down"] = delta < 0
            except Exception as ex:
                logger.warning("rs_prev_day merge on main grid: %s", ex)
                for d in data:
                    d["rs_prev_day"] = None
                    d["rs_delta"] = None
                    d["rs_delta_str"] = "—"
                    d["rs_delta_up"] = False
                    d["rs_delta_down"] = False
            try:
                self.db.ensure_w_rsi2_column()
                wm = _ui_cache_get("w_rsi2")
                if wm is None:
                    wm = self.db.get_w_rsi2_map(syms) if syms else {}
                    _ui_cache_set("w_rsi2", wm)
                for d in data:
                    v = wm.get(d["symbol"])
                    d["w_rsi2"] = v
                    d["w_rsi2_str"] = f"{v:.1f}" if v is not None else "—"
            except Exception as ex:
                logger.warning("w_rsi2 merge on main grid: %s", ex)
                for d in data:
                    d["w_rsi2"] = None
                    d["w_rsi2_str"] = "—"
            try:
                ad_map = self._get_ad_snapshot_map()
                if ad_map:
                    for d in data:
                        sym = d["symbol"]
                        v = ad_map.get(sym)
                        if v is None:
                            v = ad_map.get(_dashboard_sym_key(sym))
                        if v is None:
                            continue
                        d["ad_grade"] = v[0]
                        d["ad_ratio"] = float(v[1])
            except Exception as ex:
                logger.debug("A/D merge on main grid skipped: %s", ex)
            canslim_on = os.getenv("CANSLIM_ENABLED", "1").strip().lower() in ("1", "true", "yes")
            if not canslim_on:
                for d in data:
                    d["canslim_score"] = 0
                    d["canslim_str"] = "0/6"
                    d["canslim_icon"] = "○"
                    d["canslim_tier"] = "Weak"
                    d["canslim_cell"] = "○ 0/6 · Weak"
                    d["canslim_band"] = "weak"
                    d["canslim_tip"] = ""
            else:
                try:
                    eps_ca = self._get_screener_eps_canslim_ca_map()
                    _lp = getattr(self.math, "canslim_l_pass", None)
                    _np = getattr(self.math, "canslim_n_pass", None)
                    _m_ok = bool(getattr(self.math, "canslim_m_ok", False))
                    for d in data:
                        sym = d["symbol"]
                        idx = self.sym_to_idx.get(sym)
                        sk = _dashboard_sym_key(sym)
                        pair = eps_ca.get(sk)
                        if pair is None:
                            c_ok, a_ok = False, False
                        else:
                            c_ok, a_ok = bool(pair[0]), bool(pair[1])
                        s_ok = str(d.get("ad_grade") or "").strip().upper() in ("A", "B")
                        l_ok = bool(_lp[idx]) if _lp is not None and idx is not None and 0 <= idx < len(_lp) else False
                        n_ok = bool(_np[idx]) if _np is not None and idx is not None and 0 <= idx < len(_np) else False
                        m_ok = _m_ok
                        score = int(c_ok) + int(a_ok) + int(s_ok) + int(l_ok) + int(m_ok) + int(n_ok)
                        br = []
                        for ok, lab in (
                            (c_ok, "C Q EPS+"),
                            (a_ok, "A ann EPS+"),
                            (s_ok, "S A/D"),
                            (l_ok, "L RS+mRS+chart"),
                            (m_ok, "M market"),
                            (n_ok, "N near high"),
                        ):
                            br.append(f"{lab}: {'ok' if ok else '—'}")
                        tip = "CANSLIM-style checklist (6) — not investment advice.\n" + " · ".join(br)
                        if score >= 6:
                            icon, tier, band = "★", "Favor buy", "strong"
                        elif score == 5:
                            icon, tier, band = "✓", "Validated", "good"
                        elif score == 4:
                            icon, tier, band = "◐", "Keep watch", "track"
                        else:
                            icon, tier, band = "○", "Weak", "weak"
                        d["canslim_score"] = score
                        d["canslim_str"] = f"{score}/6"
                        d["canslim_icon"] = icon
                        d["canslim_tier"] = tier
                        d["canslim_band"] = band
                        d["canslim_cell"] = f"{icon} {score}/6 · {tier}"
                        d["canslim_tip"] = tip
                except Exception as ex:
                    logger.debug("CANSLIM merge on main grid skipped: %s", ex)
                    for d in data:
                        d.setdefault("canslim_score", 0)
                        d.setdefault("canslim_str", "0/6")
                        d.setdefault("canslim_icon", "○")
                        d.setdefault("canslim_tier", "Weak")
                        d.setdefault("canslim_cell", "○ 0/6 · Weak")
                        d.setdefault("canslim_band", "weak")
                        d.setdefault("canslim_tip", "")
            try:
                an_map = self._get_recent_announcements_map()
                if an_map:
                    for d in data:
                        v = an_map.get(d["symbol"])
                        if v is None:
                            continue
                        d["ann_has"] = True
                        d["ann_dt"] = v[0]
                        d["ann_desc"] = v[1]
            except Exception as ex:
                logger.debug("Announcements merge on main grid skipped: %s", ex)

            xage_f = str(
                filters.get("zero_cross_age") or filters.get("cross_age") or "ALL"
            ).strip().upper()
            if xage_f in ("HAS", "LE7", "LE30", "LE90", "UNK", "UNKNOWN"):
                if xage_f == "UNKNOWN":
                    xage_f = "UNK"

                def _xage_ok(row):
                    dd = row.get("zero_cross_age_days")
                    if xage_f == "HAS":
                        return dd is not None
                    if xage_f == "UNK":
                        return dd is None
                    if xage_f == "LE7":
                        return dd is not None and float(dd) <= 7.0
                    if xage_f == "LE30":
                        return dd is not None and float(dd) <= 30.0
                    if xage_f == "LE90":
                        return dd is not None and float(dd) <= 90.0
                    return True

                data = [d for d in data if _xage_ok(d)]

            sort_key = str(filters.get("sort_key") or "rs_rating").strip().lower()
            sort_desc = bool(filters.get("sort_desc", True))

            def _sort_key(row):
                if sort_key in ("rs", "rs_rating", "rt"):
                    return int(row["rs_rating"])
                if sort_key in ("rs_delta", "rt_delta", "rtd"):
                    x = row.get("rs_delta")
                    return float(x) if x is not None else float("-inf")
                if sort_key in ("mrs", "wmrs", "w_mrs"):
                    return float(row["mrs"])
                if sort_key in ("dmrs", "d_mrs", "mrs_daily"):
                    return float(row["mrs_daily"])
                if sort_key in ("rv", "rvol"):
                    return float(row.get("rv_num", 0.0))
                if sort_key in ("w_rsi2", "wrsi2", "wr"):
                    x = row.get("w_rsi2")
                    return float(x) if x is not None else -1.0
                if sort_key in ("chg", "ch_pct", "change_pct", "p1d"):
                    return float(row.get("ch_pct", 0.0))
                if sort_key in ("ltp", "price"):
                    return float(row.get("ltp", 0.0))
                if sort_key in ("brk", "brk_lvl", "pivot"):
                    x = row.get("brk_lvl")
                    return float(x) if x is not None else float("-inf")
                if sort_key in ("ad", "ad_grade", "accdist"):
                    gm = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
                    return gm.get(str(row.get("ad_grade") or "—").upper(), 0)
                if sort_key in ("ad_ratio", "accdist_ratio"):
                    return float(row.get("ad_ratio", 0.0))
                if sort_key in ("canslim", "canslim_score", "cs"):
                    return int(row.get("canslim_score", 0))
                if sort_key in ("mrs_prev_day", "prev_mrs", "prev"):
                    x = row.get("mrs_prev_day")
                    return float(x) if x is not None else float("-inf")
                if sort_key in ("sym", "symbol", "ticker"):
                    return str(row["symbol"])
                if sort_key in ("st", "status"):
                    return str(row["status"])
                if sort_key in ("prf", "profile"):
                    return str(row["profile"])
                if sort_key in (
                    "zero_cross_age",
                    "zero_cross_age_days",
                    "cross_age",
                    "rs_0_cross_age",
                    "zc_age",
                ):
                    x = row.get("zero_cross_age_days")
                    return float(x) if x is not None else float("-inf")
                return int(row["rs_rating"])

            data.sort(key=_sort_key, reverse=sort_desc)
            
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

            logger.debug("✅ UI Response -> Returning %s of %s results.", len(results), len(data))
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
                # Refresh weekly mRS, OLS slope, and RCVR immediately (otherwise stale until 60s flush)
                try:
                    self.math.calculate_rs()
                except Exception as ex:
                    logger.warning("calculate_rs after benchmark switch: %s", ex)
            
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
            
            self._batch_fill_mrs_0_cross_unix_from_weekly_history()
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
            # Dedupe in self.symbols order (not random set iteration); put Fyers index symbols first so
            # NIFTY50/NIFTY500 subscribe early and bench_prices_w updates before the main grid.
            _seen_fy: set[str] = set()
            formatted_symbols: list[str] = []
            for _s in self.symbols:
                _fy = self._to_fyers_symbol(f"NSE:{_s}-EQ" if ":" not in str(_s) else str(_s))
                _u = str(_fy).upper()
                if _u in _seen_fy:
                    continue
                _seen_fy.add(_u)
                formatted_symbols.append(_fy)
            _bfy_u = {self._to_fyers_symbol(b).upper() for b in BENCHMARK_MAP.values()}
            _head = sorted([x for x in formatted_symbols if str(x).upper() in _bfy_u])
            _bs_u = self._to_fyers_symbol(self.math.bench_sym).upper()
            _head = [x for x in _head if str(x).upper() == _bs_u] + [
                x for x in _head if str(x).upper() != _bs_u
            ]
            _tail = [x for x in formatted_symbols if str(x).upper() not in _bfy_u]
            formatted_symbols = _head + _tail
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
                _cap_bfy = {self._to_fyers_symbol(b).upper() for b in BENCHMARK_MAP.values()}
                _ch = [s for s in formatted_symbols if str(s).upper() in _cap_bfy]
                _cur_bs = self._to_fyers_symbol(self.math.bench_sym).upper()
                _ch = [s for s in _ch if str(s).upper() == _cur_bs] + [
                    s for s in _ch if str(s).upper() != _cur_bs
                ]
                _ct = [s for s in formatted_symbols if str(s).upper() not in _cap_bfy]
                formatted_symbols = _ch + _ct[: max(0, 5000 - len(_ch))]
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
                # Wait for token map to reflect this batch; if it stalls, back off a bit.
                t0 = time.time()
                prev_n = len(getattr(self.ws, "symbol_token", {}) or {})
                # Keep the per-batch wait bounded to avoid blocking forever on SDK quirks.
                # This helps with the observed "partial mapping" cases where hammering subscribe()
                # too quickly results in low token coverage.
                max_wait = float(os.getenv("FYERS_WS_SUB_CONFIRM_TIMEOUT_SEC", "3.5"))
                while time.time() - t0 < max_wait:
                    cur_n = len(getattr(self.ws, "symbol_token", {}) or {})
                    if cur_n > prev_n:
                        break
                    time.sleep(0.15)
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
            self._ws_full_subscribe_targets = list(formatted_symbols)
            self.last_flush = time.time()

            while True:
                try:
                    # MASTER PULSE RE-INITIALIZATION: Global Scope Protection
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
                            original_idx = self._universe_row_index_for_benchmark(b_sym)
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
                        
                        self._batch_fill_mrs_0_cross_unix_from_weekly_history()
                        # 3. Final Universal Persistence (X-Ray of the Universe)
                        self.persist_to_postgres()
                        self._snapshot_eod_mrs_prev_day_if_due()
                        logger.info("✅ [Scanner] Database sync complete.")
                        self.last_flush = time.time()
                        
                except Exception as e:
                    logger.error(f"❌ [Master] Critical Loop Error (Pulse/DB): {e}")
                    import traceback; traceback.print_exc()
                self._log_tick_health()
                self._maybe_recover_dead_subscription_map()
                self._maybe_resubscribe_unresolved_symbols()
                self._maybe_resubscribe_stale_symbols()
                self._maybe_refresh_w_rsi2_background()

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
            # SDK sometimes delivers a batch list instead of a single dict.
            if isinstance(m, list):
                for item in m:
                    if isinstance(item, dict):
                        self.on_tick(item)
                return
            if not isinstance(m, dict):
                return
            sym = m.get("symbol")
            if isinstance(sym, bytes):
                sym = sym.decode("utf-8", errors="ignore")
            fp = _tick_ltp_from_message(m)
            vol = _tick_session_volume(m)
            if sym is None or (isinstance(sym, str) and not sym.strip()) or fp is None:
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

        # Deduplicate by symbol before ON CONFLICT batch upsert.
        # Scanning full SHM can include mirror slots (e.g., benchmark aliases), and Postgres rejects
        # duplicate conflict keys inside a single INSERT ... ON CONFLICT statement.
        rec_map = {}
        for row in recs:
            rec_map[row[0]] = row
        dup_n = len(recs) - len(rec_map)
        recs = sorted(rec_map.values(), key=lambda t: t[0])
        if dup_n > 0:
            print(f"⚠️ [Master] Deduped {dup_n} duplicate live_state symbols before upsert.", flush=True)
        print(f"💾 [Master] Syncing Universal World: {len(recs)} symbols -> Postgres...", flush=True)

        self.db.ensure_live_state_table()
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
        for attempt in range(5):
            try:
                with self.db.get_connection() as conn:
                    try:
                        with conn.cursor() as cur:
                            acquire_live_state_xact_lock(cur)
                            execute_values(cur, q, recs)
                        conn.commit()
                        print("✅ [DB] Commit successful.", flush=True)
                        return
                    except Exception:
                        conn.rollback()
                        raise
            except Exception as e:
                if _is_deadlock_exception(e) and attempt < 4:
                    time.sleep(0.05 * (2**attempt))
                    continue
                print(f"❌ [DB] persist_to_postgres failed: {e}", flush=True)
                return

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
