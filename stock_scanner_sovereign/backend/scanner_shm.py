# backend/scanner_shm.py
import os, fcntl, time, json, mmap, logging
logger = logging.getLogger(__name__)
import numpy as np
from utils.constants import SIGNAL_DTYPE

class SHMBridge:
    def __init__(self, root_dir=None):
        # Auto-detect root: /app if in docker, otherwise current project dir
        if root_dir is None:
            if os.path.exists("/app/stock_scanner_sovereign"):
                root_dir = "/app/stock_scanner_sovereign"
            else:
                # Local host fallback: detect based on file location
                # file is in RS_PROJECT/stock_scanner_sovereign/backend/scanner_shm.py
                # we want RS_PROJECT/stock_scanner_sovereign
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.shm_path = os.path.join(root_dir, "scanner_results.mmap")
        self.map_path = os.path.join(root_dir, "symbols_idx_map.json")
        self.lock_path = f"{self.shm_path}.lock"
        self.max_symbols = 10000
        self.sz = np.dtype(SIGNAL_DTYPE).itemsize * self.max_symbols
        self.is_master = False
        self.arr = None
        self.idx_map = {}

        # Absolute Enforcement: Ensure file exists and is the CORRECT size before mmap
        if not os.path.exists(self.shm_path):
            with open(self.shm_path, "wb") as f:
                f.truncate(self.sz)
        
        # If file exists but is WRONG size (race condition), force correct size
        if os.path.getsize(self.shm_path) < self.sz:
            with open(self.shm_path, "ab") as f:
                f.truncate(self.sz)
                
        self.f = open(self.shm_path, "r+b")
        self.mm = mmap.mmap(self.f.fileno(), self.sz)
        self.arr = np.frombuffer(self.mm, dtype=SIGNAL_DTYPE)


    def setup(self, is_master_hint=None):
        """Initializes the binary segment. Enforce Master/Slave logic."""
        env_master = os.getenv("SHM_MASTER")
        if env_master is not None:
            self.is_master = env_master.lower() == "true"
        else:
            try:
                self.lock_file = open(self.lock_path, 'w')
                fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.is_master = True if is_master_hint is None else is_master_hint
            except: self.is_master = False if is_master_hint is None else is_master_hint

        if self.is_master:
            logger.info(f"📡 [SHM] MASTER Initialized: {self.shm_path} (Size: {self.sz} bytes)")
        else:
            # SLAVE: Wait until SHM is created by Master
            for _ in range(30):
                if os.path.exists(self.shm_path) and os.path.getsize(self.shm_path) == self.sz: break
                time.sleep(2)
            else: raise FileNotFoundError(f"SHM Master not started or size mismatch. Path: {self.shm_path}, Sz: {self.sz}")
            logger.info(f"🖥️ [SHM] SLAVE Attached: {self.shm_path}")

        self.arr = np.memmap(self.shm_path, dtype=SIGNAL_DTYPE, mode='r+', shape=(self.max_symbols,))
        self.load_index_map()

    def persist_index_map(self, symbols):
        """Sovereign Mapping: Persists the O(1) Index Map for both Master and Slave."""
        # 1. Update internal dictionary
        self.idx_map = {str(s): i for i, s in enumerate(symbols)}
        
        # 2. Write to JSON for SLAVE to read
        with open(self.map_path, 'w') as f:
            json.dump(self.idx_map, f)
            
        # 3. Also persist symbols into the binary SHM segment for verification/recovery
        syms_padded = list(symbols) + [""] * (self.max_symbols - len(symbols))
        self.arr['symbol'][:] = [s.encode('utf-8')[:40] for s in syms_padded]
        # removed self.arr.flush() for WSL2 compatibility
        logger.info("Universal Index Map synced to physical memory.")
        logger.info(f"📦 [SHM] PERSISTED Map for {len(symbols)} symbols to {self.map_path}")

    def load_index_map(self):
        """(All Layers): Syncs internal index with the canonical map file."""
        if os.path.exists(self.map_path):
            try:
                with open(self.map_path, 'r') as f:
                    self.idx_map = json.load(f)
                logger.info(f"📦 [SHM] LOADED Map: {len(self.idx_map)} symbols indexed.")
            except Exception as e:
                logger.error(f"❌ [SHM] Map load fail: {e}")
                self.idx_map = {}
        else:
            logger.warning(f"⚠️ [SHM] Map file missing: {self.map_path}")

    def get_idx(self, symbol):
        """O(1) Reverse Lookup: Reactive Sync for WSL2/Worker restarts."""
        idx = self.idx_map.get(str(symbol))
        if idx is None:
            # Try one reactive reload if symbol not found (Master might have added it)
            self.load_index_map()
            idx = self.idx_map.get(str(symbol))
        return idx
