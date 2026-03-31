import time, threading, logging, os
from datetime import datetime, timezone
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from zoneinfo import ZoneInfo

from config.settings import settings
from utils.breakout_math import calculate_breakout_signals
from utils.quant_breakout_config import merge_params_with_windows
from utils.pine_udai_long import compute_udai_pine
from utils.signals_math import compute_mrs_signal_line, detect_pivot_high, effective_pivot_window
from utils.monthly_rsi2_trade_rules import (
    blend_last_daily_bar_with_ltp,
    daily_close_series_from_ohlcv,
    latest_monthly_rsi2,
    sidecar_live_rsi2_window_ok,
)

LGR = logging.getLogger("Breakout")

def _weekly_close_map_from_ohlcv(h: np.ndarray) -> dict[tuple[int, int], float]:
    """
    Build { (iso_year, iso_week) : last_close_in_that_week } from daily OHLCV rows.
    Expected shape: [:, 0]=unix ts seconds, [:, 4]=close.
    """
    if h is None or len(h) < 20:
        return {}
    out: dict[tuple[int, int], float] = {}
    try:
        # h is chronological (RingBuffer ordered view); last write per week wins.
        for r in h:
            try:
                ts = float(r[0])
                c = float(r[4])
            except Exception:
                continue
            if not np.isfinite(ts) or not np.isfinite(c) or c <= 0:
                continue
            d = datetime.utcfromtimestamp(ts).date()
            iso = d.isocalendar()
            out[(int(iso.year), int(iso.week))] = c
    except Exception:
        return {}
    return out


def _stage1_price_box_from_ohlcv(h: np.ndarray) -> tuple[bool, int, float, bool, float, bool, float, bool]:
    """
    Stage-1 base detector (8+ weeks box):
    - price stays between a weekly floor/ceiling for min weeks
    - repeated tests near ceiling/floor (>=2 touches each)
    """
    if h is None or len(h) < 30:
        return False, 0, 0.0, False, 0.0, False, 0.0, False
    try:
        week = {}
        # Expected columns: [ts, open, high, low, close, vol]
        for r in h:
            try:
                ts = float(r[0])
                hi = float(r[2])
                lo = float(r[3])
                cl = float(r[4])
                vv = float(r[5]) if len(r) > 5 else 0.0
            except Exception:
                continue
            if not np.isfinite(ts) or not np.isfinite(hi) or not np.isfinite(lo) or not np.isfinite(cl):
                continue
            if hi <= 0 or lo <= 0 or cl <= 0 or lo > hi:
                continue
            d = datetime.utcfromtimestamp(ts).date()
            iso = d.isocalendar()
            k = (int(iso.year), int(iso.week))
            w = week.get(k)
            if w is None:
                week[k] = [hi, lo, cl, max(0.0, vv)]
            else:
                if hi > w[0]:
                    w[0] = hi
                if lo < w[1]:
                    w[1] = lo
                w[2] = cl
                w[3] += max(0.0, vv)
        if len(week) < 8:
            return False, 0, 0.0, False, 0.0, False, 0.0, False
        keys = sorted(week.keys())
        highs_all = np.asarray([week[k][0] for k in keys], dtype=np.float64)
        lows_all = np.asarray([week[k][1] for k in keys], dtype=np.float64)
        closes_all = np.asarray([week[k][2] for k in keys], dtype=np.float64)
        vols_all = np.asarray([week[k][3] for k in keys], dtype=np.float64)
        min_weeks = int(os.getenv("STAGE1_BOX_MIN_WEEKS", "8"))
        lookback = int(os.getenv("STAGE1_BOX_LOOKBACK_WEEKS", "12"))
        # Keep one extra latest week for confirmation check; base itself is built on prior bars.
        lb_total = max(min_weeks + 1, min(len(keys), lookback + 1))
        highs = highs_all[-lb_total:]
        lows = lows_all[-lb_total:]
        closes = closes_all[-lb_total:]
        vols = vols_all[-lb_total:]
        if highs.size < (min_weeks + 1) or lows.size < (min_weeks + 1):
            return False, int(highs.size), 0.0, False, 0.0, False, 0.0, False
        base_highs = highs[:-1]
        base_lows = lows[:-1]
        base_closes = closes[:-1]
        base_vols = vols[:-1]
        curr_close = float(closes[-1])
        curr_vol = float(vols[-1])
        if base_highs.size < min_weeks or base_lows.size < min_weeks:
            return False, int(base_highs.size), 0.0, False, 0.0, False, 0.0, False
        ceiling = float(np.percentile(base_highs, 90))
        floor = float(np.percentile(base_lows, 10))
        if floor <= 0 or ceiling <= floor:
            return False, int(base_highs.size), 0.0, False, 0.0, False, 0.0, False
        box_range = (ceiling - floor) / floor
        max_range = float(os.getenv("STAGE1_BOX_MAX_RANGE_PCT", "0.16"))
        tol = float(os.getenv("STAGE1_BOX_TOUCH_TOL_PCT", "0.015"))
        min_touches = int(os.getenv("STAGE1_BOX_MIN_TOUCHES", "3"))
        top_touches = int(np.sum(base_highs >= ceiling * (1.0 - tol)))
        bot_touches = int(np.sum(base_lows <= floor * (1.0 + tol)))
        # Volume dry-up: recent weekly activity falls vs earlier base weeks.
        # Example default: average of last 3 weeks <= 75% of prior 5 weeks average.
        tail_w = int(os.getenv("STAGE1_VOL_DRYUP_RECENT_WEEKS", "3"))
        base_w = int(os.getenv("STAGE1_VOL_DRYUP_BASE_WEEKS", "5"))
        tail_w = max(2, min(tail_w, len(base_vols)))
        base_w = max(3, min(base_w, max(0, len(base_vols) - tail_w)))
        dry_ratio = 1.0
        vol_dry = False
        if base_w >= 3 and tail_w >= 2 and len(base_vols) >= (tail_w + base_w):
            recent = float(np.mean(base_vols[-tail_w:]))
            base = float(np.mean(base_vols[-(tail_w + base_w):-tail_w]))
            if base > 0:
                dry_ratio = recent / base
                thr = float(os.getenv("STAGE1_VOL_DRYUP_RATIO_MAX", "0.65"))
                vol_dry = dry_ratio <= thr
        # Keep dry-up as required by default; can disable with env if needed.
        need_dry = os.getenv("STAGE1_REQUIRE_VOL_DRYUP", "true").strip().lower() in ("1", "true", "yes")
        dry_ok = vol_dry if need_dry else True

        # 30-week MA flatness near current price:
        # abs(curr_close - MA30) / curr_close <= 5% (configurable)
        ma_len = int(os.getenv("STAGE1_MA_FLAT_LEN_WEEKS", "30"))
        ma_len_eff = max(5, min(ma_len, len(base_closes)))
        ma30 = float(np.mean(base_closes[-ma_len_eff:])) if ma_len_eff > 0 else 0.0
        ma_dev = abs(curr_close - ma30) / max(curr_close, 1e-9) if curr_close > 0 else 999.0
        ma_flat_thr = float(os.getenv("STAGE1_MA_FLAT_MAX_DEV_PCT", "0.04"))
        ma_flat = ma_dev <= ma_flat_thr
        need_ma_flat = os.getenv("STAGE1_REQUIRE_MA_FLAT", "true").strip().lower() in ("1", "true", "yes")
        ma_ok = ma_flat if need_ma_flat else True

        is_box = (
            (box_range <= max_range)
            and (top_touches >= min_touches)
            and (bot_touches >= min_touches)
            and (base_highs.size >= min_weeks)
            and dry_ok
            and ma_ok
        )
        # Stage-2 confirmation candidate from this weekly base:
        # latest close breaks above base ceiling and latest weekly volume expands vs prior 10w.
        vol_exp_mult = float(os.getenv("STAGE2_CONFIRM_VOL_EXP_MULT", "1.5"))
        breakout_buf = float(os.getenv("STAGE2_CONFIRM_BREAKOUT_BUFFER_PCT", "0.0"))
        wk_break = bool(curr_close > (ceiling * (1.0 + breakout_buf)))
        wk_vol_exp = False
        if len(base_vols) >= 10:
            vbase = float(np.mean(base_vols[-10:]))
            if vbase > 0:
                wk_vol_exp = bool(curr_vol >= (vol_exp_mult * vbase))
        stage2_confirm = bool(is_box and wk_break and wk_vol_exp)
        return (
            bool(is_box),
            int(highs.size),
            float(box_range),
            bool(vol_dry),
            float(dry_ratio),
            bool(ma_flat),
            float(ma_dev),
            bool(stage2_confirm),
        )
    except Exception:
        return False, 0, 0.0, False, 0.0, False, 0.0, False


