import threading, time, os, numpy as np
from utils.pipeline_bridge import PipelineBridge; from utils.ring_buffer import RingBuffer
from .database import DatabaseManager; from utils.constants import BENCHMARK_MAP, SIGNAL_DTYPE
from .breakout_logic import initial_sync_helper, main_loop_helper, format_ui_row

from .scanner_shm import SHMBridge

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
            self.buffers = {s: RingBuffer(500, 6) for s in self.all_s}
            self.results = {s: {"symbol": s, "ltp": 0.0, "status": "Waiting..."} for s in self.all_s}
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
        data = [format_ui_row(d) for d in data]
        sort_key = (kw.get("sort_key") or "").strip().lower()
        sort_desc = bool(kw.get("sort_desc", False))
        if sort_key == "mrs":
            data.sort(key=lambda x: float(x.get("mrs", 0) or 0), reverse=sort_desc)
        elif sort_key == "udai":
            data.sort(
                key=lambda x: str(x.get("udai_ui", "") or "").lower(),
                reverse=sort_desc,
            )
        else:
            data = sorted(
                data,
                key=lambda x: (bool(x.get("is_breakout")), str(x.get("symbol", ""))),
                reverse=True,
            )
        p, ps = kw.get("page", 1), kw.get("page_size", 50)
        return {"results": data[(p-1)*ps : p*ps], "total_count": len(data)}

    def stop_scanning(self): self.is_scanning = False
