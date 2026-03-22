import time, threading, logging
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from utils.breakout_math import calculate_breakout_signals
from utils.quant_breakout_config import merge_params_with_windows
from utils.signals_math import compute_mrs_signal_line, detect_pivot_high, effective_pivot_window

LGR = logging.getLogger("Breakout")

def initial_sync_helper(self):
    def _fetch(s):
        try:
            d = self.bridge.get_historical_data(s, limit=400)
            if d is None: d = self.db.get_historical_data(s, "1d", limit=400)
            if d is not None and len(d) > 0:
                with self.lock: [self.buffers[s].append(r) for r in d]; self.pending.add(s)
        except Exception as e: LGR.error(f"Sync {s}: {e}")
    _fetch(self.bench_sym)
    with ThreadPoolExecutor(20) as ex: ex.map(_fetch, [s for s in self.symbols if s != self.bench_sym])

def main_loop_helper(self):
    while self.is_scanning:
        time.sleep(0.5)
        for s in self.all_s:
            if (idx := self.shm.get_idx(s)) is not None:
                row = self.arr[idx]
                if (hb := float(row['heartbeat'])) >= self.last_hb.get(s, -1):
                    lp, v = float(row['ltp']), float(row['rv'])
                    if self.buffers[s].is_empty() or hb > self.last_hb.get(s, -1):
                        self.buffers[s].append([hb, lp, lp, lp, lp, v])
                    self.last_hb[s] = hb; self.pending.add(s)
                    with self.lock:
                        self.results[s]['ltp'] = lp
                        self.results[s]['rv'] = v
                        self.results[s]['mrs'] = float(row['mrs'])
                        self.results[s]['change_pct'] = float(row['change_pct'])
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

                # 3. Generate Pro Signature Signal
                p["rs_rating_info"] = {
                    "rs_rating": int(row['rs_rating']),
                    "mrs": current_mrs,
                    "mrs_prev": float(row['mrs_prev']) if 'mrs_prev' in row.dtype.names else current_mrs,
                    "mrs_signal": mrs_signal,
                }
                hv = self.buffers[s].get_ordered_view()
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

def format_ui_row(d):
    s = d.get('symbol', ''); chp, rv = d.get('change_pct', 0.0), d.get('rv', 0.0)
    mrs = float(d.get('mrs', 0.0))
    ui_s = s.split(":")[1].split("-")[0] if ":" in s else s
    brk = d.get('brk_lvl')
    brk_disp = f"{float(brk):.2f}" if brk is not None else "—"
    d.update({
        'symbol': ui_s, 'chp': f"{chp:+.2f}%", 'chp_color': "#00FF00" if chp >= 0 else "#FF3131",
        'rv': f"{rv:.2f}", 'rv_color': "#00FF00" if rv >= 1.5 else "#D1D1D1",
        'trend_text': "UP" if d.get('trend_up') else "DOWN", 'trend_color': "#00FF00" if d.get('trend_up') else "#FF3131",
        'ema_str': f"{d.get('ema_f_val',0.0):.1f}/{d.get('ema_s_val',0.0):.1f}",
        'ema_color': "#00FF00" if d.get('trend_up') else "#D1D1D1", 'pc': f"{d.get('prev_close',0.0):.2f}",
        'mrs_weekly': f"{mrs:.2f}",
        'mrs_color': "#00FF00" if mrs > 0 else ("#FF3131" if mrs < 0 else "#D1D1D1"),
        'brk_lvl': brk_disp,
        'is_breakout': bool(d.get('is_breakout', False)),
    })
    return d
