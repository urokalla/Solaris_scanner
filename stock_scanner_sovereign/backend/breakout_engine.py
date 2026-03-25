import threading, time, os, numpy as np
from utils.pipeline_bridge import PipelineBridge; from utils.ring_buffer import RingBuffer
from .database import DatabaseManager; from utils.constants import BENCHMARK_MAP, SIGNAL_DTYPE
from .breakout_logic import initial_sync_helper, main_loop_helper, format_ui_row

from .scanner_shm import SHMBridge


def _is_index_row(sym) -> bool:
    s = str(sym or "").upper()
    return s.endswith("-INDEX") or "-INDEX" in s


def _ratio_price_to_brk(d: dict):
    try:
        brk = float(d.get("brk_lvl") or 0.0)
        ltp = float(d.get("ltp") or 0.0)
    except (TypeError, ValueError):
        return None
    if brk <= 0 or ltp <= 0:
        return None
    return ltp / brk


def _normalize_preset_key(preset) -> str:
    if preset is None:
        return "ALL"
    return "_".join(str(preset).strip().upper().split())


def _norm_mrs_grid_status(val) -> str:
    """MRS STATUS column source: master SHM weekly regime (BUY NOW / TRENDING / NOT TRENDING)."""
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="ignore").strip().strip("\x00").upper()
    if hasattr(val, "tobytes"):
        try:
            return val.tobytes().decode("utf-8", errors="ignore").strip().strip("\x00").upper()
        except Exception:
            pass
    return str(val).strip().upper()


def _mrs_grid_matches_filter(raw, want: str) -> bool:
    g = _norm_mrs_grid_status(raw)
    w = (want or "ALL").strip().upper()
    if w in ("ALL", "", "NONE"):
        return True
    if w in ("BUY NOW", "BUY"):
        return g in ("BUY NOW", "BUY")
    return g == w


def _mrs_grid_sort_priority(d: dict) -> int:
    """Higher = stronger for default descending sort (BUY NOW first)."""
    g = _norm_mrs_grid_status(d.get("grid_mrs_status"))
    if g in ("BUY NOW", "BUY"):
        return 3
    if g == "TRENDING":
        return 2
    if g == "NOT TRENDING":
        return 1
    return 0


def _sidecar_preset_keep(d: dict, preset_norm: str) -> bool:
    if preset_norm in ("ALL", "", "NONE"):
        return True
    sym = d.get("symbol")
    if _is_index_row(sym):
        return False
    st_raw = str(d.get("status") or "").strip().upper()
    try:
        mrs = float(d.get("mrs") or 0.0)
    except (TypeError, ValueError):
        mrs = 0.0
    try:
        rv = float(d.get("rv") or 0.0)
    except (TypeError, ValueError):
        rv = 0.0
    try:
        chp = float(d.get("change_pct") or 0.0)
    except (TypeError, ValueError):
        chp = 0.0

    if preset_norm == "BUYNOW_CROSS":
        # Must match **MRS STATUS** (master SHM): weekly BUY NOW session latch — same source as the column in the grid.
        return _mrs_grid_matches_filter(d.get("grid_mrs_status"), "BUY NOW")
    if preset_norm == "BREAKOUT":
        return bool(d.get("is_breakout")) or st_raw == "BREAKOUT"
    if preset_norm == "STAGE_2":
        return st_raw == "STAGE 2"
    if preset_norm == "EARLY":
        return mrs > 0 and st_raw in ("NEAR BRK", "STAGE 2")
    if preset_norm == "RETEST":
        rb = _ratio_price_to_brk(d)
        return rb is not None and 0.98 <= rb <= 1.03 and mrs > 0
    if preset_norm == "STRONG_RETEST":
        rb = _ratio_price_to_brk(d)
        return rb is not None and 0.99 <= rb <= 1.02 and mrs > 0 and rv >= 1.0
    if preset_norm == "FAST20":
        # Relative volume from master SHM (≈ session cumulative vol / 21d avg); threshold 2.0 = “20” style high RV.
        return rv >= 2.0
    if preset_norm == "HIGH10":
        return chp >= 10.0
    if preset_norm == "HIGH10_LITE":
        return chp >= 5.0
    return True


