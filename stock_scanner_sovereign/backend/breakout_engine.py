import threading, time, os, numpy as np
from utils.pipeline_bridge import PipelineBridge; from utils.ring_buffer import RingBuffer
from .database import DatabaseManager; from utils.constants import BENCHMARK_MAP, SIGNAL_DTYPE
from .breakout_logic import (
    TAG_ET9_WAIT_F21C,
    initial_sync_helper,
    main_loop_helper,
    format_ui_row,
    _update_minimal_cycle_state,
    _update_minimal_cycle_state_weekly,
    _decode_shm_grid_status,
)

from .scanner_shm import SHMBridge


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


def _infer_b_count_for_fallback(d: dict) -> int:
    try:
        cnt = int(d.get("b_count", 0) or 0)
    except Exception:
        cnt = 0
    if cnt > 0:
        return cnt
    t = str(d.get("last_tag") or "").strip().upper()
    if not t.startswith("B"):
        return 0
    digits = []
    for ch in t[1:]:
        if ch.isdigit():
            digits.append(ch)
        else:
            break
    if not digits:
        return 1
    try:
        return max(1, int("".join(digits)))
    except Exception:
        return 1


def _infer_b_count_w_for_fallback(d: dict) -> int:
    try:
        cnt = int(d.get("b_count_w", 0) or 0)
    except Exception:
        cnt = 0
    if cnt > 0:
        return cnt
    t = str(d.get("last_tag_w") or "").strip().upper()
    if not t.startswith("B"):
        return 0
    digits = []
    for ch in t[1:]:
        if ch.isdigit():
            digits.append(ch)
        else:
            break
    if not digits:
        return 1
    try:
        return max(1, int("".join(digits)))
    except Exception:
        return 1


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

    def start_scanning(self, **kwargs):
        self.is_scanning = True
        threading.Thread(target=main_loop_helper, args=(self,), daemon=True).start()

    def get_ui_view(self, **kw):
        with self.lock: data = [v.copy() for v in self.results.values()]
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
            "cycle_state_w", "state_name_w", "below21_count_w",
            "b_count_w", "e9t_count_w", "e21c_count_w", "rst_count_w",
            "last_tag_w", "last_event_ts_w", "cycle_last_bar_key_w", "brk_lvl_w",
        )
        for d in data:
            lt = str(d.get("last_tag") or "").strip()
            ltw = str(d.get("last_tag_w") or "").strip()
            brk_ok = float(d.get("brk_lvl") or 0.0) > 0.0
            brk_w_ok = float(d.get("brk_lvl_w") or 0.0) > 0.0
            if lt not in ("", "—") and ltw not in ("", "—") and brk_ok and brk_w_ok:
                continue
            sym = str(d.get("symbol") or "").strip()
            if not sym:
                continue
            try:
                last_try = float(self._cycle_backfill_ts.get(sym, 0.0))
                if now_ts - last_try < 180.0:
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
            except Exception:
                pass
        # Timing fallback runs ONLY for the /breakout-timing page.
        # /breakout (Strategy) shows confirmed bars only — never CBBUY.
        if mode == "timing":
            for d in data:
                try:
                    ltp = float(d.get("ltp", 0.0) or 0.0)
                    brk = float(d.get("brk_lvl", 0.0) or 0.0)
                    tag = str(d.get("timing_last_tag") or d.get("last_tag") or "").strip().upper()
                    if (not tag or tag in ("—", "LOCKED")) and brk > 0 and ltp > brk:
                        nxt = _infer_b_count_for_fallback(d) + 1
                        d["timing_last_tag"] = "CBBUY" if nxt <= 1 else f"CB{nxt}BUY"
                        d["timing_last_event_ts"] = float(time.time())
                        d["cb_pending_day_d"] = "fallback_live"
                        d["timing_state_name"] = "LIVE BREAKOUT"

                    brk_w = float(d.get("brk_lvl_w", 0.0) or 0.0)
                    tag_w = str(d.get("timing_last_tag_w") or d.get("last_tag_w") or "").strip().upper()
                    if (not tag_w or tag_w in ("—", "LOCKED")) and brk_w > 0 and ltp > brk_w:
                        nxt_w = _infer_b_count_w_for_fallback(d) + 1
                        d["timing_last_tag_w"] = "CBBUY" if nxt_w <= 1 else f"CB{nxt_w}BUY"
                        d["timing_last_event_ts_w"] = float(time.time())
                        d["cb_pending_week_w"] = "fallback_live"
                        d["timing_state_name_w"] = "LIVE BREAKOUT"
                except Exception:
                    pass
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
        if tf == "D_BRK":
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
        elif sort_key == "symbol":
            data.sort(key=lambda x: str(x.get("symbol", "") or "").lower(), reverse=sort_desc)
        else:
            data.sort(key=lambda x: float(x.get("last_event_ts", 0.0) or 0.0), reverse=True)
        data = [format_ui_row(d) for d in data]
        p, ps = kw.get("page", 1), kw.get("page_size", 50)
        return {"results": data[(p-1)*ps : p*ps], "total_count": len(data)}

    def stop_scanning(self): self.is_scanning = False
