import threading, time, os, json, numpy as np
from datetime import datetime
from utils.zone_info import ZoneInfo
from utils.pipeline_bridge import PipelineBridge; from utils.ring_buffer import RingBuffer
from .database import DatabaseManager; from utils.constants import BENCHMARK_MAP, SIGNAL_DTYPE
from .breakout_logic import (
    TAG_ET9_WAIT_F21C,
    WEEKLY_CYCLE_PARITY_VERSION,
    initial_sync_helper,
    main_loop_helper,
    format_ui_row,
    compute_breakout_setup_score_row,
    _update_minimal_cycle_state,
    _update_minimal_cycle_state_weekly,
    _update_live_timing_breakout_status,
    _decode_shm_grid_status,
)

from .scanner_shm import SHMBridge

_IST_TIMING = ZoneInfo("Asia/Kolkata")
_TIMING_SNAPSHOT_FIELDS = (
    "timing_last_tag", "timing_last_event_ts",
    "timing_last_tag_w", "timing_last_event_ts_w",
    "cb_pending_day_d", "cb_pending_tag_d", "cb_pending_ts_d",
    "cb_pending_prev_tag_d", "cb_sustain_base_tag_d",
    "cb_last_confirm_day_d", "cb_count_d", "cb_live_entry_px_d", "cb_live_entry_day_d",
    "cb_pending_week_w", "cb_pending_tag_w", "cb_pending_ts_w",
    "cb_pending_prev_tag_w", "cb_sustain_base_tag_w",
    "cb_last_confirm_week_w", "cb_count_w", "cb_live_entry_px_w", "cb_live_entry_week_w",
    "cb_prev_day_d", "cb_prev_ltp_d", "cb_prev_week_w", "cb_prev_ltp_w",
    "cb_not_sustained_day_d", "cb_not_sustained_ts_d",
    "cb_not_sustained_week_w", "cb_not_sustained_ts_w",
)


def _ema_last(values: np.ndarray, n: int) -> float:
    try:
        arr = np.asarray(values, dtype=np.float64)
    except Exception:
        return float("nan")
    if arr.size < max(2, int(n)):
        return float("nan")
    a = 2.0 / (float(n) + 1.0)
    out = float(arr[0])
    for i in range(1, int(arr.size)):
        out = a * float(arr[i]) + (1.0 - a) * out
    return out


def _ltp_pct_vs_anchor(x: dict, anchor_key: str) -> float:
    """Sort key: percent move LTP vs anchor (B close or first-cross LTP)."""
    try:
        a = float(x.get(anchor_key) or 0.0)
        l = float(x.get("ltp") or 0.0)
        if a > 0.0 and l > 0.0:
            return (l / a - 1.0) * 100.0
    except (TypeError, ValueError):
        pass
    return float("-inf")


def _timing_today_iso() -> str:
    return datetime.now(_IST_TIMING).date().isoformat()


def _timing_iso_from_ts(ts_raw) -> str:
    try:
        ts = float(ts_raw or 0.0)
        if ts <= 0.0:
            return ""
        return datetime.fromtimestamp(ts, tz=_IST_TIMING).date().isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _timing_live_daily(d: dict, today_iso: str) -> bool:
    """Intraday: first cross today pending, still above daily Donchian."""
    brk = float(d.get("brk_lvl") or 0.0)
    ltp = float(d.get("ltp") or 0.0)
    if brk <= 0 or ltp <= brk:
        return False
    if str(d.get("cb_pending_day_d") or "") != today_iso:
        return False
    return bool(str(d.get("cb_pending_tag_d") or "").strip()) and str(
        d.get("timing_last_tag") or ""
    ).strip().upper().startswith("C")


def _timing_sustained_daily(d: dict, today_iso: str) -> bool:
    """Daily sustained/live hold above brk_lvl: C*S hold (any day) or today's live pending C*."""
    brk = float(d.get("brk_lvl") or 0.0)
    ltp = float(d.get("ltp") or 0.0)
    if brk <= 0 or ltp <= brk:
        return False
    ttag = str(d.get("timing_last_tag") or "").strip().upper()
    if not ttag.startswith("C"):
        return False
    # Sustained tag should remain visible while still holding above breakout,
    # even if the sustain event happened on a prior day.
    if ttag.endswith("S"):
        return True
    return _timing_live_daily(d, today_iso)