class BreakoutScanner:
    def __init__(self, symbols=None, universe="Nifty 500"):
        self.db, self.bridge = DatabaseManager(), PipelineBridge()
        # USE SHMBridge to ensure index alignment with Master
        self.shm = SHMBridge()
        self.shm.setup(is_master_hint=False)
        self.arr = self.shm.arr
        self.sym_to_idx = self.shm.idx_map
        self.lock, self.is_scanning, self.params = threading.Lock(), False, {}
        try:
            self.db.ensure_live_state_brk_column()
        except Exception:
            pass
        # Explicit None breaks BENCHMARK_MAP / bench buffer; keep a sane default.
        u = universe if universe is not None else "Nifty 500"
        # Same wait as MasterScanner slave: map file may lag sovereign_scanner after restart.
        if not getattr(self.shm, "is_master", True):
            for _ in range(45):
                self.shm.load_index_map()
                if len(self.shm.idx_map) > 10:
                    break
                time.sleep(2)
        self.update_universe(u, symbols)

    def update_params(self, **p):
        """Merge runtime knobs. Window overrides: mrs_signal_period, pivot_high_window, min_intraday_bars_for_breakout (see docs/quant_rs_accuracy.md)."""
        self.params.update(p)
    def update_universe(self, universe, symbols=None):
        from utils.symbols import get_nifty_symbols
        universe = universe if universe is not None else "Nifty 500"
        with self.lock:
            self.universe = universe
            # ENSURE FULL TICKER CONVENTION (NSE:SYMBOL-EQ)
            raw_symbols = symbols or get_nifty_symbols(universe)
            self.symbols = []
            for s in raw_symbols:
                if ":" not in s:
                    # Heuristic: If it's pure alphabetical, assume NSE EQ
                    if s.isalpha() or s.isalnum():
                        s = f"NSE:{s}-EQ"
                self.symbols.append(s)
                
            self.bench_sym = BENCHMARK_MAP.get(self.universe, "NSE:NIFTY50-INDEX")
            self.all_s = list(set(self.symbols + [self.bench_sym]))
            # Need enough daily history to compute weekly Mansfield mRS (SMA52) and a 30w slope line.
            # 900 daily bars ≈ 180 weeks — safe headroom for weekly indicators.
            self.buffers = {s: RingBuffer(900, 6) for s in self.all_s}
            self.results = {
                s: {"symbol": s, "ltp": 0.0, "status": "Waiting...", "m_rsi2": None, "m_rsi2_live": False}
                for s in self.all_s
            }
            self.pending, self.last_hb = set(self.symbols), {s: 0.0 for s in self.all_s}
            # Daily Pine (Udai Long): position/trail state + throttled Parquet cache (see breakout_logic)
            self.udai_state = {}
            self.udai_last_fetch = {}
            self.udai_ohlcv = {}
        threading.Thread(target=initial_sync_helper, args=(self,), daemon=True).start()

    def start_scanning(self, **kwargs):
        self.is_scanning = True
        threading.Thread(target=main_loop_helper, args=(self,), daemon=True).start()

    def get_ui_view(self, **kw):
        with self.lock: data = [v.copy() for v in self.results.values()]
        # Layer 3: hydrate pivot from Postgres when memory has not computed it yet
        try:
            need = [d["symbol"] for d in data if d.get("brk_lvl") is None]
            if need:
                m = self.db.get_brk_lvl_map(need)
                for d in data:
                    if d.get("brk_lvl") is None and d["symbol"] in m:
                        d["brk_lvl"] = m[d["symbol"]]
        except Exception:
            pass
        sq = (kw.get("search") or "").upper()
        # BRK STAGE column uses raw `status` (BREAKOUT, NEAR BRK, STAGE 2, …) before format_ui_row
        st = (kw.get("brk_stage") or kw.get("status") or "ALL").strip().upper()
        if sq:
            data = [d for d in data if sq in d["symbol"].split(":")[-1].upper()]
        import logging
        logger = logging.getLogger("BreakoutEngine")
        if st != "ALL":
            logger.info(f"🔍 [Breakout] BRK_STAGE={st} filter on {len(data)} symbols...")
            data = [
                d
                for d in data
                if (d.get("status") == st or (st == "BREAKOUT" and d.get("is_breakout")))
            ]
        fm = (kw.get("filter_m_rsi2") or "ALL").strip().upper()
        if fm == "LT2":
            data = [
                d
                for d in data
                if d.get("m_rsi2") is not None and float(d["m_rsi2"]) < 2.0
            ]
        mgrid = (kw.get("filter_mrs_grid") or "ALL").strip().upper()
        if mgrid not in ("ALL", "", "NONE"):
            data = [
                d
                for d in data
                if _mrs_grid_matches_filter(d.get("grid_mrs_status"), mgrid)
            ]
        preset_norm = _normalize_preset_key(kw.get("preset"))
        if preset_norm not in ("ALL", "", "NONE"):
            data = [d for d in data if _sidecar_preset_keep(d, preset_norm)]
        sort_key = (kw.get("sort_key") or "").strip().lower()
        sort_desc = bool(kw.get("sort_desc", False))

        def _brk_sort_val(x):
            v = x.get("brk_lvl")
            try:
                return float(v) if v is not None else float("-inf")
            except (TypeError, ValueError):
                return float("-inf")

        if sort_key == "mrs":
            data.sort(key=lambda x: float(x.get("mrs", 0) or 0), reverse=sort_desc)
        elif sort_key == "mrsi2":
            data.sort(
                key=lambda x: float(x.get("m_rsi2") if x.get("m_rsi2") is not None else 999.0),
                reverse=sort_desc,
            )
        elif sort_key == "udai":
            data.sort(
                key=lambda x: str(x.get("udai_ui") or x.get("udai") or "").lower(),
                reverse=sort_desc,
            )
        elif sort_key == "chp":
            data.sort(key=lambda x: float(x.get("change_pct", 0) or 0), reverse=sort_desc)
        elif sort_key == "ltp":
            data.sort(key=lambda x: float(x.get("ltp", 0) or 0), reverse=sort_desc)
        elif sort_key in ("brk", "brklvl", "brk_lvl"):
            data.sort(key=_brk_sort_val, reverse=sort_desc)
        elif sort_key in ("status", "stage"):
            data.sort(key=lambda x: str(x.get("status", "") or "").lower(), reverse=sort_desc)
        elif sort_key in ("mrs_grid", "mrs_grid_status", "grid_mrs"):
            data.sort(key=lambda x: _mrs_grid_sort_priority(x), reverse=sort_desc)
        elif sort_key == "symbol":
            data.sort(key=lambda x: str(x.get("symbol", "") or "").lower(), reverse=sort_desc)
        else:
            data.sort(key=lambda x: str(x.get("symbol", "") or "").lower())
        data = [format_ui_row(d) for d in data]
        p, ps = kw.get("page", 1), kw.get("page_size", 50)
        return {"results": data[(p-1)*ps : p*ps], "total_count": len(data)}

    def stop_scanning(self): self.is_scanning = False