def _sma_last(values: np.ndarray, n: int) -> float:
    if values.size < n or n <= 0:
        return float("nan")
    return float(np.mean(values[-n:]))


def _ema_series(values: np.ndarray, n: int) -> np.ndarray:
    """EMA over full series; returns same length array (nan where insufficient)."""
    v = np.asarray(values, dtype=np.float64)
    if v.size == 0 or n <= 1:
        return v.copy()
    alpha = 2.0 / (float(n) + 1.0)
    out = np.empty_like(v, dtype=np.float64)
    out[:] = np.nan
    # seed with SMA(n) at position n-1
    if v.size >= n:
        seed = float(np.mean(v[:n]))
        out[n - 1] = seed
        prev = seed
        for i in range(n, v.size):
            prev = alpha * float(v[i]) + (1.0 - alpha) * prev
            out[i] = prev
    return out


def _decode_shm_grid_status(raw) -> str:
    """Master SHM `status`: BUY | TRENDING | NOT TRENDING (weekly mRS rules; see docs/quant_rs_accuracy.md)."""
    if raw is None:
        return "—"
    try:
        if hasattr(raw, "tobytes"):
            s = raw.tobytes().decode("utf-8", errors="ignore")
        elif isinstance(raw, (bytes, bytearray)):
            s = raw.decode("utf-8", errors="ignore")
        else:
            s = str(raw)
    except Exception:
        return "—"
    s = s.strip("\x00").strip()
    return s if s else "—"


def initial_sync_helper(self):
    def _fetch(s):
        try:
            # Need sufficient history for weekly Mansfield RS: SMA52 + 30w slope line.
            lim = int(os.getenv("SIDECAR_HISTORY_DAILY_LIMIT", "900"))
            d = self.bridge.get_historical_data(s, limit=lim)
            if d is None:
                d = self.db.get_historical_data(s, "1d", limit=lim)
            if d is not None and len(d) > 0:
                with self.lock: [self.buffers[s].append(r) for r in d]; self.pending.add(s)
        except Exception as e: LGR.error(f"Sync {s}: {e}")
    _fetch(self.bench_sym)
    with ThreadPoolExecutor(settings.SIDECAR_SYNC_WORKERS) as ex:
        ex.map(_fetch, [s for s in self.symbols if s != self.bench_sym])

