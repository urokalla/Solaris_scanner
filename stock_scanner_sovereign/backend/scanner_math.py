import numpy as np, polars as pl
import os, concurrent.futures, logging
import time

logger = logging.getLogger(__name__)
from scipy.stats import rankdata
from utils.signals_math import session_rvol
from utils.mrs_weekly_dynamics import (
    mansfield_mrs_ols_slope,
    weekly_mrs_trailing_series,
)

class RSMathEngine:
    def __init__(self, symbols, bench_sym="NSE:NIFTY500-INDEX"):
        self.symbols = symbols
        self.bench_sym = bench_sym
        self.n = len(symbols)
        
        # DUAL-BRAIN LOOKBACKS: 52-Week (Stan Weinstein) and 52-Day (Momentum)
        self.lookback_w = 53  # 52 Weeks SMA + current
        self.lookback_d = 53  # 52 Days SMA + current
        
        self.n = len(symbols)
        self.symbols = symbols
        self.idx_map = {s: i for i, s in enumerate(symbols)}

        # Performance Caches for Real-Time Intelligence
        self.sma_52w_cache = np.zeros(self.n)
        self.sma_50d_cache = np.zeros(self.n)
        
        # Matrix initialization
        self.price_matrix_w = np.zeros((self.n, self.lookback_w))
        self.price_matrix_d = np.zeros((self.n, self.lookback_d))
        self.bench_prices_w = np.zeros(self.lookback_w)
        self.bench_prices_d = np.zeros(self.lookback_d)
        
        self.bench_idx = self.idx_map.get(bench_sym, 0)
        
        # SOVEREIGN BRAIN: Physical storage for Intelligence results
        self.mrs_results = np.zeros(self.n)  # W_mRS
        self.mrs_daily = np.zeros(self.n)    # D_mRS
        self.mrs_mansfield_slope = np.zeros(self.n)
        self.mrs_w_slope_4w = np.zeros(self.n)
        self.mrs_w_slope_1w = np.zeros(self.n)
        self.mrs_w_belowzero_rising = np.zeros(self.n, dtype=bool)
        # Session latch for below-zero-rising so dashboard filter remains stable while mRS<0.
        self.mrs_w_belowzero_rising_latched = np.zeros(self.n, dtype=bool)
        self.rs_ratings = np.zeros(self.n, dtype=int)
        self.vol_avg = np.zeros(self.n)
        # Today's cumulative volume (Fyers tick `v`); RVOL = day_vol / vol_avg
        self.day_vol = np.zeros(self.n)
        # Exchange prior close (from ticks' prev_close_price); used for CHG% when daily matrix [-2] is 0/wrong
        self.prev_close_day = np.zeros(self.n)

    def set_benchmark(self, bench_sym):
        """Sovereign Rebuilding: Updates the baseline target and re-syncs the tracking vectors."""
        naked_key = bench_sym.replace('NSE:', '').replace('-INDEX', '').replace('_', '').replace('-', '').upper()
        
        self.bench_idx = None
        for s, i in self.idx_map.items():
            s_naked = str(s).replace('NSE:', '').replace('-INDEX', '').replace('_', '').replace('-', '').upper()
            if naked_key == s_naked:
                self.bench_idx = i
                break
        
        if self.bench_idx is None:
            logger.error(f"❌ [Math] Critical Calibration Failure: Benchmark {bench_sym} not found!")
            self.bench_idx = 0 
        
        self.bench_sym = bench_sym
        logger.info(f"🔄 [Math] Intelligence Calibrated to: {bench_sym}")

        # Re-extract benchmark vectors
        self.bench_prices_w = self.price_matrix_w[self.bench_idx].copy()
        self.bench_prices_d = self.price_matrix_d[self.bench_idx].copy()

    def load_historical_baseline(self, data_root="/app/data/historical"):
        """Parallel Dual-Resampling: 30W and 52D matrices via Polars."""
        try:
            def get_naked(text):
                return str(text).upper().replace('NSE:', '').replace('NSE_', '').replace('-EQ', '').replace('_EQ', '').replace('-INDEX', '').replace('_INDEX', '').replace('.PARQUET', '').replace('-', '').replace('_', '')
            
            all_files = os.listdir(data_root)
            naked_file_lookup = {get_naked(f): f for f in all_files if f.upper().endswith(".PARQUET")}
        except Exception as e:
            logger.error(f"❌ [Math] Directory Fail {data_root}: {e}")
            naked_file_lookup = {}

        def _volume_col(df: pl.DataFrame):
            for c in df.columns:
                if str(c).lower() in ("volume", "vol", "v"):
                    return c
            return None

        def _mean_vol_baseline(vol_arr: np.ndarray) -> float:
            if vol_arr.size == 0:
                return 0.0
            tail = vol_arr[-21:].astype(np.float64)
            m = float(np.mean(tail))
            if m > 0:
                return m
            nz = tail[tail > 0]
            if nz.size:
                return float(np.mean(nz))
            nz2 = vol_arr.astype(np.float64)
            nz2 = nz2[nz2 > 0]
            return float(np.mean(nz2[-21:])) if nz2.size else 0.0

        def load_one(i, s):
            naked_s = get_naked(s)
            real_fname = naked_file_lookup.get(naked_s)
            
            if real_fname:
                try:
                    p = os.path.join(data_root, real_fname)
                    df = pl.read_parquet(p)
                    vcol = _volume_col(df)
                    if vcol is None:
                        return False
                    df = df.with_columns(pl.col(vcol).fill_null(0.0).alias(vcol))
                    
                    # 1. Weekly Resample (30W Perspective)
                    rw = df.group_by_dynamic("timestamp", every="1w").agg([pl.col("close").last()]).tail(self.lookback_w)
                    vals_w = rw["close"].to_numpy()
                    self.price_matrix_w[i, -len(vals_w):] = vals_w
                    
                    # 2. Daily Resample (52D Perspective)
                    rd = df.group_by_dynamic("timestamp", every="1d").agg([
                        pl.col("close").last(),
                        pl.col(vcol).sum().alias("_vol_day"),
                    ]).tail(self.lookback_d)
                    vals_d = rd["close"].to_numpy()
                    self.price_matrix_d[i, -len(vals_d):] = vals_d
                    
                    # RVOL Baseline: 21-day average daily volume (single source with session_rvol)
                    if len(rd) > 0:
                        self.vol_avg[i] = _mean_vol_baseline(rd["_vol_day"].to_numpy())
                    return True
                except Exception:
                    return False
            return False

        loaded_count = 0
        with concurrent.futures.ThreadPoolExecutor(10) as exe:
            futures = [exe.submit(load_one, i, s) for i, s in enumerate(self.symbols)]
            concurrent.futures.wait(futures)
            for f in futures:
                if f.result(): loaded_count += 1
        
        logger.info(f"✅ [Math] Dual-Matrix Sync: {loaded_count}/{self.n} symbols ready.")
        self.bench_prices_w = self.price_matrix_w[self.bench_idx]
        self.bench_prices_d = self.price_matrix_d[self.bench_idx]
        
        return self.calculate_rs()

    def calculate_rs(self):
        """SOVEREIGN DUAL BRAIN: Weekly (30W) and Daily (52D) Independent RS."""
        # Baseline Benchmark Check: If silent, fallback to synthetic median
        if not np.any(self.bench_prices_w != 0):
            self.bench_prices_w = np.nanmedian(np.where(self.price_matrix_w == 0, np.nan, self.price_matrix_w), axis=0)
            self.bench_prices_w = np.nan_to_num(self.bench_prices_w, nan=1.0)
            
        if not np.any(self.bench_prices_d != 0):
            self.bench_prices_d = np.nanmedian(np.where(self.price_matrix_d == 0, np.nan, self.price_matrix_d), axis=0)
            self.bench_prices_d = np.nan_to_num(self.bench_prices_d, nan=1.0)

        with np.errstate(divide='ignore', invalid='ignore'):
            # 1. Weekly RS Calculation (Match TradingView: 1.91 style)
            # Formula: (Price / Bench) / SMA(Price/Bench, 52W)
            ratio_w = self.price_matrix_w / (self.bench_prices_w + 1e-9)
            ratio_w_masked = np.where(ratio_w == 0, np.nan, ratio_w)
            sma_52w_val = np.nanmean(ratio_w_masked[:, :-1], axis=1).reshape(-1, 1) # Exclude current week
            sma_52w_val = np.where(np.isnan(sma_52w_val) | (sma_52w_val == 0), ratio_w[:, -1:] + 1e-9, sma_52w_val)
            self.sma_52w_cache = sma_52w_val.flatten()
            w_mrs = (ratio_w[:, -1:] / sma_52w_val).flatten()
            
            # 2. Daily RS Calculation (Match TradingView: 1.32 style)
            # Formula: (Price / Bench) / SMA(Price/Bench, 52D)
            ratio_d = self.price_matrix_d / (self.bench_prices_d + 1e-9)
            ratio_d_masked = np.where(ratio_d == 0, np.nan, ratio_d)
            sma_50d_val = np.nanmean(ratio_d_masked[:, :-1], axis=1).reshape(-1, 1) # Exclude current day
            sma_50d_val = np.where(np.isnan(sma_50d_val) | (sma_50d_val == 0), ratio_d[:, -1:] + 1e-9, sma_50d_val)
            self.sma_50d_cache = sma_50d_val.flatten()
            d_mrs = (ratio_d[:, -1:] / sma_50d_val).flatten()

        # --- SOVEREIGN PRO EDITION MATH --- 
        # Formula: ((Ratio / SMA) - 1) * 10 -> Centers at 0.0
        self.mrs_results = np.nan_to_num(((w_mrs / 1.0) - 1) * 10, nan=0.0)
        self.mrs_daily = np.nan_to_num(((d_mrs / 1.0) - 1) * 10, nan=0.0)

        # 3. Percentile Ratings (Based on Weekly Strength)
        ranks = rankdata(self.mrs_results, method='average')
        self.rs_ratings = (ranks / len(ranks) * 100).astype(int)
        
        # 4. Zero Shield: Empty data = Zero rating
        self.rs_ratings = np.where(self.price_matrix_d[:, -1] == 0, 0, self.rs_ratings)

        # 5. Mansfield mRS slope: OLS on trailing weekly mRS (oldest→newest); RCVR = below 0 + positive slope.
        try:
            K = int(os.getenv("MRS_MANSFIELD_SLOPE_WEEKS", "10"))
            K = max(3, min(K, self.lookback_w - 1))
            Y = weekly_mrs_trailing_series(self.price_matrix_w, self.bench_prices_w, K)
            self.mrs_mansfield_slope = mansfield_mrs_ols_slope(Y)
            self.mrs_w_slope_1w = Y[:, -1] - Y[:, -2]
            if Y.shape[1] >= 5:
                self.mrs_w_slope_4w = Y[:, -1] - Y[:, -5]
            else:
                self.mrs_w_slope_4w = Y[:, -1] - Y[:, 0]
            thr_slope = float(os.getenv("MRS_MANSFIELD_SLOPE_MIN", "0.035"))
            zmax = float(os.getenv("MRS_RCVR_BELOW_ZERO_MAX", "0"))
            alive = self.price_matrix_d[:, -1] != 0
            short_up = True
            if os.getenv("MRS_MANSFIELD_REQUIRE_SHORT_UP", "true").lower() in ("1", "true", "yes"):
                short_up = self.mrs_w_slope_1w > float(os.getenv("MRS_MANSFIELD_SHORT_UP_EPS", "0"))
            self.mrs_w_belowzero_rising = (
                alive
                & (self.mrs_results < zmax)
                & (self.mrs_mansfield_slope > thr_slope)
                & short_up
            )
            self.mrs_w_belowzero_rising_latched = (
                (self.mrs_results < zmax)
                & (self.mrs_w_belowzero_rising_latched | self.mrs_w_belowzero_rising)
            )
        except Exception as ex:
            logger.debug("mrs weekly dynamics skipped: %s", ex)
            self.mrs_mansfield_slope = np.zeros(self.n)
            self.mrs_w_slope_4w = np.zeros(self.n)
            self.mrs_w_slope_1w = np.zeros(self.n)
            self.mrs_w_belowzero_rising = np.zeros(self.n, dtype=bool)
            self.mrs_w_belowzero_rising_latched = np.zeros(self.n, dtype=bool)

        return self.mrs_results, self.mrs_daily, self.rs_ratings

    def update_tick(self, sym, price, session_vol=None, prev_close=None):
        """O(1) update of the last slots for real-time recalculation."""
        if sym == self.bench_sym:
            self.bench_prices_w[-1] = price
            self.bench_prices_d[-1] = price
            
        if sym in self.idx_map:
            idx = self.idx_map[sym]
            self.price_matrix_w[idx, -1] = price
            self.price_matrix_d[idx, -1] = price
            if prev_close is not None:
                try:
                    pc = float(prev_close)
                    if np.isfinite(pc) and pc > 0:
                        self.prev_close_day[idx] = pc
                except (TypeError, ValueError):
                    pass
            if session_vol is not None:
                try:
                    sv = float(session_vol)
                    if np.isfinite(sv) and sv >= 0:
                        self.day_vol[idx] = sv
                except (TypeError, ValueError):
                    pass

    def compute_rvol(self, idx: int) -> float:
        """RVOL for SHM/UI: day cumulative volume vs 21d average daily volume."""
        if idx < 0 or idx >= self.n:
            return 0.0
        d = float(self.day_vol[idx])
        a = float(self.vol_avg[idx])
        # If this symbol had no Parquet/DB volume baseline, approximate denominator from peers
        # so RVOL is not permanently 0 when ticks carry session volume.
        if (not np.isfinite(a) or a <= 0) and d > 0:
            nz = self.vol_avg[np.isfinite(self.vol_avg) & (self.vol_avg > 0)]
            if nz.size:
                a = float(np.median(nz))
        return float(session_rvol(d, a))

    def backfill_vol_avg_from_prices(self, db, limit: int = 80) -> int:
        """
        When Parquet under data_root has no usable volume, fill vol_avg from Postgres `prices.volume`
        (same 21d mean idea as load_one). Keeps RVOL denominator non-zero when DB has history.
        """
        # Pipeline persistence uses timeframe '1D'; older code queried '1d' — try both.
        _tfs = ("1D", "1d", "D")

        def try_one(i: int) -> bool:
            if self.vol_avg[i] > 0:
                return False
            sym = self.symbols[i]
            try:
                arr = np.empty((0, 6))
                for tf in _tfs:
                    arr = db.get_historical_data(sym, tf, limit)
                    if arr.size > 0:
                        break
                if arr.size == 0:
                    return False
                vols = np.asarray(arr[:, 5], dtype=np.float64)
                vols = vols[np.isfinite(vols) & (vols >= 0)]
                if vols.size == 0:
                    return False
                tail = vols[-21:] if vols.size >= 21 else vols
                m = float(np.mean(tail))
                if m > 0:
                    self.vol_avg[i] = m
                    return True
            except Exception:
                pass
            return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            hits = list(ex.map(try_one, range(self.n)))
        added = int(sum(hits))
        logger.info("[Math] vol_avg Postgres backfill: %s / %s symbols", added, self.n)
        return added

    def get_instant_mrs(self, sym, price):
        """Calculates mRS in-memory without full matrix re-scan."""
        idx = self.idx_map.get(sym)
        if idx is None or self.sma_52w_cache[idx] == 0: return 0.0
        
        bench_price = self.bench_prices_w[-1]
        if bench_price == 0: return 0.0
        
        ratio = float(price) / bench_price
        instant_mrs = ((ratio / self.sma_52w_cache[idx]) - 1) * 10
        return instant_mrs