def _timing_sustained_weekly(d: dict, today_iso: str) -> bool:
    """Weekly sustained/live hold above brk_lvl_w: C*S hold (any day) or live weekly pending."""
    brk = float(d.get("brk_lvl_w") or 0.0)
    ltp = float(d.get("ltp") or 0.0)
    if brk <= 0 or ltp <= brk:
        return False
    ttag = str(d.get("timing_last_tag_w") or "").strip().upper()
    if not ttag.startswith("C"):
        return False
    if ttag.endswith("S"):
        return True
    return bool(str(d.get("cb_pending_week_w") or "").strip()) and bool(str(d.get("cb_pending_tag_w") or "").strip())


def _timing_not_sustained_daily(d: dict, today_iso: str) -> bool:
    """Today had a daily live breakout context, but price is now back at/below brk_lvl."""
    brk = float(d.get("brk_lvl") or 0.0)
    ltp = float(d.get("ltp") or 0.0)
    if brk <= 0.0 or ltp > brk:
        return False
    # Explicit marker (set on failed sustain finalize).
    if str(d.get("cb_not_sustained_day_d") or "") == today_iso:
        return True
    # Intraday fallback: breakout happened today (captured), now dropped below level.
    if str(d.get("cb_live_entry_day_d") or "") == today_iso:
        return True
    # Additional fallback for rows without live_entry carry: timing event today + C* family.
    ttag = str(d.get("timing_last_tag") or "").strip().upper()
    if ttag.startswith("C") and _timing_iso_from_ts(d.get("timing_last_event_ts")) == today_iso:
        return True
    return False


def _timing_e_family(d: dict) -> bool:
    """Strict E-family timing visibility: only CE* timing tags."""
    td = str(d.get("timing_last_tag") or "").strip().upper()
    tw = str(d.get("timing_last_tag_w") or "").strip().upper()
    return td.startswith("CE") or tw.startswith("CE")


def _timing_e_sustained(d: dict) -> bool:
    """Only explicit CE*S timing tags (daily or weekly)."""
    td = str(d.get("timing_last_tag") or "").strip().upper()
    tw = str(d.get("timing_last_tag_w") or "").strip().upper()
    return (td.startswith("CE") and td.endswith("S")) or (tw.startswith("CE") and tw.endswith("S"))


def _is_index_row(sym) -> bool:
    s = str(sym or "").upper()
    return s.endswith("-INDEX") or "-INDEX" in s


def _last_tag_matches_tag_filter(lt: str, flt: str) -> bool:
    """Sidecar “tag stage” and m_rsi2 filter: support new labels (E9CT, ET9DNWF21C) + legacy (E9T, ETDN)."""
    u = (lt or "").strip().upper()
    f = (flt or "").strip().upper()
    if not f or f in ("ALL", "NONE"):
        return True
    if f in ("E9CT", "E9T") or f.startswith("E9CT"):
        return u.startswith("E9CT") or u.startswith("E9T")
    if f in (TAG_ET9_WAIT_F21C.upper(), "ETDN", "ET9DNWF21C") or f.startswith("ET9DN"):
        return u == TAG_ET9_WAIT_F21C.upper() or u == "ETDN"
    return u.startswith(f)


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