def main_loop_helper(self):
    loop_sleep = max(0.05, float(settings.SIDECAR_LOOP_SLEEP_SEC))
    while self.is_scanning:
        time.sleep(loop_sleep)
        # Snapshot keys so update_universe() replacing buffers cannot KeyError mid-iteration.
        for s in list(self.all_s):
            buf = self.buffers.get(s)
            if buf is None:
                continue
            if (idx := self.shm.get_idx(s)) is not None:
                row = self.arr[idx]
                if (hb := float(row['heartbeat'])) >= self.last_hb.get(s, -1):
                    lp, v = float(row['ltp']), float(row['rv'])
                    if buf.is_empty() or hb > self.last_hb.get(s, -1):
                        buf.append([hb, lp, lp, lp, lp, v])
                    self.last_hb[s] = hb; self.pending.add(s)
                    with self.lock:
                        rrow = self.results.get(s)
                        if rrow is None:
                            continue
                        rrow['ltp'] = lp
                        rrow['rv'] = v
                        rrow['mrs'] = float(row['mrs'])
                        rrow['change_pct'] = float(row['change_pct'])
                        # Main RS grid STATUS (same as dashboard): from master SHM, not breakout STAGE labels
                        rrow["grid_mrs_status"] = _decode_shm_grid_status(
                            row["status"] if "status" in row.dtype.names else None
                        )
        tasks, self.pending = list(self.pending), set()
        b_vw = self.buffers[self.bench_sym].get_ordered_view() if self.bench_sym in self.buffers else None
        for s in tasks:
            if (idx := self.shm.get_idx(s)) is not None and s in self.buffers:
                row = self.arr[idx]

                # --- PRO EDITION: SIGNAL LINE & CROSSOVERS ---
                # Streaming MRS deque per symbol (length from quant_breakout_config); signal line = SMA(mrs_signal_period).
                if not hasattr(self, '_mrs_history_buffers'):
                    self._mrs_history_buffers = {}

                p = merge_params_with_windows(self.params)
                mrs_period = int(p["mrs_signal_period"])
                buf_max = int(p["mrs_history_buffer_max"])

                if s not in self._mrs_history_buffers:
                    self._mrs_history_buffers[s] = {"mrs": deque(maxlen=buf_max)}

                # 1. Update MRS History
                current_mrs = float(row['mrs'])
                self._mrs_history_buffers[s]["mrs"].append(current_mrs)

                # 2. MRS signal line (SMA of length mrs_signal_period)
                mrs_deque = self._mrs_history_buffers[s]["mrs"]
                mrs_signal = compute_mrs_signal_line(mrs_deque, mrs_period)
                hv = self.buffers[s].get_ordered_view()
                # Daily EMA30 context for pullback/pierce filters.
                try:
                    if hv is not None and len(hv) >= 2:
                        cser = np.asarray(hv[:, 4], dtype=np.float64)
                        e30 = _ema_series(cser, 30)
                        ema30_val = float(e30[-1]) if e30.size else float("nan")
                        ema30_prev = float(e30[-2]) if e30.size >= 2 else float("nan")
                        prev_close = float(cser[-2]) if cser.size >= 2 else float("nan")
                    else:
                        ema30_val = float("nan")
                        ema30_prev = float("nan")
                        prev_close = float("nan")
                except Exception:
                    ema30_val = float("nan")
                    ema30_prev = float("nan")
                    prev_close = float("nan")
                with self.lock:
                    self.results[s]["ema30"] = ema30_val
                    self.results[s]["ema30_prev"] = ema30_prev
                    self.results[s]["prev_close"] = prev_close

                # 2.4 Stage-1 price box (8+ week accumulation base)
                box_refresh = float(os.getenv("STAGE1_BOX_REFRESH_SEC", "120"))
                if not hasattr(self, "_stage1_box_cache"):
                    self._stage1_box_cache = {}
                box_cached = self._stage1_box_cache.get(s)
                if box_cached and (time.time() - float(box_cached.get("ts", 0.0))) < box_refresh:
                    box_flag = bool(box_cached.get("flag", False))
                    box_weeks = int(box_cached.get("weeks", 0))
                    box_range = float(box_cached.get("range", 0.0))
                    vol_dry = bool(box_cached.get("vol_dry", False))
                    vol_dry_ratio = float(box_cached.get("vol_dry_ratio", 0.0))
                    ma_flat = bool(box_cached.get("ma_flat", False))
                    ma_dev = float(box_cached.get("ma_dev", 0.0))
                    stage2_confirm = bool(box_cached.get("stage2_confirm", False))
                else:
                    box_flag, box_weeks, box_range, vol_dry, vol_dry_ratio, ma_flat, ma_dev, stage2_confirm = _stage1_price_box_from_ohlcv(hv)
                    self._stage1_box_cache[s] = {
                        "ts": time.time(),
                        "flag": bool(box_flag),
                        "weeks": int(box_weeks),
                        "range": float(box_range),
                        "vol_dry": bool(vol_dry),
                        "vol_dry_ratio": float(vol_dry_ratio),
                        "ma_flat": bool(ma_flat),
                        "ma_dev": float(ma_dev),
                        "stage2_confirm": bool(stage2_confirm),
                    }
                with self.lock:
                    self.results[s]["stage1_box"] = bool(box_flag)
                    self.results[s]["stage1_box_weeks"] = int(box_weeks)
                    self.results[s]["stage1_box_range"] = float(box_range)
                    self.results[s]["stage1_vol_dry"] = bool(vol_dry)
                    self.results[s]["stage1_vol_dry_ratio"] = float(vol_dry_ratio)
                    self.results[s]["stage1_ma_flat"] = bool(ma_flat)
                    self.results[s]["stage1_ma_dev"] = float(ma_dev)
                    self.results[s]["stage2_confirm"] = bool(stage2_confirm)

                # 2.5. RVCR (weekly-style): match TradingView weekly pane.
                # - Compute weekly Mansfield mRS series from daily history buffer (hv) + benchmark (b_vw).
                # - Compute mRS_signal = SMA(mRS, 30) (your Pine script).
                # - Compute slopeLine = EMA(mRS, 30) or SMA(mRS, 30) (your "slope line").
                # - Signal when: slopeLine is rising by eps AND signal line crosses above slope line.
                rvcr_refresh = float(os.getenv("MRS_RVCR_WEEKLY_REFRESH_SEC", "60"))
                ma_len = int(os.getenv("MRS_WEEKLY_BASE_MA_LEN", "52"))
                sig_len = int(os.getenv("MRS_WEEKLY_SIGNAL_LEN", "30"))
                slope_len = int(os.getenv("MRS_RVCR_SLOPE_LEN", "30"))
                slope_eps = float(os.getenv("MRS_RVCR_SLOPE_EPS", "0.01"))
                now_ts = time.time()
                if not hasattr(self, "_rvcr_weekly_cache"):
                    self._rvcr_weekly_cache = {}
                cached = self._rvcr_weekly_cache.get(s)
                if cached and (now_ts - float(cached.get("ts", 0))) < rvcr_refresh:
                    with self.lock:
                        self.results[s]["mrs_rcvr"] = bool(cached.get("flag", False))
                        self.results[s]["mrs_rcvr_slope"] = float(cached.get("slope", 0.0))
                        self.results[s]["mrs_neg_ma10_rising"] = bool(cached.get("neg_ma10_rising", False))
                else:
                    flag = False
                    slope_val = 0.0
                    neg_ma10_rising = False
                    try:
                        wk_s = _weekly_close_map_from_ohlcv(hv)
                        wk_b = _weekly_close_map_from_ohlcv(b_vw) if b_vw is not None else {}
                        if wk_s and wk_b:
                            keys = sorted(set(wk_s.keys()) & set(wk_b.keys()))
                            # Allow shorter-history symbols by adapting MA lengths to available weeks.
                            # We still require at least 3 points for a reliable last/prev check.
                            need_weeks = int(max(3, max(sig_len, slope_len) + 2))
                            if len(keys) >= need_weeks:
                                s_close = np.asarray([wk_s[k] for k in keys], dtype=np.float64)
                                b_close = np.asarray([wk_b[k] for k in keys], dtype=np.float64)
                                ratio = s_close / (b_close + 1e-9)
                                # Pine: avgRatio = sma(baseRatio, 52); mRS = ((ratio/avgRatio)-1)*10
                                ma_eff = max(3, min(ma_len, int(ratio.size - 2)))
                                sig_eff = max(2, min(sig_len, int(ratio.size)))
                                slope_eff = max(2, min(slope_len, int(ratio.size)))
                                # rolling SMA for ratio
                                avg = np.full_like(ratio, np.nan, dtype=np.float64)
                                if ratio.size >= ma_eff:
                                    csum = np.cumsum(ratio, dtype=np.float64)
                                    csum = np.insert(csum, 0, 0.0)
                                    for i2 in range(ma_eff - 1, ratio.size):
                                        avg[i2] = (csum[i2 + 1] - csum[i2 + 1 - ma_eff]) / float(ma_eff)
                                mrs_series = np.nan_to_num(((ratio / (avg + 1e-12)) - 1.0) * 10.0, nan=0.0)
                                if mrs_series.size >= 11:
                                    ma10_now = float(np.mean(mrs_series[-10:]))
                                    ma10_prev = float(np.mean(mrs_series[-11:-1]))
                                    mrs_now = float(mrs_series[-1])
                                    neg_ma10_rising = (mrs_now < 0.0) and (ma10_now > ma10_prev)

                                # Signal line (SMA of mRS)
                                sig = np.full_like(mrs_series, np.nan, dtype=np.float64)
                                if mrs_series.size >= sig_eff:
                                    c2 = np.cumsum(mrs_series, dtype=np.float64)
                                    c2 = np.insert(c2, 0, 0.0)
                                    for i2 in range(sig_eff - 1, mrs_series.size):
                                        sig[i2] = (c2[i2 + 1] - c2[i2 + 1 - sig_eff]) / float(sig_eff)

                                # Slope line: EMA30 or SMA30 of mRS
                                ma_type = os.getenv("MRS_RVCR_SLOPE_MA_TYPE", "EMA").strip().upper()
                                if ma_type == "SMA":
                                    slope = np.full_like(mrs_series, np.nan, dtype=np.float64)
                                    if mrs_series.size >= slope_eff:
                                        c3 = np.cumsum(mrs_series, dtype=np.float64)
                                        c3 = np.insert(c3, 0, 0.0)
                                        for i2 in range(slope_eff - 1, mrs_series.size):
                                            slope[i2] = (c3[i2 + 1] - c3[i2 + 1 - slope_eff]) / float(slope_eff)
                                else:
                                    slope = _ema_series(mrs_series, slope_eff)

                                # Latest usable index (both lines present)
                                i_last = int(mrs_series.size - 1)
                                if i_last >= 1 and np.isfinite(slope[i_last]) and np.isfinite(slope[i_last - 1]):
                                    slope_val = float(slope[i_last] - slope[i_last - 1])
                                    slope_up = slope_val > slope_eps
                                    if np.isfinite(sig[i_last]) and np.isfinite(sig[i_last - 1]):
                                        # Signal rule: slope rising + signal line piercing above slope line.
                                        sig_cross = (float(sig[i_last - 1]) <= float(slope[i_last - 1])) and (
                                            float(sig[i_last]) > float(slope[i_last])
                                        )
                                        flag = slope_up and sig_cross
                    except Exception:
                        flag = False
                        slope_val = 0.0
                        neg_ma10_rising = False

                    self._rvcr_weekly_cache[s] = {
                        "ts": now_ts,
                        "flag": bool(flag),
                        "slope": float(slope_val),
                        "neg_ma10_rising": bool(neg_ma10_rising),
                    }
                    with self.lock:
                        self.results[s]["mrs_rcvr"] = bool(flag)
                        self.results[s]["mrs_rcvr_slope"] = float(slope_val)
                        self.results[s]["mrs_neg_ma10_rising"] = bool(neg_ma10_rising)

                # Latch RVCR while mRS is below zero so Stage-1 candidates do not flicker.
                with self.lock:
                    prev_latched = bool(self.results[s].get("mrs_rcvr_latched", False))
                    curr_flag = bool(self.results[s].get("mrs_rcvr", False))
                    if current_mrs < 0:
                        latched = prev_latched or curr_flag
                    else:
                        latched = False
                    self.results[s]["mrs_rcvr_latched"] = latched
                    self.results[s]["mrs_rcvr"] = latched

                # 3. Generate Pro Signature Signal
                p["rs_rating_info"] = {
                    "rs_rating": int(row['rs_rating']),
                    "mrs": current_mrs,
                    "mrs_prev": float(row['mrs_prev']) if 'mrs_prev' in row.dtype.names else current_mrs,
                    "mrs_signal": mrs_signal,
                    "mrs_rcvr": bool(self.results[s].get("mrs_rcvr", False)),
                    "stage1_box": bool(self.results[s].get("stage1_box", False)),
                    "mrs_neg_ma10_rising": bool(self.results[s].get("mrs_neg_ma10_rising", False)),
                    "stage2_confirm": bool(self.results[s].get("stage2_confirm", False)),
                }
                try:
                    res = calculate_breakout_signals(s, hv, b_vw, p)
                    if res:
                        self.results[s].update(res)
                        # SHM `status` is owned by the master (e.g. BUY NOW on mRS cross). Do not mirror
                        # breakout labels (STAGE 2, …) here — they overwrite and flicker vs the RS grid.
                        # Breakout page uses self.results + format_ui_row only.
                    raw_pw = int(p["pivot_high_window"])
                    pw_cap = max(1, min(raw_pw, 500))
                    pw_use = effective_pivot_window(len(hv), pw_cap) if hv is not None else None
                    if pw_use is not None and hv is not None:
                        self.results[s]["brk_lvl"] = float(detect_pivot_high(hv[:-1, 2], pw_use))
                except Exception as e:
                    LGR.error(f"Error calculating breakout signals for {s}: {e}")

                # Daily Pine (Udai Long): Parquet daily OHLCV + live LTP (feature-flagged)
                if settings.SIDECAR_UDAI_PINE and s in self.symbols and s != self.bench_sym:
                    now = time.time()
                    last = self.udai_last_fetch.get(s, 0.0)
                    if now - last >= settings.UDAI_REFRESH_SEC or s not in self.udai_ohlcv:
                        try:
                            d = self.bridge.get_historical_data(s, limit=400)
                            if d is None:
                                d = self.db.get_historical_data(s, "1d", limit=400)
                            if d is not None and len(d) > 0:
                                self.udai_ohlcv[s] = d
                                self.udai_last_fetch[s] = now
                        except Exception as e:
                            LGR.error(f"Udai fetch {s}: {e}")
                    d_hist = self.udai_ohlcv.get(s)
                    if d_hist is not None:
                        try:
                            st = self.udai_state.setdefault(s, {"in_pos": False, "trail": None})
                            lp = float(self.results[s].get("ltp", 0) or float(row["ltp"]))
                            u = compute_udai_pine(
                                d_hist,
                                lp,
                                st,
                                ema_fast=settings.UDAI_EMA_FAST,
                                ema_slow=settings.UDAI_EMA_SLOW,
                                breakout_period=settings.UDAI_BREAKOUT_PERIOD,
                                atr_period=settings.UDAI_ATR_PERIOD,
                                atr_mult=settings.UDAI_ATR_MULT,
                                risk_pct=settings.UDAI_RISK_PCT,
                                account_equity=settings.UDAI_ACCOUNT_EQUITY,
                            )
                            self.udai_state[s] = st
                            self.results[s].update(u)
                        except Exception as e:
                            LGR.error(f"Udai Pine {s}: {e}")

        # Layer 3 persistence: batch mirror brk_lvl -> live_state (same table master uses for LTP/mRS/status)
        try:
            t = time.time()
            last = getattr(self, "_brk_db_flush_ts", 0.0)
            if t - last >= 10.0:
                batch = []
                with self.lock:
                    for sym, row in self.results.items():
                        brk = row.get("brk_lvl")
                        if brk is not None:
                            batch.append((sym, float(brk)))
                if batch:
                    self.db.upsert_brk_lvls(batch)
                self._brk_db_flush_ts = t
        except Exception as e:
            LGR.error(f"brk_lvl DB persist: {e}")

        # Monthly RSI(2): run in a daemon thread so this loop never blocks on 100–500× Parquet/DB + pandas.
        if settings.SIDECAR_M_RSI2:
            now_ts = time.time()
            interval = float(settings.SIDECAR_M_RSI2_REFRESH_SEC)
            thr = getattr(self, "_mrsi2_refresh_thread", None)
            if now_ts - getattr(self, "_mrsi2_ts", 0) >= interval:
                if thr is None or not thr.is_alive():
                    self._mrsi2_ts = now_ts

                    def _mrsi2_worker():
                        try:
                            _refresh_sidecar_monthly_rsi2(self)
                        except Exception:
                            LGR.exception("mRSI2 background refresh failed")

                    self._mrsi2_refresh_thread = threading.Thread(
                        target=_mrsi2_worker,
                        daemon=True,
                        name="sidecar-mrsi2-refresh",
                    )
                    self._mrsi2_refresh_thread.start()

        # Daily pre-thrust indicators (your "missing yesterday" bucket):
        # Run once per day after 14:30 IST and persist to Postgres for quick checks.
        if settings.SIDECAR_PRE_THRUST_ENABLED:
            try:
                IST = ZoneInfo("Asia/Kolkata")
                now = datetime.now(IST)
                target_h = int(settings.SIDECAR_PRE_THRUST_IST_HOUR)
                target_m = int(settings.SIDECAR_PRE_THRUST_IST_MINUTE)
                target_hit = (now.hour > target_h) or (now.hour == target_h and now.minute >= target_m)
                done_date = getattr(self, "_pre_thrust_done_date", None)
                thr = getattr(self, "_pre_thrust_refresh_thread", None)
                if target_hit and done_date != now.date():
                    if thr is None or not thr.is_alive():
                        self._pre_thrust_done_date = now.date()

                        def _pre_thrust_worker():
                            try:
                                _refresh_sidecar_pre_thrust(self, run_date=now.date())
                            except Exception:
                                LGR.exception("Pre-thrust refresh failed")

                        self._pre_thrust_refresh_thread = threading.Thread(
                            target=_pre_thrust_worker,
                            daemon=True,
                            name="sidecar-pre-thrust-refresh",
                        )
                        self._pre_thrust_refresh_thread.start()
            except Exception:
                # Never let a scheduling bug kill sidecar scanning.
                pass

