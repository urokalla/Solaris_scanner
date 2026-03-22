# backend/scanner_ui.py
import numpy as np, logging 
logger = logging.getLogger(__name__)
from .scanner_shm import SHMBridge 
from utils.symbols import get_nifty_symbols 

class ThinClientAPI:
    def __init__(self):
        self.shm = SHMBridge()
        self.shm.setup(is_master_hint=False) # STRICT SLAVE
        logger.info("🖥️ [UI-API] Attached to Canonical SHM. Logic: PASSIVE.")

    def get_ui_view(self, filters=None, page=1, page_size=50):
        """Vectorized view: Filters indices based on universe, then slices."""
        data = self.shm.arr[self.shm.arr['symbol'] != b""]
        
        # 1. Universe Filtering (Metadata Overlay)
        univ = filters.get('universe', 'Nifty 500') if filters else 'Nifty 500'
        u_syms = [s.encode() for s in get_nifty_symbols(univ)]
        data = data[np.isin(data['symbol'], u_syms)]
        
        # 2. Search/Profile Filtering
        if filters:
            if (s := filters.get('search')): data = data[np.char.find(data['symbol'].astype(str), s.upper()) >= 0]
            if (p := filters.get('profile')) and p != 'ALL': data = data[np.char.find(data['profile'].astype(str), p.upper()) >= 0]
            st = filters.get('status'); st = 'BUY' if st == 'BREAKOUT' else st
            if st and st != 'ALL': data = data[np.char.find(data['status'].astype(str), st.upper()) >= 0]

        # 3. Pagination & Packaging
        total = len(data); start = (page-1)*page_size; end = start+page_size
        paged = data[start:end]; results = []
        
        # 4. Binary to Dictionary (The Thin Mapping)
        for r in paged:
            results.append({
                "symbol": r['symbol'].decode(),
                "ltp": float(r['ltp']),
                "mrs": f"{float(r['mrs']):.2f}",
                "rs_rating": int(r['rs_rating']),
                "status": r['status'].decode(),
                "price_up": bool(r['price_up']),
                "price_down": bool(r['price_down'])
            })
        
        # 5. Benchmark Summary (Zero-Lag Snapshot)
        b_sym = filters.get('benchmark', 'NSE:NIFTY50-INDEX') if filters else 'NSE:NIFTY50-INDEX'
        b_idx = self.shm.get_idx(b_sym); b_row = self.shm.arr[b_idx or 0]
        
        return {
            "results": results, "total_count": total, "page": page,
            "bench_ltp": f"₹{float(b_row['ltp']):,.2f}",
            "bench_change": f"{float(b_row['change_pct']):+.2f}%",
            "bench_up": b_row['change_pct'] >= 0, "status": "Active"
        }