def _decode_shm_text(val) -> str:
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="ignore").strip().strip("\x00")
    if hasattr(val, "tobytes"):
        try:
            return val.tobytes().decode("utf-8", errors="ignore").strip().strip("\x00")
        except Exception:
            pass
    return str(val).strip()


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
    if preset_norm == "STAGE1_EARLY":
        return st_raw == "STAGE 1" or (mrs < 0 and bool(d.get("mrs_rcvr", False)))
    if preset_norm == "STAGE2_TRIGGER":
        return (mrs > 0) and st_raw in ("BUY NOW", "NEAR BRK", "STAGE 2")
    if preset_norm == "STAGE3_CONFIRMED":
        return bool(d.get("is_breakout")) or st_raw == "BREAKOUT"
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
        # RLock: guarded `get` + `update` patterns may nest in the same thread during refactors.
        self.lock, self.is_scanning, self.params = threading.RLock(), False, {}
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
        self._timing_snapshot_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            ".timing_state_snapshot.json",
        )
        self._timing_snapshot_flush_ts = 0.0
        self._load_timing_snapshot()

    def _load_timing_snapshot(self) -> None:
        p = getattr(self, "_timing_snapshot_path", "")
        if not p or not os.path.isfile(p):
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                snap = json.load(f)
            if not isinstance(snap, dict):
                return
            with self.lock:
                for sym, fields in snap.items():
                    row = self.results.get(sym)
                    if row is None or not isinstance(fields, dict):
                        continue
                    for k in _TIMING_SNAPSHOT_FIELDS:
                        if k in fields:
                            row[k] = fields[k]
        except Exception:
            pass

    def _flush_timing_snapshot(self, force: bool = False) -> None:
        p = getattr(self, "_timing_snapshot_path", "")
        if not p:
            return
        now = float(time.time())
        if not force and (now - float(getattr(self, "_timing_snapshot_flush_ts", 0.0))) < 5.0:
            return
        snap = {}
        try:
            with self.lock:
                for sym, row in self.results.items():
                    fields = {k: row.get(k) for k in _TIMING_SNAPSHOT_FIELDS if k in row}
                    if any(v not in (None, "", 0, 0.0) for v in fields.values()):
                        snap[sym] = fields
            os.makedirs(os.path.dirname(p), exist_ok=True)
            tmp = f"{p}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snap, f, separators=(",", ":"))
            os.replace(tmp, p)
            self._timing_snapshot_flush_ts = now
        except Exception:
            pass

    def update_params(self, **p):
        """Merge runtime knobs. Window overrides: mrs_signal_period, pivot_high_window, min_intraday_bars_for_breakout (see docs/quant_rs_accuracy.md)."""
        self.params.update(p)
    def update_universe(self, universe, symbols=None):
        from utils.symbols import get_nifty_symbols
        universe = universe if universe is not None else "Nifty 500"
        # ENSURE FULL TICKER CONVENTION (NSE:SYMBOL-EQ)
        raw_symbols = get_nifty_symbols(universe) if symbols is None else list(symbols)
        new_symbols = []
        for s in raw_symbols:
            if ":" not in s:
                # Heuristic: If it's pure alphabetical, assume NSE EQ
                if s.isalpha() or s.isalnum():
                    s = f"NSE:{s}-EQ"
            new_symbols.append(s)
        new_bench = BENCHMARK_MAP.get(universe, "NSE:NIFTY50-INDEX")
        # Idempotency: if requested universe + symbol set + benchmark are unchanged,
        # do NOT reset self.results / self.buffers. Previously every /breakout on_load
        # wiped hydrated cycle state, causing the UI to flash correct data for a poll
        # then revert to blanks/LOCKED while history reloaded.
        with self.lock:
            same = (
                getattr(self, "universe", None) == universe
                and getattr(self, "bench_sym", None) == new_bench
                and set(getattr(self, "symbols", []) or []) == set(new_symbols)
            )
            if same:
                return
            prev_buffers = getattr(self, "buffers", {}) or {}
            prev_results = getattr(self, "results", {}) or {}
            prev_last_hb = getattr(self, "last_hb", {}) or {}
            self.universe = universe
            self.symbols = new_symbols
            self.bench_sym = new_bench
            self.all_s = list(set(self.symbols + [self.bench_sym]))
            # Preserve buffers / results for symbols that are in both the old and new universe.
            # Switching Nifty 50 → Nifty 500 used to wipe the 50 already-hydrated tickers, forcing
            # a full 900-bar re-fetch for them. This now keeps their RingBuffer and cycle state intact
            # and `initial_sync_helper` only fetches the genuinely new (or empty-buffer) symbols.
            new_buffers, new_results, new_last_hb = {}, {}, {}
            for s in self.all_s:
                buf = prev_buffers.get(s)
                if buf is None:
                    # Need enough daily history to compute weekly Mansfield mRS (SMA52) and a 30w slope line.
                    # 900 daily bars ≈ 180 weeks — safe headroom for weekly indicators.
                    buf = RingBuffer(900, 6)
                new_buffers[s] = buf
                prev_row = prev_results.get(s)
                if prev_row:
                    new_results[s] = prev_row
                else:
                    new_results[s] = {
                        "symbol": s, "ltp": 0.0, "status": "Waiting...",
                        "m_rsi2": None, "m_rsi2_live": False,
                    }
                new_last_hb[s] = float(prev_last_hb.get(s, 0.0))
            self.buffers = new_buffers
            self.results = new_results
            self.last_hb = new_last_hb
            # Only symbols whose RingBuffer is still empty need an initial sync.
            self.pending = {s for s in self.symbols if self.buffers[s].is_empty()}
            # Preserve per-symbol caches where the buffer survived; drop stale entries.
            self.udai_state = {s: v for s, v in getattr(self, "udai_state", {}).items() if s in new_buffers}
            self.udai_last_fetch = {s: v for s, v in getattr(self, "udai_last_fetch", {}).items() if s in new_buffers}
            self.udai_ohlcv = {s: v for s, v in getattr(self, "udai_ohlcv", {}).items() if s in new_buffers}
            self._cycle_backfill_ts = {s: v for s, v in getattr(self, "_cycle_backfill_ts", {}).items() if s in new_buffers}
        threading.Thread(target=initial_sync_helper, args=(self,), daemon=True).start()
        self._load_timing_snapshot()

    def start_scanning(self, **kwargs):
        self.is_scanning = True
        threading.Thread(target=main_loop_helper, args=(self,), daemon=True).start()

    def get_ui_view(self, **kw):
        with self.lock: data = [v.copy() for v in self.results.values()]
        # `SHMBridge.load_index_map()` replaces `idx_map` with a new dict when the master rewrites
        # symbols_idx_map.json. We still hold the old dict on `sym_to_idx`, so SHM lookups can
        # return another symbol's row → stale LTP/RV/CHG in UI and XLSX. Resync when the file changes.
        try:
            mp = getattr(self.shm, "map_path", None)
            if mp and os.path.exists(mp):
                mtime = os.path.getmtime(mp)
                if mtime > float(getattr(self, "_shm_idx_map_mtime", 0.0)):
                    self.shm.load_index_map()
                    self._shm_idx_map_mtime = mtime
        except Exception:
            pass
        self.sym_to_idx = self.shm.idx_map
        if not hasattr(self, "_cycle_backfill_ts"):
            self._cycle_backfill_ts = {}
        # mode="strategy" → /breakout: confirmed bar tags (B, E9CT, ET9DNWF21C, E21C, RST). No live CB overlay.
        # mode="timing"   → /breakout-timing page: live intraday CBBUY overlay + confirmed tags.
        mode = str(kw.get("mode") or "strategy").strip().lower()
        profile_f = str(kw.get("profile") or "ALL").strip().upper()
        if profile_f != "ALL":
            filtered = []
            for d in data:
                sym = str(d.get("symbol") or "")
                idx = self.sym_to_idx.get(sym)
                if idx is None or idx >= len(self.shm.arr):
                    continue
                try:
                    pf = _decode_shm_text(self.shm.arr[idx]["profile"]).upper()
                except Exception:
                    pf = ""
                if profile_f in pf:
                    filtered.append(d)
            data = filtered
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
        # Broad hydration: rebuild daily+weekly cycle state (and brk_lvl / brk_lvl_w)
        # from history for any row whose tags or breakout levels are still blank.
        # Runs BEFORE the timing fallback so the live-breakout detection has fresh levels.
        don_win = max(2, int(self.params.get("pivot_high_window", 10)))
        now_ts = float(time.time())
        # Fields the cycle helpers write; copy these back into self.results so future polls
        # (both /breakout and /breakout-timing) see the hydrated state without re-running history.
        _cycle_fields = (
            "cycle_state", "state_name", "below21_count",
            "b_count", "e9t_count", "e21c_count", "rst_count",
            "last_tag", "last_event_ts", "cycle_last_bar_key", "brk_lvl",
            "brk_b_anchor_close", "brk_b_anchor_level", "brk_b_anchor_ts",
            "cycle_state_w", "state_name_w", "below21_count_w",
            "b_count_w", "e9t_count_w", "e21c_count_w", "rst_count_w",
            "last_tag_w", "last_event_ts_w", "cycle_last_bar_key_w", "brk_lvl_w",
            "brk_b_anchor_close_w", "brk_b_anchor_level_w", "brk_b_anchor_ts_w",
            "_wcycle_v",
        )
        for d in data:
            lt = str(d.get("last_tag") or "").strip()
            ltw = str(d.get("last_tag_w") or "").strip()
            brk_ok = float(d.get("brk_lvl") or 0.0) > 0.0
            brk_w_ok = float(d.get("brk_lvl_w") or 0.0) > 0.0
            _wcv = int(d.get("_wcycle_v") or 0)
            _need_cycle_refresh = _wcv < WEEKLY_CYCLE_PARITY_VERSION
            # Persist used to omit brk_b_anchor_level(_w); rows could have tags + brk_lvl_w but
            # anchor 0 → SINCE BRK % fell back to rolling Donchian (~2%) instead of fixed B (~12%).
            _lw_u = str(ltw).strip().upper()
            _need_anchor_w = (
                brk_w_ok
                and _lw_u not in ("", "—", "RST")
                and float(d.get("brk_b_anchor_level_w") or 0.0) <= 0.0
            )
            if (
                lt not in ("", "—")
                and ltw not in ("", "—")
                and brk_ok
                and brk_w_ok
                and not _need_cycle_refresh
                and not _need_anchor_w
            ):
                continue
            sym = str(d.get("symbol") or "").strip()
            if not sym:
                continue
            try:
                last_try = float(self._cycle_backfill_ts.get(sym, 0.0))
                # Throttle random backfill; only bypass when an *old* stamp (v>=1) must be upgraded.
                _bypass_backfill_throttle = _need_cycle_refresh and _wcv > 0
                if now_ts - last_try < 180.0 and not _bypass_backfill_throttle:
                    continue
                self._cycle_backfill_ts[sym] = now_ts
                buf = self.buffers.get(sym)
                hv = buf.get_ordered_view() if buf is not None else None
                if hv is None or len(hv) < 6:
                    hist = self.bridge.get_historical_data(sym, limit=900)
                    if hist is None:
                        hist = self.db.get_historical_data(sym, "1d", limit=900)
                    if hist is not None and len(hist) > 0 and buf is not None:
                        with self.lock:
                            for rr in hist:
                                buf.append(rr)
                        hv = buf.get_ordered_view()
                if hv is not None and len(hv) >= 6:
                    _update_minimal_cycle_state(d, hv, don_len=don_win)
                    _update_minimal_cycle_state_weekly(d, hv, don_len=don_win)
                    # Persist into the stored row so the next poll (either page) gets it
                    # without re-running history, independent of the throttle cache.
                    with self.lock:
                        stored = self.results.get(sym)
                        if stored is not None:
                            for k in _cycle_fields:
                                if k in d:
                                    stored[k] = d[k]
            except Exception:
                pass
        # Persist any freshly hydrated brk_lvl to Postgres (batched, throttled to ~15 s). The
        # sidecar container scans Nifty 500 and writes the bulk of brk_lvl via its own loop;
        # this covers universes outside that scope (Midcap, Bank Nifty, SME, etc.) so the
        # main home grid's BRK column stays populated no matter what universe the dashboard
        # is currently viewing. Safe no-op when the sidecar already wrote the same value.
        try:
            _now = float(time.time())
            _last = float(getattr(self, "_ui_brk_db_flush_ts", 0.0))
            if _now - _last >= 15.0:
                _batch = []
                with self.lock:
                    for _sym, _row in self.results.items():
                        _bl = _row.get("brk_lvl")
                        if _bl is not None:
                            try:
                                _batch.append((_sym, float(_bl)))
                            except Exception:
                                continue
                if _batch:
                    try:
                        self.db.upsert_brk_lvls(_batch)
                    except Exception:
                        pass
                self._ui_brk_db_flush_ts = _now
        except Exception:
            pass
        # Pull fresh live fields from SHM for every visible row (both pages need accurate
        # price/mrs/rv/change_pct). When `main_loop_helper` is disabled in this container
        # (e.g. DASHBOARD_BREAKOUT_LOOP=0 while the sidecar container owns the heavy loop),
        # `self.results[s]` holds only the baseline {ltp:0, status:"Waiting..."}. Without this
        # refresh the /breakout page would show RVOL/W_MRS/CHG% as 0 for every row. Master SHM
        # is the source of truth for live quotes, so reading it here keeps both modes identical.
        for d in data:
            try:
                sym = str(d.get("symbol") or "")
                idx = self.sym_to_idx.get(sym)
                if idx is None or idx >= len(self.shm.arr):
                    continue
                row = self.shm.arr[idx]
                try:
                    shm_ltp = float(row["ltp"])
                    if shm_ltp > 0:
                        d["ltp"] = shm_ltp
                except Exception:
                    pass
                # Only overwrite with a positive / non-zero reading — keeps last-known values
                # during partial WS gaps. A fresh-from-SHM zero still gets written for fields
                # that are legitimately zero (e.g. rv before market open) to avoid stale UI.
                for fld, key in (("mrs", "mrs"), ("rv", "rv"), ("change_pct", "change_pct")):
                    try:
                        if fld in row.dtype.names:
                            d[key] = float(row[fld])
                    except Exception:
                        pass
                # RS Rating is an i4 percentile (0-100) written by the master scanner into SHM;
                # mirror it into the sidecar row so format_ui_row can expose it as `rs_rating`.
                try:
                    if "rs_rating" in row.dtype.names:
                        d["rs_rating"] = int(row["rs_rating"])
                except Exception:
                    pass
                try:
                    if "status" in row.dtype.names:
                        d["grid_mrs_status"] = _decode_shm_grid_status(row["status"])
                except Exception:
                    pass
                try:
                    if mode == "timing" and "heartbeat" in row.dtype.names:
                        d["_shm_quote_ts"] = float(row["heartbeat"])
                except Exception:
                    pass
                # Keep stored rows warm with the same SHM snapshot used by this response.
                # Without this, `self.results` can stay at ltp=0 while UI rows are live,
                # which also hurts timing carry-over diagnostics / probes.
                try:
                    with self.lock:
                        stored = self.results.get(sym)
                        if stored is not None:
                            for k in ("ltp", "mrs", "rv", "change_pct", "rs_rating", "grid_mrs_status"):
                                if k in d:
                                    stored[k] = d[k]
                except Exception:
                    pass
            except Exception:
                pass
        # /breakout-timing: same live timing helper as main_loop (avoids duplicate CBBUY + wall-clock ts).
        if mode == "timing":
            _now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
            for d in data:
                try:
                    # Timing overlay can run even when EMA stack feature is disabled.
                    # Backfill daily EMA9/EMA21 from the in-memory daily history so E-family
                    # live transitions (E9CT/ET9/E21C) can still be reflected intraday.
                    try:
                        if d.get("ema9_d") is None or d.get("ema21_d") is None:
                            sym = str(d.get("symbol") or "")
                            buf = self.buffers.get(sym)
                            hv = buf.get_ordered_view() if buf is not None else None
                            if hv is not None and len(hv) >= 22:
                                cls = np.asarray(hv[:, 4], dtype=np.float64)
                                e9 = _ema_last(cls, 9)
                                e21 = _ema_last(cls, 21)
                                if np.isfinite(e9):
                                    d["ema9_d"] = float(e9)
                                if np.isfinite(e21):
                                    d["ema21_d"] = float(e21)
                    except Exception:
                        pass
                    _qts = d.pop("_shm_quote_ts", None)
                    _update_live_timing_breakout_status(
                        d, float(d.get("ltp", 0.0) or 0.0), _now_ist, _qts
                    )
                    # Persist timing overlay state back to scanner memory so pending/confirm
                    # state is carried across polls (not recomputed from scratch each request).
                    try:
                        sym = str(d.get("symbol") or "")
                        with self.lock:
                            stored = self.results.get(sym)
                            if stored is not None:
                                for k in (
                                    "ema9_d", "ema21_d", *_TIMING_SNAPSHOT_FIELDS
                                ):
                                    if k in d:
                                        stored[k] = d[k]
                    except Exception:
                        pass
                except Exception:
                    pass
            self._flush_timing_snapshot()
        sq = (kw.get("search") or "").upper()
        # Sidecar v2 uses Pine-parity state_name + last_tag.
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
                if (
                    str(d.get("state_name", "")).upper() == st
                    or _last_tag_matches_tag_filter(str(d.get("last_tag", "")), st)
                )
            ]
        fm = (kw.get("filter_m_rsi2") or "ALL").strip().upper()
        if fm not in ("ALL", "", "NONE"):
            data = [
                d
                for d in data
                if _last_tag_matches_tag_filter(str(d.get("last_tag", "")), fm)
            ]
        mgrid = (kw.get("filter_mrs_grid") or "ALL").strip().upper()
        if mgrid == "TREND_OK":
            # Skip the filter entirely when the EMA9/21 stack is disabled (SIDECAR_EMA_STACK_ENABLED=0)
            # so picking TREND_OK doesn't zero out the grid. Detect "disabled" as "every row has
            # ema9_d is None" — a single populated row is enough to keep the real filter active.
            _stack_live = any(d.get("ema9_d") is not None for d in data)
            if _stack_live:
                data = [
                    d for d in data
                    if (
                        float(d.get("ltp", 0.0) or 0.0) > float(d.get("ema9_d", 0.0) or 0.0)
                        and float(d.get("ltp", 0.0) or 0.0) > float(d.get("ema21_d", 0.0) or 0.0)
                        and float(d.get("ema9_d", 0.0) or 0.0) > float(d.get("ema21_d", 0.0) or 0.0)
                    )
                ]
        preset_norm = _normalize_preset_key(kw.get("preset"))
        if preset_norm not in ("ALL", "", "NONE"):
            data = [d for d in data if _sidecar_preset_keep(d, preset_norm)]
        tf = (kw.get("timing_filter") or "ALL").strip().upper()
        _today_iso = _timing_today_iso()
        if tf == "LIVE":
            data = [d for d in data if _timing_live_daily(d, _today_iso)]
        elif tf == "SUSTAINED":
            data = [d for d in data if _timing_sustained_daily(d, _today_iso)]
        elif tf in ("SUSTAINED_W", "W_SUSTAINED"):
            data = [d for d in data if _timing_sustained_weekly(d, _today_iso)]
        elif tf == "NOT_SUSTAINED":
            data = [d for d in data if _timing_not_sustained_daily(d, _today_iso)]
        elif tf in ("E_TIMING", "E_FAMILY"):
            data = [d for d in data if _timing_e_family(d)]
        elif tf in ("E_SUSTAINED", "E_S"):
            data = [d for d in data if _timing_e_sustained(d)]
        elif tf == "D_BRK":
            data = [
                d
                for d in data
                if str(d.get("timing_last_tag") or d.get("last_tag") or "").upper().startswith(("B", "CB"))
            ]
        elif tf == "W_BRK":
            data = [
                d
                for d in data
                if str(d.get("timing_last_tag_w") or d.get("last_tag_w") or "").upper().startswith(("B", "CB"))
            ]
        elif tf in ("ANY_BRK", "B_ANY"):
            data = [
                d
                for d in data
                if str(d.get("timing_last_tag") or d.get("last_tag") or "").upper().startswith(("B", "CB"))
                or str(d.get("timing_last_tag_w") or d.get("last_tag_w") or "").upper().startswith(("B", "CB"))
            ]
        for _row in data:
            _row["setup_score"] = compute_breakout_setup_score_row(_row)
        sort_key = (kw.get("sort_key") or "").strip().lower()
        sort_desc = bool(kw.get("sort_desc", False))

        def _brk_sort_val(x):
            v = x.get("brk_lvl")
            try:
                return float(v) if v is not None else float("-inf")
            except (TypeError, ValueError):
                return float("-inf")

        if sort_key == "chp":
            data.sort(key=lambda x: float(x.get("change_pct", 0) or 0), reverse=sort_desc)
        elif sort_key == "ltp":
            data.sort(key=lambda x: float(x.get("ltp", 0) or 0), reverse=sort_desc)
        elif sort_key in ("rv", "rvol"):
            data.sort(key=lambda x: float(x.get("rv", 0) or 0), reverse=sort_desc)
        elif sort_key in ("wmrs", "w_mrs", "mrs"):
            data.sort(key=lambda x: float(x.get("mrs", 0) or 0), reverse=sort_desc)
        elif sort_key in ("last_tag_d", "timing_last_tag_d"):
            data.sort(
                key=lambda x: str(x.get("timing_last_tag") or x.get("last_tag") or "").upper(),
                reverse=sort_desc,
            )
        elif sort_key in ("last_tag_w", "timing_last_tag_w"):
            data.sort(
                key=lambda x: str(x.get("timing_last_tag_w") or x.get("last_tag_w") or "").upper(),
                reverse=sort_desc,
            )
        elif sort_key == "pct_from_b_d":
            data.sort(key=lambda x: _ltp_pct_vs_anchor(x, "brk_b_anchor_close"), reverse=sort_desc)
        elif sort_key == "pct_live_d":
            data.sort(key=lambda x: _ltp_pct_vs_anchor(x, "cb_live_entry_px_d"), reverse=sort_desc)
        elif sort_key == "pct_from_b_w":
            data.sort(key=lambda x: _ltp_pct_vs_anchor(x, "brk_b_anchor_close_w"), reverse=sort_desc)
        elif sort_key == "pct_live_w":
            data.sort(key=lambda x: _ltp_pct_vs_anchor(x, "cb_live_entry_px_w"), reverse=sort_desc)
        elif sort_key == "mrs_grid":
            data.sort(key=_mrs_grid_sort_priority, reverse=sort_desc)
        elif sort_key in ("last_ts", "last_event", "event_d", "when_d"):
            data.sort(key=lambda x: float(x.get("timing_last_event_ts", x.get("last_event_ts", 0)) or 0), reverse=sort_desc)
        elif sort_key in ("last_ts_w", "event_w", "when_w"):
            data.sort(key=lambda x: float(x.get("timing_last_event_ts_w", x.get("last_event_ts_w", 0)) or 0), reverse=sort_desc)
        elif sort_key in ("brk", "brklvl", "brk_lvl", "don10"):
            data.sort(key=_brk_sort_val, reverse=sort_desc)
        elif sort_key in ("state", "state_name"):
            data.sort(key=lambda x: str(x.get("state_name", "") or "").lower(), reverse=sort_desc)
        elif sort_key in ("last", "last_tag", "status", "stage"):
            data.sort(key=lambda x: float(x.get("last_event_ts", 0.0) or 0.0), reverse=True)
        elif sort_key == "b_count":
            data.sort(key=lambda x: int(x.get("b_count", 0) or 0), reverse=sort_desc)
        elif sort_key == "e9t_count":
            data.sort(key=lambda x: int(x.get("e9t_count", 0) or 0), reverse=sort_desc)
        elif sort_key == "e21c_count":
            data.sort(key=lambda x: int(x.get("e21c_count", 0) or 0), reverse=sort_desc)
        elif sort_key == "below21_count":
            data.sort(key=lambda x: int(x.get("below21_count", 0) or 0), reverse=sort_desc)
        elif sort_key in ("rs_rating", "rsr"):
            # rs_rating is still a raw int from SHM at this point (format_ui_row runs later).
            data.sort(key=lambda x: int(x.get("rs_rating", 0) or 0), reverse=sort_desc)
        elif sort_key in ("setup_score", "setup", "rank", "brk_rank", "score"):
            data.sort(key=lambda x: int(x.get("setup_score", 0) or 0), reverse=sort_desc)
        elif sort_key == "symbol":
            data.sort(key=lambda x: str(x.get("symbol", "") or "").lower(), reverse=sort_desc)
        else:
            data.sort(key=lambda x: float(x.get("last_event_ts", 0.0) or 0.0), reverse=True)
        _raw_rows = list(data)
        data = [format_ui_row(d) for d in _raw_rows]
        # Final display guard: enforce Rule A for SINCE BRK % on rendered rows.
        # D: breakout-level anchor (brk_b_anchor_level -> brk_lvl)
        # W: breakout-level anchor (brk_b_anchor_level_w -> brk_lvl_w)
        for i, raw in enumerate(_raw_rows):
            try:
                ltp = float(raw.get("ltp") or 0.0)
            except Exception:
                ltp = 0.0
            if ltp <= 0.0:
                continue
            try:
                ad = float(raw.get("brk_b_anchor_level", 0.0) or 0.0)
                if ad <= 0.0:
                    ad = float(raw.get("brk_lvl", 0.0) or 0.0)
                data[i]["brk_move_live_pct"] = f"{((ltp / ad) - 1.0) * 100.0:+.2f}%" if ad > 0.0 else "—"
            except Exception:
                pass
            try:
                _lw_rst_cb = (
                    str(raw.get("last_tag_w") or "").strip().upper() == "RST"
                    and str(raw.get("timing_last_tag_w") or "").strip().upper().startswith("CB")
                )
                aw = float(raw.get("brk_b_anchor_level_w", 0.0) or 0.0)
                if _lw_rst_cb:
                    aw = float(raw.get("brk_lvl_w", 0.0) or 0.0)
                elif aw <= 0.0:
                    aw = float(raw.get("brk_lvl_w", 0.0) or 0.0)
                data[i]["brk_move_live_pct_w"] = f"{((ltp / aw) - 1.0) * 100.0:+.2f}%" if aw > 0.0 else "—"
            except Exception:
                pass
        p, ps = kw.get("page", 1), kw.get("page_size", 50)
        return {"results": data[(p-1)*ps : p*ps], "total_count": len(data)}

    def stop_scanning(self): self.is_scanning = False