def _refresh_sidecar_monthly_rsi2(self):
    live_ok = sidecar_live_rsi2_window_ok(
        hour=settings.SIDECAR_M_RSI2_LIVE_IST_HOUR,
        minute=settings.SIDECAR_M_RSI2_LIVE_IST_MINUTE,
    )
    for s in self.symbols:
        if s == self.bench_sym:
            continue
        try:
            d_hist = self.udai_ohlcv.get(s)
            if d_hist is None or len(d_hist) < 80:
                d_hist = self.bridge.get_historical_data(s, limit=400)
                if d_hist is None:
                    d_hist = self.db.get_historical_data(s, "1d", limit=400)
            if d_hist is None or len(d_hist) < 80:
                with self.lock:
                    self.results[s]["m_rsi2"] = None
                    self.results[s]["m_rsi2_live"] = False
                continue
            arr = np.asarray(d_hist)
            base = daily_close_series_from_ohlcv(arr)
            if base is None:
                with self.lock:
                    self.results[s]["m_rsi2"] = None
                    self.results[s]["m_rsi2_live"] = False
                continue
            with self.lock:
                lp = float(self.results[s].get("ltp", 0) or 0)
            series = base
            used_live = False
            if live_ok and lp > 0:
                series = blend_last_daily_bar_with_ltp(base, lp)
                used_live = True
            lr = latest_monthly_rsi2(series, period=2)
            with self.lock:
                if lr:
                    self.results[s]["m_rsi2"] = float(lr[1])
                    self.results[s]["m_rsi2_live"] = used_live
                else:
                    self.results[s]["m_rsi2"] = None
                    self.results[s]["m_rsi2_live"] = False
        except Exception as e:
            LGR.error(f"mRSI2 {s}: {e}")

def _score_pre_thrust_setup(
    *,
    years: int,
    y_vol_x20: float | None,
    y_rng_x_atr14: float | None,
    y_near_20d_high: bool,
    y_near_52w_high: bool,
    y_near_multiy_high: bool,
    y_compress_10d: bool,
    y_compress_20d: bool,
):
    """
    Same explainable points model as `scripts/live_big_move_audit.py` (yesterday features only).
    """
    pts = 0
    why: list[str] = []

    if y_near_multiy_high:
        pts += 4
        why.append(f"{years}Y_HIGH(+4)")
    elif y_near_52w_high:
        pts += 3
        why.append("52W_HIGH(+3)")
    elif y_near_20d_high:
        pts += 2
        why.append("20D_HIGH(+2)")

    if y_compress_20d:
        pts += 2
        why.append("COMP20(+2)")
    if y_compress_10d:
        pts += 2
        why.append("COMP10(+2)")

    if y_vol_x20 is not None and np.isfinite(y_vol_x20):
        if y_vol_x20 >= 3.0:
            pts += 3
            why.append("Y_VOLx20>=3(+3)")
        elif y_vol_x20 >= 2.0:
            pts += 2
            why.append("Y_VOLx20>=2(+2)")
        elif y_vol_x20 >= 1.5:
            pts += 1
            why.append("Y_VOLx20>=1.5(+1)")

    if y_rng_x_atr14 is not None and np.isfinite(y_rng_x_atr14):
        if y_rng_x_atr14 >= 2.0:
            pts += 3
            why.append("Y_RNG/ATR>=2(+3)")
        elif y_rng_x_atr14 >= 1.5:
            pts += 2
            why.append("Y_RNG/ATR>=1.5(+2)")
        elif y_rng_x_atr14 >= 1.2:
            pts += 1
            why.append("Y_RNG/ATR>=1.2(+1)")

    return int(pts), why


def _compute_yesterday_pre_thrust_features_from_hv(
    hv: np.ndarray,
    *,
    years: int,
):
    """
    hv expected columns: [:,0]=unix ts seconds, [:,1]=open, [:,2]=high, [:,3]=low, [:,4]=close, [:,5]=volume
    """
    if hv is None or len(hv) < 60 or hv.shape[1] < 6:
        return None
    i_y = len(hv) - 1

    o = hv[:, 1].astype(np.float64)
    h = hv[:, 2].astype(np.float64)
    l = hv[:, 3].astype(np.float64)
    c = hv[:, 4].astype(np.float64)
    v = hv[:, 5].astype(np.float64)

    y_close = float(c[i_y])
    if not np.isfinite(y_close) or y_close <= 0:
        return None

    # Volume expansion vs prior 20 sessions.
    y_vol_x20 = None
    if i_y >= 21:
        base = v[i_y - 20 : i_y]
        denom = float(np.mean(base)) if base.size else 0.0
        if np.isfinite(denom) and denom > 0 and np.isfinite(v[i_y]):
            y_vol_x20 = float(v[i_y] / denom)

    # Range vs ATR(14)
    y_rng_x_atr14 = None
    if i_y >= 16:
        prev_c = c[:-1]
        tr = np.zeros_like(c, dtype=np.float64)
        tr[1:] = np.maximum.reduce(
            [
                (h[1:] - l[1:]),
                np.abs(h[1:] - prev_c),
                np.abs(l[1:] - prev_c),
            ]
        )
        atr_last = float(np.mean(tr[i_y - 13 : i_y + 1])) if i_y - 13 >= 0 else float("nan")
        if np.isfinite(atr_last) and atr_last > 0:
            y_rng = float(h[i_y] - l[i_y])
            y_rng_x_atr14 = float(y_rng / atr_last)

    # Near highs
    y_near_20d_high = False
    if i_y >= 20:
        hh20 = float(np.nanmax(h[i_y - 19 : i_y + 1]))
        if np.isfinite(hh20) and hh20 > 0:
            y_near_20d_high = bool(y_close >= 0.98 * hh20)

    win_52w = 252
    y_near_52w_high = False
    if i_y >= min(win_52w, len(hv) - 1):
        start = max(0, i_y - win_52w + 1)
        hh = float(np.nanmax(h[start : i_y + 1]))
        if np.isfinite(hh) and hh > 0:
            y_near_52w_high = bool(y_close >= 0.98 * hh)

    win_my = int(max(252, years * 252))
    y_near_multiy_high = False
    if i_y >= min(win_my, len(hv) - 1):
        start = max(0, i_y - win_my + 1)
        hh = float(np.nanmax(h[start : i_y + 1]))
        if np.isfinite(hh) and hh > 0:
            y_near_multiy_high = bool(y_close >= 0.98 * hh)

    # Compression
    rets = np.zeros_like(c, dtype=np.float64)
    rets[1:] = np.where(c[:-1] > 0, c[1:] / c[:-1] - 1.0, 0.0)
    y_compress_10d = False
    y_compress_20d = False
    if i_y >= 40:
        r10 = rets[i_y - 9 : i_y + 1]
        r10_prev = rets[i_y - 19 : i_y - 9]
        s10 = float(np.std(r10, ddof=0)) if r10.size else float("nan")
        s10p = float(np.std(r10_prev, ddof=0)) if r10_prev.size else float("nan")
        if np.isfinite(s10) and np.isfinite(s10p) and s10p > 0:
            y_compress_10d = bool(s10 <= 0.6 * s10p)

        r20 = rets[i_y - 19 : i_y + 1]
        r20_prev = rets[i_y - 39 : i_y - 19]
        s20 = float(np.std(r20, ddof=0)) if r20.size else float("nan")
        s20p = float(np.std(r20_prev, ddof=0)) if r20_prev.size else float("nan")
        if np.isfinite(s20) and np.isfinite(s20p) and s20p > 0:
            y_compress_20d = bool(s20 <= 0.6 * s20p)

    # y_date from the daily timestamp -> convert from UTC to IST
    y_date = None
    try:
        ts_y = float(hv[i_y, 0])
        y_date = datetime.fromtimestamp(ts_y, tz=timezone.utc).astimezone(ZoneInfo("Asia/Kolkata")).date()
    except Exception:
        y_date = None

    return {
        "y_date": y_date,
        "y_vol_x20": y_vol_x20,
        "y_rng_x_atr14": y_rng_x_atr14,
        "y_near_20d_high": y_near_20d_high,
        "y_near_52w_high": y_near_52w_high,
        "y_near_multiy_high": y_near_multiy_high,
        "y_compress_10d": y_compress_10d,
        "y_compress_20d": y_compress_20d,
    }


def _refresh_sidecar_pre_thrust(self, *, run_date):
    """
    Compute and persist "pre-thrust" indicators once per day (~14:30 IST).
    """
    years = int(getattr(settings, "SIDECAR_PRE_THRUST_MULTIYEAR_YEARS", 3))
    score_min = int(getattr(settings, "SIDECAR_PRE_THRUST_SCORE_MIN", 6))
    vol_min = float(getattr(settings, "SIDECAR_PRE_THRUST_Y_VOL_X20_MIN", 2.0))
    rng_min = float(getattr(settings, "SIDECAR_PRE_THRUST_Y_RNG_ATR14_MIN", 1.5))
    live_chg_min = float(getattr(settings, "SIDECAR_PRE_THRUST_LIVE_CHG_PCT_MIN", 10.0))
    max_movers = int(getattr(settings, "SIDECAR_PRE_THRUST_MAX_MOVERS", 30))

    # Find live movers from SHM, then only analyze those symbols (much faster + avoids ring-buffer pollution).
    movers: list[tuple[float, str]] = []
    for s in self.symbols:
        if not s or "-INDEX" in str(s).upper():
            continue
        try:
            idx = self.shm.get_idx(s)
            if idx is None:
                continue
            chg = float(self.arr[idx]["change_pct"])
            if np.isfinite(chg) and chg >= live_chg_min:
                movers.append((chg, s))
        except Exception:
            continue
    movers.sort(key=lambda x: x[0], reverse=True)
    movers = movers[:max_movers]

    rows: list[tuple] = []
    top: list[tuple] = []

    # Need enough daily bars for multi-year windows.
    limit = max(900, int(years * 252) + 60)

    for _, s in movers:
        try:
            d_hist = self.bridge.get_historical_data(s, limit=limit)
            feats = _compute_yesterday_pre_thrust_features_from_hv(d_hist, years=years) if d_hist is not None else None
            if not feats or feats.get("y_date") is None:
                continue

            y_score, why = _score_pre_thrust_setup(
                years=years,
                y_vol_x20=feats.get("y_vol_x20"),
                y_rng_x_atr14=feats.get("y_rng_x_atr14"),
                y_near_20d_high=bool(feats.get("y_near_20d_high")),
                y_near_52w_high=bool(feats.get("y_near_52w_high")),
                y_near_multiy_high=bool(feats.get("y_near_multiy_high")),
                y_compress_10d=bool(feats.get("y_compress_10d")),
                y_compress_20d=bool(feats.get("y_compress_20d")),
            )

            # Candidate definition: store only meaningful setups to keep DB clean.
            y_vol_x20 = feats.get("y_vol_x20")
            y_rng_x_atr14 = feats.get("y_rng_x_atr14")
            y_compress_20d = bool(feats.get("y_compress_20d"))
            is_candidate = (
                (y_score >= score_min)
                or (y_vol_x20 is not None and np.isfinite(y_vol_x20) and y_vol_x20 >= vol_min)
                or (y_rng_x_atr14 is not None and np.isfinite(y_rng_x_atr14) and y_rng_x_atr14 >= rng_min)
                or y_compress_20d
            )
            if not is_candidate:
                continue

            y_label = ",".join(why) if why else None
            rows.append(
                (
                    s,
                    run_date,
                    feats["y_date"],
                    feats.get("y_vol_x20"),
                    feats.get("y_rng_x_atr14"),
                    int(feats.get("y_compress_10d", False)),
                    int(feats.get("y_compress_20d", False)),
                    int(feats.get("y_near_20d_high", False)),
                    int(feats.get("y_near_52w_high", False)),
                    int(feats.get("y_near_multiy_high", False)),
                    y_score,
                    y_label,
                )
            )
            top.append((y_score, s, y_label))
        except Exception:
            # Keep looping even if one symbol/parquet fetch fails.
            continue

    if rows:
        try:
            self.db.upsert_pre_thrust_watchlist(rows)
        except Exception:
            LGR.exception("DB upsert for pre-thrust failed")

        top_sorted = sorted(top, key=lambda x: x[0], reverse=True)[:15]
        LGR.info(
            "Pre-thrust persisted for run_date=%s candidates=%s top=%s",
            run_date,
            len(rows),
            ", ".join([f"{sc}:{sym}" for sc, sym, _ in top_sorted if sym]),
        )
    else:
        LGR.info("Pre-thrust: no candidates computed for run_date=%s", run_date)

def format_ui_row(d):
    s = d.get('symbol', '')
    try:
        chp = float(d.get('change_pct', 0.0) or 0.0)
    except (TypeError, ValueError):
        chp = 0.0
    try:
        rv = float(d.get('rv', 0.0) or 0.0)
    except (TypeError, ValueError):
        rv = 0.0
    mrs = float(d.get('mrs', 0.0))
    ui_s = s.split(":")[1].split("-")[0] if ":" in s else s
    brk = d.get('brk_lvl')
    brk_disp = f"{float(brk):.2f}" if brk is not None else "—"
    sp = d.get("stop_price")
    stop_disp = f"{float(sp):.2f}" if sp is not None else "—"
    if not settings.SIDECAR_UDAI_PINE:
        udai_disp = "OFF"
    else:
        _u = d.get("udai_ui")
        udai_disp = str(_u).strip() if _u is not None else ""
        if not udai_disp:
            udai_disp = "—"
    _gs = d.get("grid_mrs_status") or "—"
    if _gs in ("BUY NOW", "BUY"):
        _gsc = "#00FF00"
    elif _gs == "TRENDING":
        _gsc = "#88FFAA"
    elif _gs == "NOT TRENDING":
        _gsc = "#FF6666"
    else:
        _gsc = "#D1D1D1"
    if chp < 0:
        chp_color = "#FF3131"
    elif chp > 0:
        chp_color = "#00FF00"
    else:
        chp_color = "#D1D1D1"
    _mr = d.get("m_rsi2")
    _mrl = d.get("m_rsi2_live")
    if _mr is None:
        mrsi_ui, mrsi_color = "—", "#D1D1D1"
    else:
        mfv = float(_mr)
        mrsi_ui = f"{mfv:.2f}" + ("*" if _mrl else "")
        mrsi_color = "#00FF00" if mfv < 2.0 else ("#FFB000" if mfv < 5.0 else "#D1D1D1")
    d.update({
        'symbol': ui_s, 'chp': f"{chp:+.2f}%", 'chp_color': chp_color,
        'rv': f"{rv:.2f}", 'rv_color': "#00FF00" if rv >= 1.5 else "#D1D1D1",
        'trend_text': "UP" if d.get('trend_up') else "DOWN", 'trend_color': "#00FF00" if d.get('trend_up') else "#FF3131",
        'ema_str': f"{d.get('ema_f_val',0.0):.1f}/{d.get('ema_s_val',0.0):.1f}",
        'ema30': float(d.get("ema30", 0.0) or 0.0),
        'ema30_prev': float(d.get("ema30_prev", 0.0) or 0.0),
        'prev_close_num': float(d.get("prev_close", 0.0) or 0.0),
        'ema_color': "#00FF00" if d.get('trend_up') else "#D1D1D1", 'pc': f"{d.get('prev_close',0.0):.2f}",
        'mrs_weekly': f"{mrs:.2f}",
        'mrs_color': "#00FF00" if mrs > 0 else ("#FF3131" if mrs < 0 else "#D1D1D1"),
        'mrs_grid_status': _gs,
        'mrs_grid_status_color': _gsc,
        'mrs_rcvr': bool(d.get("mrs_rcvr", False)),
        'mrs_rcvr_slope_up': float(d.get("mrs_rcvr_slope", 0.0)) > 0,
        'mrs_rcvr_str': f"{float(d.get('mrs_rcvr_slope', 0.0)):+.3f}" + (" ↑SIG" if bool(d.get("mrs_rcvr", False)) else ""),
        'mrs_rcvr_color': "#00FFAA" if float(d.get("mrs_rcvr_slope", 0.0)) > 0 else "#555555",
        'brk_lvl': brk_disp,
        'stop_price': stop_disp,
        'udai_ui': udai_disp,
        'm_rsi2_ui': mrsi_ui,
        'm_rsi2_color': mrsi_color,
        'is_breakout': bool(d.get('is_breakout', False)),
    })
    return d
