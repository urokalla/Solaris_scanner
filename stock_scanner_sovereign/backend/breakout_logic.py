import time, threading, logging, os
from datetime import date, datetime, time as dt_time, timezone
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from utils.zone_info import ZoneInfo

from config.settings import settings
from utils.breakout_math import calculate_breakout_signals
from utils.quant_breakout_config import merge_params_with_windows
from utils.pine_udai_long import compute_udai_pine
from utils.signals_math import (
    collapse_sidecar_buffer_to_daily_ohlc,
    compute_mrs_signal_line,
    detect_pivot_high,
    effective_pivot_window,
    trim_series_after_corporate_action,
)
from utils.monthly_rsi2_trade_rules import (
    blend_last_daily_bar_with_ltp,
    daily_close_series_from_ohlcv,
    latest_monthly_rsi2,
    sidecar_live_rsi2_window_ok,
)

LGR = logging.getLogger("Breakout")
_IST = ZoneInfo("Asia/Kolkata")

# Bump when weekly E21C / last_tag_w parity logic changes; dashboard backfill will
# recompute once (see breakout_engine) even if last_tag_w and brk levels look "complete".
WEEKLY_CYCLE_PARITY_VERSION = 3

# User-facing LAST TAG strings (used in UI, filters, colors).
# E9T{n} / +E9T and ETDN were renamed; internal counters still use e9t_count / e9t.
TAG_ET9_WAIT_F21C = "ET9DNWF21C"  # close under EMA9, waiting for 21C path (was ETDN)


def _nse_ist_session_date_for_when(ts: float) -> date | None:
    """
    IST calendar day for a bar / event timestamp — same *date* axis as _fmt_last_event_ist
    (EOD remapped display). Used for NSE week buckets, w_row==w_now, and WHEN (W) alignment.
    """
    try:
        t = float(ts)
        if t <= 0.0 or not bool(np.isfinite(t)):
            return None
        return datetime.fromtimestamp(t, tz=_IST).date()
    except Exception:
        return None


def _nse_ist_cash_eod_ts_for_session_date(d: date) -> float:
    h = int(settings.CYCLE_SAME_DAY_BAR_FRIDAY_EOD_HOUR)
    m = int(settings.CYCLE_SAME_DAY_BAR_FRIDAY_EOD_MINUTE)
    return float(datetime.combine(d, dt_time(h, m), tzinfo=_IST).timestamp())


def _nse_ist_cash_eod_ts_for_event_bar_ts(ts: float) -> float:
    """
    Canonical NSE cash-EOD unix for the bar’s IST session day. Use for last_event_ts_w so
    the stored float matches WHEN (W) IST (15:30) instead of e.g. vendor midnight-UTC.
    """
    d = _nse_ist_session_date_for_when(ts)
    if d is None:
        return float(ts)
    return _nse_ist_cash_eod_ts_for_session_date(d)


def _bar_date_key_from_ts(ts: float) -> str:
    try:
        d = _nse_ist_session_date_for_when(float(ts))
        return d.isoformat() if d is not None else ""
    except Exception:
        return ""


def _tag_e9ct(n: int) -> str:
    k = int(n)
    return f"E9CT{k}"


def _tag_power_e9ct(base: str) -> str:
    """B1+… 'power bar' when low tagged EMA9 on the breakout bar."""
    return f"{base}+E9CT"


def _is_e9ct_tag(s: str) -> bool:
    u = str(s or "").strip().upper()
    return u.startswith("E9CT") or u.startswith("E9T")  # legacy E9T1


def _is_et9dn_wait_tag(s: str) -> bool:
    u = str(s or "").strip().upper()
    return u == TAG_ET9_WAIT_F21C.upper() or u == "ETDN"

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
            d = datetime.fromtimestamp(ts, tz=_IST).date()
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
            d = datetime.fromtimestamp(ts, tz=_IST).date()
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


def _weekly_high_close_series_from_hv(hv: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """
    Collapse daily OHLCV rows to one (week_high, week_close) per ISO week, oldest → newest.
    Week key = (year, week); last row in buffer for that week wins on close, max aggregates high.
    """
    if hv is None or len(hv) < 5:
        return None
    week: dict[tuple[int, int], list[float]] = {}
    for row in hv:
        try:
            ts = float(row[0])
            hi = float(row[2])
            cl = float(row[4])
        except Exception:
            continue
        if not (np.isfinite(ts) and np.isfinite(hi) and np.isfinite(cl) and hi > 0 and cl > 0):
            continue
        d = _nse_ist_session_date_for_when(ts)
        if d is None:
            continue
        iso = d.isocalendar()
        k = (int(iso[0]), int(iso[1]))
        if k not in week:
            week[k] = [hi, cl]
        else:
            if hi > week[k][0]:
                week[k][0] = hi
            week[k][1] = cl
    if len(week) < 4:
        return None
    keys = sorted(week.keys())
    highs = np.asarray([week[k][0] for k in keys], dtype=np.float64)
    closes = np.asarray([week[k][1] for k in keys], dtype=np.float64)
    return highs, closes


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


def _cbuy_tag(idx: int) -> str:
    n = max(1, int(idx))
    return "CBBUY" if n == 1 else f"CB{n}BUY"


def _infer_b_count_from_tag(tag_val) -> int:
    t = str(tag_val or "").strip().upper()
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


def _timing_state_from_tag(tag_val: str, pending: bool) -> str:
    t = str(tag_val or "").strip().upper()
    if t.startswith("CB"):
        return "LIVE BREAKOUT" if pending else "CONFIRMED BREAKOUT"
    if t.startswith("B"):
        # Bx+E9CT: breakout bar also tagged EMA9 on the same candle.
        return "POST-BREAKOUT" if "+" in t else "CONFIRMED BREAKOUT"
    if t == TAG_ET9_WAIT_F21C or t.startswith(("E9CT", "E21C", "RST")):
        return "POST-BREAKOUT"
    return "LOCKED"


def _update_live_timing_breakout_status(
    r: dict, ltp: float, now_dt: datetime, quote_event_ts=None
) -> None:
    now_ts = float(now_dt.timestamp())
    try:
        qts = float(quote_event_ts) if quote_event_ts is not None else 0.0
    except (TypeError, ValueError):
        qts = 0.0
    cross_ts = qts if qts > 0.0 else now_ts
    today = now_dt.date().isoformat()
    week_id = f"{int(now_dt.isocalendar().year)}-W{int(now_dt.isocalendar().week):02d}"
    cutoff = (now_dt.hour, now_dt.minute) >= (15, 30)
    weekly_finalize = now_dt.weekday() == 4 and cutoff

    def _c_tag(base_tag: str, cb_idx: int) -> str:
        t = str(base_tag or "").strip().upper()
        if t.startswith("B") or t.startswith("RST"):
            return f"CB{max(1, int(cb_idx))}"
        if t.startswith("E9CT"):
            return f"C{t}"
        if t == TAG_ET9_WAIT_F21C:
            return f"C{t}"
        if t.startswith("E21C"):
            return f"C{t}"
        return f"C{t}" if t else "CB1"

    def _stream(*, now_id: str, finalize: bool, brk_key: str, last_tag_key: str, last_ts_key: str, b_count_key: str,
                timing_tag_key: str, timing_ts_key: str, pend_id_key: str, pend_tag_key: str, pend_ts_key: str,
                pend_prev_key: str, sustain_base_key: str, cb_count_key: str, live_px_key: str, live_id_key: str,
                prev_id_key: str, prev_ltp_key: str, fail_id_key: str, fail_ts_key: str, is_weekly: bool):
        base_tag = str(r.get(last_tag_key) or "—")
        base_ts = float(r.get(last_ts_key, 0.0) or 0.0)
        brk = float(r.get(brk_key) or 0.0)
        prev_ltp = float(r.get(prev_ltp_key) or 0.0) if str(r.get(prev_id_key) or "") == now_id else 0.0
        prev_close = 0.0
        try:
            chp = float(r.get("change_pct", 0.0) or 0.0)
            den = 1.0 + chp / 100.0
            if ltp > 0 and den > 0:
                prev_close = float(ltp) / den
        except (TypeError, ValueError, ZeroDivisionError):
            prev_close = 0.0
        crossed = bool(brk > 0 and ltp > brk and ((prev_ltp > 0 and prev_ltp <= brk) or (prev_ltp <= 0 and prev_close > 0 and prev_close <= brk)))

        pend_id = str(r.get(pend_id_key) or "")
        pend_tag = str(r.get(pend_tag_key) or "")
        sustain_base = str(r.get(sustain_base_key) or "")
        cur_timing = str(r.get(timing_tag_key) or "")
        # Keep sustained timing event immutable for the same base cycle tag.
        if cur_timing.endswith("S") and sustain_base and sustain_base == base_tag:
            crossed = False
        if crossed and pend_id != now_id:
            if str(base_tag).strip().upper().startswith("RST"):
                cb_idx = 1
            else:
                base_b = max(int(r.get(b_count_key, 0) or 0), _infer_b_count_from_tag(base_tag))
                # Live timing page: if base B is from a prior bar bucket, crossing now implies next B.
                # Example: base B2 (yesterday) + live cross today => CB3. If base already updated to
                # B3 in the same bucket, keep CB3 (not CB4).
                cb_idx = max(1, base_b)
                if str(base_tag or "").strip().upper().startswith("B"):
                    evt_ts = float(r.get(last_ts_key, 0.0) or 0.0)
                    same_bucket = False
                    if evt_ts > 0.0:
                        dt = datetime.fromtimestamp(evt_ts, tz=_IST)
                        if is_weekly:
                            same_bucket = f"{int(dt.isocalendar().year)}-W{int(dt.isocalendar().week):02d}" == now_id
                        else:
                            same_bucket = dt.date().isoformat() == now_id
                    if not same_bucket:
                        cb_idx = max(1, base_b + 1)
            # This branch is entered ONLY for Donchian breakout crossing events.
            # Always use breakout-family timing tags (CBn), never CE*.
            ctag = f"CB{cb_idx}"
            r[pend_id_key], r[pend_tag_key], r[pend_ts_key], r[pend_prev_key] = now_id, ctag, cross_ts, str(r.get(timing_tag_key) or base_tag)
            r[live_px_key], r[live_id_key] = float(ltp), now_id

        pend_id = str(r.get(pend_id_key) or "")
        pend_tag = str(r.get(pend_tag_key) or "")
        if pend_id == now_id and pend_tag:
            r[timing_tag_key] = pend_tag
            r[timing_ts_key] = float(r.get(pend_ts_key) or 0.0) or now_ts
            if finalize:
                sustained = bool((pend_tag.startswith("CB") and brk > 0 and ltp > brk) or (pend_tag.startswith("CE9CT") and str(base_tag).upper().startswith("E9CT")) or (pend_tag == f"C{TAG_ET9_WAIT_F21C}" and str(base_tag).upper() == TAG_ET9_WAIT_F21C) or (pend_tag.startswith("CE21C") and str(base_tag).upper().startswith("E21C")))
                if sustained:
                    r[timing_tag_key] = f"{pend_tag}S"
                    r[timing_ts_key] = float(r.get(pend_ts_key) or 0.0) or now_ts
                    r[sustain_base_key] = base_tag
                    r[fail_id_key], r[fail_ts_key] = "", 0.0
                    if pend_tag.startswith("CB"):
                        try:
                            r[cb_count_key] = int(pend_tag[2:] or "1")
                        except ValueError:
                            r[cb_count_key] = max(1, int(r.get(cb_count_key, 0) or 0))
                else:
                    # Keep a lightweight audit marker so "NOT_SUSTAINED" can show
                    # today's failed intraday crosses without changing tag behavior.
                    r[fail_id_key], r[fail_ts_key] = now_id, float(r.get(pend_ts_key) or 0.0) or now_ts
                    r[timing_tag_key] = str(r.get(pend_prev_key) or base_tag or "RST")
                    r[timing_ts_key] = base_ts if base_ts > 0 else now_ts
                    r[sustain_base_key] = ""
                r[pend_id_key], r[pend_tag_key], r[pend_ts_key], r[pend_prev_key] = "", "", 0.0, ""
                r[live_px_key], r[live_id_key] = 0.0, ""
        else:
            cur_timing = str(r.get(timing_tag_key) or "")
            sustain_base = str(r.get(sustain_base_key) or "")
            if cur_timing.endswith("S") and sustain_base and sustain_base == base_tag:
                # Keep sustained timing tag sticky until base cycle tag changes.
                r[timing_ts_key] = float(r.get(timing_ts_key, 0.0) or 0.0)
                # Preserve live breakout anchor for current bucket so "% from breakout" remains visible.
                if str(r.get(live_id_key) or "") != now_id:
                    r[live_px_key] = float(ltp) if float(ltp or 0) > 0 else float(r.get(live_px_key, 0.0) or 0.0)
                    r[live_id_key] = now_id
            else:
                r[timing_tag_key] = base_tag
                r[timing_ts_key] = base_ts
                r[sustain_base_key] = ""
                r[live_px_key], r[live_id_key] = 0.0, ""

        r[prev_id_key] = now_id
        r[prev_ltp_key] = float(ltp) if ltp > 0 else 0.0

    _stream(
        now_id=today, finalize=cutoff, brk_key="brk_lvl", last_tag_key="last_tag", last_ts_key="last_event_ts", b_count_key="b_count",
        timing_tag_key="timing_last_tag", timing_ts_key="timing_last_event_ts",
        pend_id_key="cb_pending_day_d", pend_tag_key="cb_pending_tag_d", pend_ts_key="cb_pending_ts_d", pend_prev_key="cb_pending_prev_tag_d",
        sustain_base_key="cb_sustain_base_tag_d",
        cb_count_key="cb_count_d", live_px_key="cb_live_entry_px_d", live_id_key="cb_live_entry_day_d",
        prev_id_key="cb_prev_day_d", prev_ltp_key="cb_prev_ltp_d",
        fail_id_key="cb_not_sustained_day_d", fail_ts_key="cb_not_sustained_ts_d", is_weekly=False,
    )
    _stream(
        now_id=week_id, finalize=weekly_finalize, brk_key="brk_lvl_w", last_tag_key="last_tag_w", last_ts_key="last_event_ts_w", b_count_key="b_count_w",
        timing_tag_key="timing_last_tag_w", timing_ts_key="timing_last_event_ts_w",
        pend_id_key="cb_pending_week_w", pend_tag_key="cb_pending_tag_w", pend_ts_key="cb_pending_ts_w", pend_prev_key="cb_pending_prev_tag_w",
        sustain_base_key="cb_sustain_base_tag_w",
        cb_count_key="cb_count_w", live_px_key="cb_live_entry_px_w", live_id_key="cb_live_entry_week_w",
        prev_id_key="cb_prev_week_w", prev_ltp_key="cb_prev_ltp_w",
        fail_id_key="cb_not_sustained_week_w", fail_ts_key="cb_not_sustained_ts_w", is_weekly=True,
    )


def _update_minimal_cycle_state(
    r: dict, hv: np.ndarray | None, don_len: int = 10, *, weekly: bool = False
) -> None:
    if hv is None or len(hv) < 6:
        return
    try:
        now_dt = datetime.now(_IST)
        now_date = now_dt.date()
        last_date = datetime.fromtimestamp(float(hv[-1][0]), tz=_IST).date()
        if last_date < now_date:
            i = len(hv) - 1
        elif last_date > now_date:
            i = len(hv) - 2
        else:
            # last_date == now_date: defer partial bar unless Friday after cash (IST).
            i = len(hv) - 2
            if settings.CYCLE_SAME_DAY_BAR_FRIDAY_EOD_ENABLED and now_dt.weekday() == 4:
                if (now_dt.hour, now_dt.minute) >= (
                    settings.CYCLE_SAME_DAY_BAR_FRIDAY_EOD_HOUR,
                    settings.CYCLE_SAME_DAY_BAR_FRIDAY_EOD_MINUTE,
                ):
                    i = len(hv) - 1
        # Weekly OHLC: each row is an ISO week; last row updates intraday. TradingView
        # weekly/confirmed = last *closed* week, not the developing week — same as
        # deferring an incomplete bar. Do not i=len-1 on the in-progress last week
        # (avoids e.g. E21C8 on dashboard while TV still shows E21C7 on last confirm).
        if weekly and len(hv) >= 2:
            t_last = float(hv[-1][0])
            d_last = _nse_ist_session_date_for_when(t_last)
            if d_last is not None:
                w_row = d_last.isocalendar()[:2]
                w_now = now_dt.date().isocalendar()[:2]
                if w_row == w_now:
                    i = min(i, len(hv) - 2)
        if i < 3:
            return
        curr = hv[i]
        prev = hv[i - 1]
        ts = float(curr[0])
        close = float(curr[4])
        low = float(curr[3])
        prev_close = float(prev[4])
    except Exception:
        return

    close_ser = np.asarray(hv[:, 4], dtype=np.float64)
    highs = np.asarray(hv[:, 2], dtype=np.float64)
    lows = np.asarray(hv[:, 3], dtype=np.float64)
    e9_ser = _ema_series(close_ser, 9)
    e21_ser = _ema_series(close_ser, 21)
    if not (
        np.isfinite(e9_ser[i]) and np.isfinite(e21_ser[i]) and np.isfinite(close) and np.isfinite(low)
    ):
        return

    bar_key = _bar_date_key_from_ts(ts)
    if not bar_key:
        return

    if not str(r.get("cycle_last_bar_key") or ""):
        st_state = 0; st_below21 = 0; st_b = 0; st_e9t = 0; st_e21c = 0; st_rst = 0; st_last_tag = "—"; st_last_ts = 0.0
        st_last_don_c: float | None = None
        st_b_anchor_close = 0.0
        st_b_anchor_ts = 0.0
        try:
            dlen = max(2, int(don_len))
            replay_end = i
            for j in range(3, replay_end + 1):
                if not (np.isfinite(e9_ser[j]) and np.isfinite(e21_ser[j]) and np.isfinite(close_ser[j])):
                    continue
                c = float(close_ser[j]); pc = float(close_ser[j - 1]); lo = float(lows[j]); e9j = float(e9_ser[j]); e21j = float(e21_ser[j])
                trend = c > e9j and e9j > e21j
                brk = False
                if j >= dlen + 1:
                    don_c = float(np.max(highs[(j - dlen):j]))
                    don_p = float(np.max(highs[(j - dlen - 1):(j - 1)]))
                    brk = bool(trend and c > don_c and pc <= don_p)
                    st_last_don_c = don_c
                # Pine parity: below21 counter runs on all confirmed bars.
                st_below21 = st_below21 + 1 if c < e21j else 0
                # Pine parity: RST is the ONLY thing that resets bCount / e9tCount / e21cCount.
                # Breakouts only increment bCount; cycle counters persist across intra-cycle breakouts.
                if st_state > 0 and st_below21 >= 2:
                    st_rst += 1
                    st_state = 0; st_b = 0; st_e9t = 0; st_e21c = 0
                    st_last_tag = "RST"; st_last_ts = float(hv[j][0])
                    st_b_anchor_close = 0.0
                    st_b_anchor_ts = 0.0
                elif brk:
                    st_state = 1
                    st_b += 1
                    st_last_tag = f"B{st_b}"
                    if lo <= e9j:
                        # Pine "Power Bar": breakout and EMA9 test same candle.
                        st_last_tag = _tag_power_e9ct(st_last_tag)
                    st_last_ts = float(hv[j][0])
                    st_b_anchor_close = c
                    st_b_anchor_ts = float(hv[j][0])
                elif st_state > 0:
                    # Pine's layout: first an if/elif for state==1 transitions, then a SEPARATE
                    # if for state==2 reclaim (so a bar that flipped 1→2 this bar can't also
                    # reclaim in the same bar — but one that was already in state 2 can).
                    if st_state == 1 and lo < e9j and c > e9j and not brk:
                        st_e9t += 1; st_last_tag = _tag_e9ct(st_e9t); st_last_ts = float(hv[j][0])
                    elif st_state == 1 and c < e9j:
                        st_state = 2; st_last_tag = TAG_ET9_WAIT_F21C; st_last_ts = float(hv[j][0])
                    elif st_state == 1 and c >= e9j and not brk:
                        # E21C without a prior ETDN: prior close was under *that bar’s* EMA21, this close
                        # reclaims back above the current EMA21 (rare; needs EMAs not stacked e9>21).
                        pco = float(close_ser[j - 1])
                        e21_prev = float(e21_ser[j - 1])
                        if j >= 1 and pco < e21_prev and c > e21j:
                            st_e21c += 1; st_last_tag = f"E21C{st_e21c}"
                            st_last_ts = float(hv[j][0])
                    if st_state == 2 and c > e9j:
                        st_state = 1
                        # E21C = reclaimed EMA21 on the EMA9 reclaim bar, not the old touch+deep filter.
                        if c > e21j:
                            st_e21c += 1; st_last_tag = f"E21C{st_e21c}"
                        else:
                            st_e9t += 1; st_last_tag = _tag_e9ct(st_e9t)
                        st_last_ts = float(hv[j][0])
        except Exception:
            pass
        r["cycle_state"] = st_state
        r["state_name"] = "LOCKED" if st_state == 0 else ("TRENDING" if st_state == 1 else "PULLBACK")
        r["below21_count"] = st_below21
        r["b_count"] = st_b
        r["e9t_count"] = st_e9t
        r["e21c_count"] = st_e21c
        r["rst_count"] = st_rst
        r["last_tag"] = st_last_tag
        r["last_event_ts"] = st_last_ts
        r["cycle_last_bar_key"] = bar_key
        r["brk_b_anchor_close"] = float(st_b_anchor_close) if st_b_anchor_close > 0 else 0.0
        r["brk_b_anchor_ts"] = float(st_b_anchor_ts) if st_b_anchor_close > 0 else 0.0
        if st_last_don_c is not None:
            r["brk_lvl"] = st_last_don_c
        return

    if str(r.get("cycle_last_bar_key") or "") == bar_key:
        _anc0 = float(r.get("brk_b_anchor_close", 0.0) or 0.0)
        _lt0 = str(r.get("last_tag") or "")
        if (
            _anc0 <= 0.0
            and int(r.get("b_count", 0) or 0) > 0
            and _lt0.startswith("B")
        ):
            r["cycle_last_bar_key"] = ""
            _update_minimal_cycle_state(r, hv, don_len=don_len)
        return
    r["cycle_last_bar_key"] = bar_key

    state = int(r.get("cycle_state", 0) or 0)
    below21 = int(r.get("below21_count", 0) or 0)
    b_count = int(r.get("b_count", 0) or 0)
    e9t_count = int(r.get("e9t_count", 0) or 0)
    e21c_count = int(r.get("e21c_count", 0) or 0)
    rst_count = int(r.get("rst_count", 0) or 0)
    trend_ok = close > e9_ser[i] and e9_ser[i] > e21_ser[i]
    dlen = max(2, int(don_len))
    breakout = False
    if i >= dlen + 1:
        try:
            don_curr = float(np.max(highs[(i - dlen):i]))
            don_prev = float(np.max(highs[(i - dlen - 1):(i - 1)]))
            breakout = bool(trend_ok and close > don_curr and prev_close <= don_prev)
            r["brk_lvl"] = don_curr
        except Exception:
            breakout = False
    # Pine parity: below21 counter runs on all confirmed bars.
    below21 = below21 + 1 if close < e21_ser[i] else 0
    last_tag = str(r.get("last_tag") or "—")
    # Pine parity: only RST resets bCount / e9tCount / e21cCount; breakout just bumps bCount.
    if state > 0 and below21 >= 2:
        rst_count += 1
        state = 0; b_count = 0; e9t_count = 0; e21c_count = 0; last_tag = "RST"
        r["brk_b_anchor_close"] = 0.0
        r["brk_b_anchor_ts"] = 0.0
    elif breakout:
        state = 1
        b_count += 1
        last_tag = f"B{b_count}"
        if low <= e9_ser[i]:
            # Pine "Power Bar": breakout and EMA9 test same candle.
            last_tag = _tag_power_e9ct(last_tag)
        r["brk_b_anchor_close"] = close
        r["brk_b_anchor_ts"] = ts
    elif state > 0:
        # Pine's layout: state==1 transitions via if/elif, then a separate
        # if for state==2 reclaim so a 1→2 transition this bar cannot also reclaim.
        if state == 1 and low < e9_ser[i] and close > e9_ser[i] and not breakout:
            e9t_count += 1; last_tag = _tag_e9ct(e9t_count)
        elif state == 1 and close < e9_ser[i]:
            state = 2; last_tag = TAG_ET9_WAIT_F21C
        elif state == 1 and not breakout and close >= e9_ser[i]:
            # E21C without a prior ETDN: last close was under the prior EMA21; this close reclaims 21
            # (only matters when the stack is not e9>21, else this rarely fires in state 1).
            try:
                pc0 = float(prev[4])
                e21p = float(e21_ser[i - 1])
                e21_now = float(e21_ser[i])
                if i >= 1 and np.isfinite(e21p) and np.isfinite(e21_now) and pc0 < e21p and close > e21_now:
                    e21c_count += 1; last_tag = f"E21C{e21c_count}"
            except Exception:
                pass
        if state == 2 and close > e9_ser[i]:
            state = 1
            # E21C when the EMA9 reclaim bar also closes above EMA21; else shallow reclaim = E9T.
            if close > e21_ser[i]:
                e21c_count += 1; last_tag = f"E21C{e21c_count}"
            else:
                e9t_count += 1; last_tag = _tag_e9ct(e9t_count)
    r["cycle_state"] = state
    r["state_name"] = "LOCKED" if state == 0 else ("TRENDING" if state == 1 else "PULLBACK")
    r["below21_count"] = below21
    r["b_count"] = b_count
    r["e9t_count"] = e9t_count
    r["e21c_count"] = e21c_count
    r["rst_count"] = rst_count
    r["last_tag"] = last_tag
    r["last_event_ts"] = ts


def _weekly_ohlc5_from_daily_hv(hv: np.ndarray | None) -> np.ndarray | None:
    if hv is None or len(hv) < 5:
        return None
    week: dict[tuple[int, int], list[float]] = {}
    for row in hv:
        try:
            ts = float(row[0]); op = float(row[1]); hi = float(row[2]); lo = float(row[3]); cl = float(row[4])
        except Exception:
            continue
        d = _nse_ist_session_date_for_when(ts)
        if d is None:
            continue
        iso = d.isocalendar()
        k = (int(iso[0]), int(iso[1]))
        if k not in week:
            week[k] = [ts, op, hi, lo, cl]
        else:
            w = week[k]; w[0] = ts; w[2] = max(w[2], hi); w[3] = min(w[3], lo); w[4] = cl
    if len(week) < 4:
        return None
    keys = sorted(week.keys())
    return np.asarray([week[k] for k in keys], dtype=np.float64)


def _weekly_atr_stop_from_daily_hv(
    hv: np.ndarray | None,
    ltp: float,
    atr_period: int = 9,
    atr_mult: float = 2.0,
) -> float | None:
    """
    Weekly ATR stop proxy from daily OHLCV:
    - collapse to weekly OHLC
    - Wilder ATR(period) on weekly bars
    - stop = current LTP - atr_mult * weekly_atr
    """
    w = _weekly_ohlc5_from_daily_hv(hv)
    if w is None or len(w) < max(3, int(atr_period) + 1):
        return None
    try:
        high = np.asarray(w[:, 2], dtype=np.float64)
        low = np.asarray(w[:, 3], dtype=np.float64)
        close = np.asarray(w[:, 4], dtype=np.float64)
        n = int(max(2, atr_period))

        tr = np.zeros(len(close), dtype=np.float64)
        tr[0] = high[0] - low[0]
        for i in range(1, len(close)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i - 1])
            lc = abs(low[i] - close[i - 1])
            tr[i] = max(hl, hc, lc)

        atr = np.full(len(close), np.nan, dtype=np.float64)
        if len(close) <= n:
            return None
        atr[n - 1] = float(np.mean(tr[1:n]))
        for i in range(n, len(close)):
            atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n

        atr_last = atr[-1]
        if not np.isfinite(atr_last) and len(atr) > 1:
            atr_last = atr[-2]
        if not np.isfinite(atr_last) or atr_last <= 0:
            return None
        return float(ltp) - float(atr_mult) * float(atr_last)
    except Exception:
        return None


def _update_minimal_cycle_state_weekly(r: dict, hv: np.ndarray | None, don_len: int = 10) -> None:
    w = _weekly_ohlc5_from_daily_hv(hv)
    if w is None or len(w) < 2:
        return
    # Drop the in-progress ISO week before EMA/Donchian: those series are computed on *all*
    # rows of hv; a partial last week shifts EMA at every prior index vs TradingView weekly,
    # which can add an extra E21C (e.g. E21C8 here vs E21C7 on TV). Slice whenever the last
    # bar is in the current ISO week (any history length), but require >=6 *completed* weeks
    # of history after the drop to satisfy _update_minimal_cycle_state's min bar count.
    now_dt = datetime.now(_IST)
    t_last = float(w[-1][0])
    if not np.isfinite(t_last) or t_last <= 0:
        return
    d_last = _nse_ist_session_date_for_when(t_last)
    if d_last is None:
        return
    w_row = d_last.isocalendar()[:2]
    w_now = now_dt.date().isocalendar()[:2]
    w_run = w
    if w_row == w_now:
        w_run = np.asarray(w[:-1], dtype=np.float64)
    if len(w_run) < 6:
        return
    # Always full replay on weekly[] (empty cycle_last_bar_key) so last_tag_w / e21c_count_w
    # match a TradingView-style “confirmed weeks only” run. Incremental re-use of
    # cycle_last_bar_key_w kept stale counts after the weekly index fix (E21C8 vs TV E21C7)
    # until the key happened to change.
    tmp = {
        "cycle_state": 0,
        "below21_count": 0,
        "b_count": 0,
        "e9t_count": 0,
        "e21c_count": 0,
        "rst_count": 0,
        "last_tag": "—",
        "last_event_ts": 0.0,
        "cycle_last_bar_key": "",
        "brk_lvl": r.get("brk_lvl_w"),
        "brk_b_anchor_close": 0.0,
        "brk_b_anchor_ts": 0.0,
    }
    _update_minimal_cycle_state(tmp, w_run, don_len=don_len, weekly=True)
    cstate = int(tmp.get("cycle_state", 0) or 0)
    r["cycle_state_w"] = cstate
    r["state_name_w"] = "LOCKED" if cstate == 0 else ("TRENDING" if cstate == 1 else "PULLBACK")
    r["below21_count_w"] = int(tmp.get("below21_count", 0) or 0)
    r["b_count_w"] = int(tmp.get("b_count", 0) or 0)
    r["e9t_count_w"] = int(tmp.get("e9t_count", 0) or 0)
    r["e21c_count_w"] = int(tmp.get("e21c_count", 0) or 0)
    r["rst_count_w"] = int(tmp.get("rst_count", 0) or 0)
    r["last_tag_w"] = str(tmp.get("last_tag", "—") or "—")
    _let = float(tmp.get("last_event_ts", 0.0) or 0.0)
    r["last_event_ts_w"] = _nse_ist_cash_eod_ts_for_event_bar_ts(_let) if _let > 0.0 else 0.0
    r["cycle_last_bar_key_w"] = str(tmp.get("cycle_last_bar_key", "") or "")
    if tmp.get("brk_lvl") is not None:
        r["brk_lvl_w"] = tmp.get("brk_lvl")
    r["brk_b_anchor_close_w"] = float(tmp.get("brk_b_anchor_close", 0) or 0)
    r["brk_b_anchor_ts_w"] = float(tmp.get("brk_b_anchor_ts", 0) or 0)
    r["_wcycle_v"] = WEEKLY_CYCLE_PARITY_VERSION


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
                return True
        except Exception as e: LGR.error(f"Sync {s}: {e}")
        return False

    # Only fetch symbols whose RingBuffer is still empty. update_universe() now preserves
    # buffers for overlapping universes (Nifty 50 → Nifty 500 keeps the 50 already-loaded
    # symbols), so reloading the full 900 bars for every ticker on every navigation is wasted.
    def _is_empty(s):
        buf = self.buffers.get(s)
        return buf is None or buf.is_empty()

    if _is_empty(self.bench_sym):
        _fetch(self.bench_sym)
    to_fetch = [s for s in self.symbols if s != self.bench_sym and _is_empty(s)]
    t0 = time.time()
    if to_fetch:
        LGR.info(f"Sidecar history: fetching {len(to_fetch)} of {len(self.symbols)} symbols (rest already cached)")
        # Drain the map iterator so all fetches actually execute (Executor.map is lazy).
        with ThreadPoolExecutor(settings.SIDECAR_SYNC_WORKERS) as ex:
            list(ex.map(_fetch, to_fetch))
    else:
        LGR.info(f"Sidecar history: all {len(self.symbols)} symbols already cached (instant switch)")
    # Self-heal: for any symbol whose buffer is still empty, retry a few more times.
    # Local parquet reads rarely fail transiently, but the Fyers fallback path can; keep
    # a short, bounded retry loop so we do not stall the UI for a minute on fresh starts.
    max_retries = int(os.getenv("SIDECAR_HISTORY_RETRIES", "2"))
    retry_sleep = float(os.getenv("SIDECAR_HISTORY_RETRY_SLEEP", "1.5"))
    for attempt in range(max_retries):
        missing = [s for s in self.symbols if _is_empty(s)]
        if not missing:
            break
        LGR.warning(f"Sidecar history retry #{attempt + 1}: {len(missing)} symbols still empty")
        time.sleep(retry_sleep)
        with ThreadPoolExecutor(settings.SIDECAR_SYNC_WORKERS) as ex:
            list(ex.map(_fetch, missing))
    final_missing = [s for s in self.symbols if _is_empty(s)]
    dt = time.time() - t0
    if final_missing:
        LGR.warning(f"Sidecar history FAILED for {len(final_missing)} symbols after {dt:.1f}s: {final_missing[:20]}...")
    else:
        LGR.info(f"Sidecar history loaded for all {len(self.symbols)} symbols in {dt:.1f}s")

def main_loop_helper(self):
    loop_sleep = max(0.05, float(settings.SIDECAR_LOOP_SLEEP_SEC))
    while self.is_scanning:
        loop_t0 = time.time()
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
        cap = max(1, int(settings.SIDECAR_MAX_TASKS_PER_LOOP))
        if len(tasks) > cap:
            self.pending.update(tasks[cap:])
            tasks = tasks[:cap]
        b_vw = self.buffers[self.bench_sym].get_ordered_view() if self.bench_sym in self.buffers else None
        for s in tasks:
            # Stale `pending` tickers after `update_universe()` can still be processed once; new `results`
            # only has `all_s` keys—skip to avoid KeyError on `self.results[s]`.
            if s not in self.results or s not in self.buffers:
                continue
            if (idx := self.shm.get_idx(s)) is not None:
                row = self.arr[idx]

                # --- PRO EDITION: SIGNAL LINE & CROSSOVERS ---
                # Streaming MRS deque per symbol (length from quant_breakout_config); signal line = SMA(mrs_signal_period).
                # Only used by calculate_breakout_signals to label crossovers ("BUY NOW" when
                # mrs crosses its own signal line). None of the current breakout grids render
                # this label, so SIDECAR_MRS_SIGNAL_ENABLED=0 cleanly drops the deque work.
                p = merge_params_with_windows(self.params)
                current_mrs = float(row['mrs'])
                if settings.SIDECAR_MRS_SIGNAL_ENABLED:
                    if not hasattr(self, '_mrs_history_buffers'):
                        self._mrs_history_buffers = {}
                    mrs_period = int(p["mrs_signal_period"])
                    buf_max = int(p["mrs_history_buffer_max"])
                    if s not in self._mrs_history_buffers:
                        self._mrs_history_buffers[s] = {"mrs": deque(maxlen=buf_max)}
                    self._mrs_history_buffers[s]["mrs"].append(current_mrs)
                    mrs_deque = self._mrs_history_buffers[s]["mrs"]
                    mrs_signal = compute_mrs_signal_line(mrs_deque, mrs_period)
                else:
                    mrs_signal = 0.0
                hv = self.buffers[s].get_ordered_view()
                hv_d = collapse_sidecar_buffer_to_daily_ohlc(hv) if hv is not None else None
                hv_bar = hv_d if hv_d is not None and len(hv_d) >= 2 else hv
                # Recovery path: some symbols can be present in SHM/live feed but miss sidecar history
                # (bridge/db lag, late universe swap). Without history, LAST TAG / timing stays blank.
                if hv_bar is None or len(hv_bar) < 6:
                    try:
                        now_ts = time.time()
                        if not hasattr(self, "_symbol_hist_retry_ts"):
                            self._symbol_hist_retry_ts = {}
                        last_try = float(self._symbol_hist_retry_ts.get(s, 0.0))
                        if now_ts - last_try >= 120.0:
                            self._symbol_hist_retry_ts[s] = now_ts
                            d = self.bridge.get_historical_data(s, limit=900)
                            if d is None:
                                d = self.db.get_historical_data(s, "1d", limit=900)
                            if d is not None and len(d) > 0:
                                with self.lock:
                                    for rr in d:
                                        self.buffers[s].append(rr)
                                hv = self.buffers[s].get_ordered_view()
                                hv_d = collapse_sidecar_buffer_to_daily_ohlc(hv) if hv is not None else None
                                hv_bar = hv_d if hv_d is not None and len(hv_d) >= 2 else hv
                    except Exception:
                        pass
                b_bar = (
                    collapse_sidecar_buffer_to_daily_ohlc(b_vw)
                    if b_vw is not None
                    else None
                )
                b_bar = b_bar if b_bar is not None and len(b_bar) >= 2 else b_vw
                # Daily EMA30 context for pullback/pierce filters. Not rendered in the current
                # /breakout or /breakout-timing grids — kept behind a flag so users running the
                # Stage-1 box / RVCR backtests can re-enable it via SIDECAR_EMA30_ENABLED=1.
                if settings.SIDECAR_EMA30_ENABLED:
                    try:
                        if hv_bar is not None and len(hv_bar) >= 2:
                            cser = np.asarray(hv_bar[:, 4], dtype=np.float64)
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
                        _r = self.results.get(s)
                        if _r is not None:
                            _r["ema30"] = ema30_val
                            _r["ema30_prev"] = ema30_prev
                            _r["prev_close"] = prev_close

                # 2.4 Stage-1 price box (8+ week accumulation base)
                if settings.SIDECAR_STAGE1_BOX_ENABLED:
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
                        box_flag, box_weeks, box_range, vol_dry, vol_dry_ratio, ma_flat, ma_dev, stage2_confirm = _stage1_price_box_from_ohlcv(hv_bar)
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
                else:
                    box_flag = False
                    box_weeks = 0
                    box_range = 0.0
                    vol_dry = False
                    vol_dry_ratio = 0.0
                    ma_flat = False
                    ma_dev = 0.0
                    stage2_confirm = False
                with self.lock:
                    _r = self.results.get(s)
                    if _r is not None:
                        _r["stage1_box"] = bool(box_flag)
                        _r["stage1_box_weeks"] = int(box_weeks)
                        _r["stage1_box_range"] = float(box_range)
                        _r["stage1_vol_dry"] = bool(vol_dry)
                        _r["stage1_vol_dry_ratio"] = float(vol_dry_ratio)
                        _r["stage1_ma_flat"] = bool(ma_flat)
                        _r["stage1_ma_dev"] = float(ma_dev)
                        _r["stage2_confirm"] = bool(stage2_confirm)

                if not settings.SIDECAR_RVCR_ENABLED:
                    with self.lock:
                        _r = self.results.get(s)
                        if _r is not None:
                            _r["mrs_rcvr"] = False
                            _r["mrs_rcvr_slope"] = 0.0
                            _r["mrs_neg_ma10_rising"] = False
                            _r["mrs_rcvr_latched"] = False

                if settings.SIDECAR_RVCR_ENABLED:
                    # 2.5. RVCR (weekly-style): match TradingView weekly pane.
                    # - Compute weekly Mansfield mRS series from daily OHLC (hv_bar) + benchmark (b_bar).
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
                            _r = self.results.get(s)
                            if _r is not None:
                                _r["mrs_rcvr"] = bool(cached.get("flag", False))
                                _r["mrs_rcvr_slope"] = float(cached.get("slope", 0.0))
                                _r["mrs_neg_ma10_rising"] = bool(cached.get("neg_ma10_rising", False))
                    else:
                        flag = False
                        slope_val = 0.0
                        neg_ma10_rising = False
                        try:
                            wk_s = _weekly_close_map_from_ohlcv(hv_bar)
                            wk_b = _weekly_close_map_from_ohlcv(b_bar) if b_bar is not None else {}
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
                            _r = self.results.get(s)
                            if _r is not None:
                                _r["mrs_rcvr"] = bool(flag)
                                _r["mrs_rcvr_slope"] = float(slope_val)
                                _r["mrs_neg_ma10_rising"] = bool(neg_ma10_rising)

                    # Latch RVCR while mRS is below zero so Stage-1 candidates do not flicker.
                    with self.lock:
                        _r = self.results.get(s)
                        if _r is not None:
                            prev_latched = bool(_r.get("mrs_rcvr_latched", False))
                            curr_flag = bool(_r.get("mrs_rcvr", False))
                            if current_mrs < 0:
                                latched = prev_latched or curr_flag
                            else:
                                latched = False
                            _r["mrs_rcvr_latched"] = latched
                            _r["mrs_rcvr"] = latched

                # 3. Generate Pro Signature Signal
                with self.lock:
                    _r = self.results.get(s)
                if _r is None:
                    continue
                _hb_ts = None
                try:
                    if "heartbeat" in row.dtype.names:
                        _hb_ts = float(row["heartbeat"])
                except Exception:
                    pass
                _update_live_timing_breakout_status(
                    _r, float(row["ltp"]), datetime.now(_IST), _hb_ts
                )
                p["rs_rating_info"] = {
                    "rs_rating": int(row['rs_rating']),
                    "mrs": current_mrs,
                    "mrs_prev": float(row['mrs_prev']) if 'mrs_prev' in row.dtype.names else current_mrs,
                    "mrs_signal": mrs_signal,
                    "mrs_rcvr": bool(_r.get("mrs_rcvr", False)),
                    "stage1_box": bool(_r.get("stage1_box", False)),
                    "mrs_neg_ma10_rising": bool(_r.get("mrs_neg_ma10_rising", False)),
                    "stage2_confirm": bool(_r.get("stage2_confirm", False)),
                }
                try:
                    res = calculate_breakout_signals(s, hv_bar, b_bar, p)
                    if res:
                        _r.update(res)
                        # SHM `status` is owned by the master (e.g. BUY NOW on mRS cross). Do not mirror
                        # breakout labels (STAGE 2, …) here — they overwrite and flicker vs the RS grid.
                        # Breakout page uses self.results + format_ui_row only.
                    raw_pw = int(p["pivot_high_window"])
                    pw_cap = max(1, min(raw_pw, 500))
                    hv_for_breakout = trim_series_after_corporate_action(hv_bar) if hv_bar is not None else None
                    pw_use = effective_pivot_window(len(hv_for_breakout), pw_cap) if hv_for_breakout is not None else None
                    if pw_use is not None and hv_for_breakout is not None:
                        _r["brk_lvl"] = float(detect_pivot_high(hv_for_breakout[:-1, 2], pw_use))

                    # Daily + weekly EMA9/EMA21 stacks feed the TREND_OK dropdown filter and
                    # the (unrendered) ema_d_str / ema_w_str / tf_ema display fields. Behind
                    # a flag because 4× 900-bar EMA per task is a notable chunk of loop CPU.
                    # brk_lvl_w still gets computed regardless — it's the weekly pivot level
                    # and is what the sidecar's own /breakout UI renders.
                    ema_fast = max(2, int(settings.UDAI_EMA_FAST))
                    ema_slow = max(3, int(settings.UDAI_EMA_SLOW))
                    if settings.SIDECAR_EMA_STACK_ENABLED:
                        if hv_bar is not None and len(hv_bar) >= ema_slow + 2:
                            cser = np.asarray(hv_bar[:, 4], dtype=np.float64)
                            e9d = _ema_series(cser, ema_fast)
                            e21d = _ema_series(cser, ema_slow)
                            e9dv, e21dv = float(e9d[-1]), float(e21d[-1])
                            d_ok = (
                                np.isfinite(e9dv)
                                and np.isfinite(e21dv)
                                and e9dv > e21dv
                            )
                            _r["ema9_d"] = e9dv if np.isfinite(e9dv) else None
                            _r["ema21_d"] = e21dv if np.isfinite(e21dv) else None
                            _r["daily_ema_stack_ok"] = bool(d_ok)
                        else:
                            _r["ema9_d"] = None
                            _r["ema21_d"] = None
                            _r["daily_ema_stack_ok"] = False

                    wc = _weekly_high_close_series_from_hv(hv_for_breakout) if hv_for_breakout is not None else None
                    if wc is not None:
                        wh, wcl = wc
                        pw_w = effective_pivot_window(len(wh), pw_cap)
                        if pw_w is not None and len(wh) >= pw_w + 1:
                            _r["brk_lvl_w"] = float(detect_pivot_high(wh[:-1], pw_w))
                        else:
                            _r["brk_lvl_w"] = None
                        if settings.SIDECAR_EMA_STACK_ENABLED:
                            if wcl.size >= ema_slow + 1:
                                e9w = _ema_series(wcl, ema_fast)
                                e21w = _ema_series(wcl, ema_slow)
                                e9wv, e21wv = float(e9w[-1]), float(e21w[-1])
                                w_ok = (
                                    np.isfinite(e9wv)
                                    and np.isfinite(e21wv)
                                    and e9wv > e21wv
                                )
                                _r["ema9_w"] = e9wv if np.isfinite(e9wv) else None
                                _r["ema21_w"] = e21wv if np.isfinite(e21wv) else None
                                _r["weekly_ema_stack_ok"] = bool(w_ok)
                            else:
                                _r["ema9_w"] = None
                                _r["ema21_w"] = None
                                _r["weekly_ema_stack_ok"] = False
                    else:
                        _r["brk_lvl_w"] = None
                        if settings.SIDECAR_EMA_STACK_ENABLED:
                            _r["ema9_w"] = None
                            _r["ema21_w"] = None
                            _r["weekly_ema_stack_ok"] = False

                    if settings.SIDECAR_EMA_STACK_ENABLED:
                        d_stack = bool(_r.get("daily_ema_stack_ok"))
                        w_stack = bool(_r.get("weekly_ema_stack_ok"))
                        _r["dual_tf_ema_stack_ok"] = d_stack and w_stack
                        _r["dual_tf_stack_score"] = int(d_stack) + int(w_stack)
                    _update_minimal_cycle_state(
                        _r,
                        hv_for_breakout,
                        don_len=max(2, int(p.get("pivot_high_window", settings.BREAKOUT_PIVOT_HIGH_WINDOW))),
                    )
                    _update_minimal_cycle_state_weekly(
                        _r,
                        hv_for_breakout,
                        don_len=max(2, int(p.get("pivot_high_window", settings.BREAKOUT_PIVOT_HIGH_WINDOW))),
                    )
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
                            with self.lock:
                                _ru = self.results.get(s)
                            lp = float((_ru.get("ltp", 0) if _ru else 0) or float(row["ltp"]))
                            u = compute_udai_pine(
                                d_hist,
                                lp,
                                st,
                                ema_fast=settings.UDAI_EMA_FAST,
                                ema_slow=settings.UDAI_EMA_SLOW,
                                breakout_period=settings.UDAI_BREAKOUT_PERIOD,
                                require_price_above_emas=settings.UDAI_REQUIRE_PRICE_ABOVE_EMAS,
                                atr_period=settings.UDAI_ATR_PERIOD,
                                atr_mult=settings.UDAI_ATR_MULT,
                                risk_pct=settings.UDAI_RISK_PCT,
                                account_equity=settings.UDAI_ACCOUNT_EQUITY,
                            )
                            w_stop = _weekly_atr_stop_from_daily_hv(
                                d_hist,
                                lp,
                                atr_period=settings.UDAI_ATR_PERIOD,
                                atr_mult=settings.UDAI_ATR_MULT,
                            )
                            if w_stop is not None:
                                u["weekly_stop_price"] = float(w_stop)
                            self.udai_state[s] = st
                            if _ru is not None:
                                _ru.update(u)
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

        # Pace the loop: if work took longer than loop_sleep, still pause one full slot so the
        # host does not sit at ~100% CPU (leading sleep alone does not help when work >> sleep).
        elapsed = time.time() - loop_t0
        if elapsed < loop_sleep:
            time.sleep(loop_sleep - elapsed)
        else:
            time.sleep(loop_sleep)

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
                    _rm = self.results.get(s)
                    if _rm is not None:
                        _rm["m_rsi2"] = None
                        _rm["m_rsi2_live"] = False
                continue
            arr = np.asarray(d_hist)
            base = daily_close_series_from_ohlcv(arr)
            if base is None:
                with self.lock:
                    _rm = self.results.get(s)
                    if _rm is not None:
                        _rm["m_rsi2"] = None
                        _rm["m_rsi2_live"] = False
                continue
            with self.lock:
                _rm = self.results.get(s)
                lp = float(_rm.get("ltp", 0) or 0) if _rm is not None else 0.0
            series = base
            used_live = False
            if live_ok and lp > 0:
                series = blend_last_daily_bar_with_ltp(base, lp)
                used_live = True
            lr = latest_monthly_rsi2(series, period=2)
            with self.lock:
                _rm = self.results.get(s)
                if _rm is not None:
                    if lr:
                        _rm["m_rsi2"] = float(lr[1])
                        _rm["m_rsi2_live"] = used_live
                    else:
                        _rm["m_rsi2"] = None
                        _rm["m_rsi2_live"] = False
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


def _fmt_last_event_ist(ts_raw) -> str:
    """Bar / event unix time → IST wall clock for sidecar timing page."""
    try:
        t = float(ts_raw or 0.0)
        if t <= 0:
            return "—"
        dt_utc = datetime.fromtimestamp(t, tz=timezone.utc)
        # Parquet / vendors often key daily rows at 00:00 UTC → 05:30 IST; map to NSE-style EOD display.
        if (
            dt_utc.microsecond == 0
            and dt_utc.second == 0
            and dt_utc.minute == 0
            and dt_utc.hour == 0
        ):
            d_ist = _nse_ist_session_date_for_when(t)
            if d_ist is None:
                return "—"
            h = int(settings.CYCLE_SAME_DAY_BAR_FRIDAY_EOD_HOUR)
            m = int(settings.CYCLE_SAME_DAY_BAR_FRIDAY_EOD_MINUTE)
            close_dt = datetime.combine(d_ist, dt_time(h, m), tzinfo=_IST)
            return close_dt.strftime("%Y-%m-%d %H:%M:%S IST")
        return datetime.fromtimestamp(t, tz=_IST).strftime("%Y-%m-%d %H:%M:%S IST")
    except Exception:
        return "—"


def compute_breakout_setup_score_row(d: dict) -> int:
    """
    0–100 heuristic rank for /breakout sorting (tape + cycle context).
    Not investment advice.
    """
    try:
        chp = float(d.get("change_pct", 0.0) or 0.0)
    except (TypeError, ValueError):
        chp = 0.0
    try:
        rv = float(d.get("rv", 0.0) or 0.0)
    except (TypeError, ValueError):
        rv = 0.0
    try:
        mrs = float(d.get("mrs", 0.0) or 0.0)
    except (TypeError, ValueError):
        mrs = 0.0
    try:
        ltp = float(d.get("ltp", 0.0) or 0.0)
    except (TypeError, ValueError):
        ltp = 0.0
    try:
        rsr_raw = d.get("rs_rating")
        rsr = int(rsr_raw) if rsr_raw is not None else None
    except (TypeError, ValueError):
        rsr = None

    pts = 0.0
    if rsr is not None and rsr > 0:
        pts += min(28.0, rsr * 0.28)
    else:
        pts += 10.0

    pts += min(22.0, max(0.0, rv) * 8.0)
    pts += max(0.0, min(18.0, 8.0 + mrs * 2.5))

    if chp >= 0:
        pts += min(10.0, 2.0 + chp * 0.35)
    else:
        pts += max(-8.0, chp * 0.45)

    ba = float(d.get("brk_b_anchor_close", 0.0) or 0.0)
    if ba > 0 and ltp > 0:
        pbd = ((ltp / ba) - 1.0) * 100.0
        if pbd >= 0:
            pts += min(12.0, pbd * 0.95)
        else:
            pts += max(-10.0, pbd * 0.85)

    baw = float(d.get("brk_b_anchor_close_w", 0.0) or 0.0)
    if baw > 0 and ltp > 0:
        pbw = ((ltp / baw) - 1.0) * 100.0
        if pbw >= 0:
            pts += min(7.0, pbw * 0.65)
        else:
            pts += max(-6.0, pbw * 0.45)

    if bool(d.get("dual_tf_ema_stack_ok")):
        pts += 8.0
    if bool(d.get("is_breakout", False)):
        pts += 5.0

    lt = str(d.get("last_tag") or "").upper()
    if lt.startswith("B"):
        pts += 4.0

    return int(round(max(0.0, min(100.0, pts))))


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
    brk_w = d.get("brk_lvl_w")
    brk_w_disp = f"{float(brk_w):.2f}" if brk_w is not None else "—"
    d_st = bool(d.get("daily_ema_stack_ok"))
    w_st = bool(d.get("weekly_ema_stack_ok"))
    tf_ema_disp = ("D✓" if d_st else "D—") + " " + ("W✓" if w_st else "W—")
    e9d, e21d = d.get("ema9_d"), d.get("ema21_d")
    e9w, e21w = d.get("ema9_w"), d.get("ema21_w")
    ema_d_str = (
        f"{float(e9d):.1f}>{float(e21d):.1f}"
        if e9d is not None and e21d is not None
        else "—"
    )
    ema_w_str = (
        f"{float(e9w):.1f}>{float(e21w):.1f}"
        if e9w is not None and e21w is not None
        else "—"
    )
    ema_stack_tooltip = f"{ema_d_str} | {ema_w_str}"
    sp = d.get("stop_price")
    stop_disp = f"{float(sp):.2f}" if sp is not None else "—"
    wsp = d.get("weekly_stop_price")
    weekly_stop_disp = f"{float(wsp):.2f}" if wsp is not None else "—"
    try:
        _ltp_num = float(d.get("ltp", 0.0) or 0.0)
    except (TypeError, ValueError):
        _ltp_num = 0.0
    try:
        _sp_num = float(wsp) if wsp is not None else float("nan")
    except (TypeError, ValueError):
        _sp_num = float("nan")
    atr_below = bool(np.isfinite(_sp_num) and _ltp_num > 0 and _ltp_num < _sp_num)
    atr_state_ui = "BELOW" if atr_below else "ABOVE"
    atr_state_color = "#FF3131" if atr_below else "#00FF00"
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
    _ttd = str(d.get("timing_last_tag") or d.get("last_tag") or "—")
    _ttw = str(d.get("timing_last_tag_w") or d.get("last_tag_w") or "—")
    _ttd_ts = float(d.get("timing_last_event_ts", d.get("last_event_ts", 0.0)) or 0.0)
    _ttw_ts = float(d.get("timing_last_event_ts_w", d.get("last_event_ts_w", 0.0)) or 0.0)
    d_pending = bool(str(d.get("cb_pending_day_d") or "").strip())
    w_pending = bool(str(d.get("cb_pending_week_w") or "").strip())
    # Query-time fallback rows may not carry full cycle pending fields; keep CB as live in that case.
    if _ttd.startswith("CB") and d.get("timing_state_name") == "LIVE BREAKOUT":
        d_pending = True
    if _ttw.startswith("CB") and d.get("timing_state_name_w") == "LIVE BREAKOUT":
        w_pending = True
    timing_state_d = _timing_state_from_tag(_ttd, d_pending)
    timing_state_w = _timing_state_from_tag(_ttw, w_pending)
    # % move since last structural B bar (close on that bar → current LTP). Cleared on RST.
    brk_move_pct = None
    brk_move_ui = "—"
    brk_move_band = "—"
    brk_move_color = "#888888"
    # % FROM B tracks move from breakout LEVEL (Donchian), not from live captured entry.
    _b_anchor = float(d.get("brk_lvl", 0.0) or 0.0)
    _b_anchor_ts = float(d.get("brk_b_anchor_ts", 0.0) or 0.0)
    brk_b_anchor_dt = _fmt_last_event_ist(_b_anchor_ts) if _b_anchor_ts > 0 else "—"
    try:
        if _b_anchor > 0 and _ltp_num > 0:
            brk_move_pct = ((_ltp_num / _b_anchor) - 1.0) * 100.0
            brk_move_ui = f"{brk_move_pct:+.2f}%"
            brk_move_band = "Breakout level"
            if brk_move_pct > 0:
                brk_move_color = "#00FF00"
            elif brk_move_pct < 0:
                brk_move_color = "#FF3131"
            else:
                brk_move_color = "#D1D1D1"
    except Exception:
        pass

    brk_move_pct_w = None
    brk_move_ui_w = "—"
    brk_move_color_w = "#888888"
    _b_anchor_w = float(d.get("brk_lvl_w", 0.0) or 0.0)
    _b_anchor_ts_w = float(d.get("brk_b_anchor_ts_w", 0.0) or 0.0)
    brk_b_anchor_dt_w = _fmt_last_event_ist(_b_anchor_ts_w) if _b_anchor_ts_w > 0 else "—"
    try:
        if _b_anchor_w > 0 and _ltp_num > 0:
            brk_move_pct_w = ((_ltp_num / _b_anchor_w) - 1.0) * 100.0
            brk_move_ui_w = f"{brk_move_pct_w:+.2f}%"
            if brk_move_pct_w > 0:
                brk_move_color_w = "#00FF00"
            elif brk_move_pct_w < 0:
                brk_move_color_w = "#FF3131"
            else:
                brk_move_color_w = "#D1D1D1"
    except Exception:
        pass

    # % since LTP when price first crossed brk_lvl this IST day (timing CB), not structural B close.
    brk_move_live_ui = "—"
    brk_move_live_color = "#666666"
    _live_px_d = float(d.get("cb_live_entry_px_d", 0.0) or 0.0)
    try:
        if _live_px_d > 0 and _ltp_num > 0:
            _lmd = ((_ltp_num / _live_px_d) - 1.0) * 100.0
            brk_move_live_ui = f"{_lmd:+.2f}%"
            if _lmd > 0:
                brk_move_live_color = "#00FF00"
            elif _lmd < 0:
                brk_move_live_color = "#FF3131"
            else:
                brk_move_live_color = "#D1D1D1"
    except Exception:
        pass

    brk_move_live_ui_w = "—"
    brk_move_live_color_w = "#666666"
    _live_px_w = float(d.get("cb_live_entry_px_w", 0.0) or 0.0)
    try:
        if _live_px_w > 0 and _ltp_num > 0:
            _lmw = ((_ltp_num / _live_px_w) - 1.0) * 100.0
            brk_move_live_ui_w = f"{_lmw:+.2f}%"
            if _lmw > 0:
                brk_move_live_color_w = "#00FF00"
            elif _lmw < 0:
                brk_move_live_color_w = "#FF3131"
            else:
                brk_move_live_color_w = "#D1D1D1"
    except Exception:
        pass

    # RS Rating (0-100 percentile from the master scanner). Colour ramp: ≥80 strong (green),
    # 60-79 neutral-green, 40-59 grey, <40 weak (red). `rs_rating` may be absent when SHM has
    # not yet rolled the daily rank for a symbol — surface "—" so the UI doesn't render 0.
    try:
        _rsr_raw = d.get("rs_rating")
        _rsr = int(_rsr_raw) if _rsr_raw is not None else None
    except (TypeError, ValueError):
        _rsr = None
    if _rsr is None or _rsr <= 0:
        rs_rating_ui, rs_rating_color = "—", "#888888"
    else:
        rs_rating_ui = str(_rsr)
        if _rsr >= 80:
            rs_rating_color = "#00FF00"
        elif _rsr >= 60:
            rs_rating_color = "#88FFAA"
        elif _rsr >= 40:
            rs_rating_color = "#D1D1D1"
        else:
            rs_rating_color = "#FF6666"

    # After RST, b_count is reset; the next Donchian + EMA-stack breakout prints B1 (same as a cold cycle).
    _lt_d_u = str(d.get("last_tag") or "").strip().upper()
    _lt_w_u = str(d.get("last_tag_w") or "").strip().upper()
    post_rst_hint_d = "Post-RST → next tag B1" if _lt_d_u == "RST" else ""
    post_rst_hint_w = "Post-RST → next tag B1" if _lt_w_u == "RST" else ""
    _pr_parts = []
    if post_rst_hint_d:
        _pr_parts.append("Daily: post-RST → B1")
    if post_rst_hint_w:
        _pr_parts.append("Weekly: post-RST → B1")
    post_rst_hint_dw = "  |  ".join(_pr_parts) if _pr_parts else ""

    try:
        _sc_raw = d.get("setup_score")
        _sc = int(_sc_raw) if _sc_raw is not None else compute_breakout_setup_score_row(d)
    except (TypeError, ValueError):
        _sc = compute_breakout_setup_score_row(d)
    if _sc >= 75:
        setup_score_color = "#00FF00"
    elif _sc >= 55:
        setup_score_color = "#FFB000"
    elif _sc >= 40:
        setup_score_color = "#D1D1D1"
    else:
        setup_score_color = "#FF6666"
    setup_score_ui = str(_sc)

    d.update({
        'symbol': ui_s, 'chp': f"{chp:+.2f}%", 'chp_color': chp_color,
        'rs_rating': rs_rating_ui, 'rs_rating_color': rs_rating_color,
        'rv': f"{rv:.2f}", 'rv_color': "#00FF00" if rv >= 1.5 else "#D1D1D1",
        'trend_text': "UP" if d.get('trend_up') else "DOWN", 'trend_color': "#00FF00" if d.get('trend_up') else "#FF3131",
        'ema_str': ema_d_str,
        'ema_f_val': float(e9d) if e9d is not None else 0.0,
        'ema_s_val': float(e21d) if e21d is not None else 0.0,
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
        'brk_move_pct': brk_move_ui,
        'brk_move_band': brk_move_band,
        'brk_move_color': brk_move_color,
        'brk_b_anchor_dt': brk_b_anchor_dt,
        'brk_move_pct_w': brk_move_ui_w,
        'brk_move_color_w': brk_move_color_w,
        'brk_move_live_pct': brk_move_live_ui,
        'brk_move_live_color': brk_move_live_color,
        'brk_move_live_pct_w': brk_move_live_ui_w,
        'brk_move_live_color_w': brk_move_live_color_w,
        'brk_b_anchor_dt_w': brk_b_anchor_dt_w,
        'brk_lvl_w': brk_w_disp,
        'tf_ema': tf_ema_disp,
        'ema_d_str': ema_d_str,
        'ema_w_str': ema_w_str,
        'ema_stack_tooltip': ema_stack_tooltip,
        'dual_tf_ema_stack_ok': bool(d.get("dual_tf_ema_stack_ok")),
        'stop_price': stop_disp,
        'weekly_stop_price': weekly_stop_disp,
        'atr9x2_state': atr_state_ui,
        'atr9x2_color': atr_state_color,
        'udai_ui': udai_disp,
        'm_rsi2_ui': mrsi_ui,
        'm_rsi2_color': mrsi_color,
        'is_breakout': bool(d.get('is_breakout', False)),
        'state_name': str(d.get("state_name") or "LOCKED"),
        'post_rst_hint_d': post_rst_hint_d,
        'post_rst_hint_w': post_rst_hint_w,
        'post_rst_hint_dw': post_rst_hint_dw,
        'last_tag': str(d.get("last_tag") or "—"),
        'b_count': int(d.get("b_count", 0) or 0),
        'e9t_count': int(d.get("e9t_count", 0) or 0),
        'e21c_count': int(d.get("e21c_count", 0) or 0),
        'rst_count': int(d.get("rst_count", 0) or 0),
        'below21_count': int(d.get("below21_count", 0) or 0),
        'state_name_w': str(d.get("state_name_w") or "LOCKED"),
        'last_tag_w': str(d.get("last_tag_w") or "—"),
        'b_count_w': int(d.get("b_count_w", 0) or 0),
        'e9t_count_w': int(d.get("e9t_count_w", 0) or 0),
        'e21c_count_w': int(d.get("e21c_count_w", 0) or 0),
        'rst_count_w': int(d.get("rst_count_w", 0) or 0),
        'below21_count_w': int(d.get("below21_count_w", 0) or 0),
        'age_mins': (
            f"{int(max(0.0, (time.time() - float(d.get('last_event_ts', 0.0) or 0.0)) / 60.0))}m"
            if float(d.get('last_event_ts', 0.0) or 0.0) > 0 else "—"
        ),
        'age_mins_w': (
            f"{int(max(0.0, (time.time() - float(d.get('last_event_ts_w', 0.0) or 0.0)) / 60.0))}m"
            if float(d.get('last_event_ts_w', 0.0) or 0.0) > 0 else "—"
        ),
        'last_tag_color': (
            "#00FF00" if str(d.get("last_tag", "")).startswith("B")
            else "#1565C0" if _is_e9ct_tag(str(d.get("last_tag", "")))
            else "#E65100" if _is_et9dn_wait_tag(str(d.get("last_tag", "")))
            else "#6A1B9A" if str(d.get("last_tag", "")).startswith("E21C")
            else "#C62828" if str(d.get("last_tag", "")).startswith("RST")
            else "#888888"
        ),
        'last_tag_color_w': (
            "#00FF00" if str(d.get("last_tag_w", "")).startswith("B")
            else "#1565C0" if _is_e9ct_tag(str(d.get("last_tag_w", "")))
            else "#E65100" if _is_et9dn_wait_tag(str(d.get("last_tag_w", "")))
            else "#6A1B9A" if str(d.get("last_tag_w", "")).startswith("E21C")
            else "#C62828" if str(d.get("last_tag_w", "")).startswith("RST")
            else "#888888"
        ),
        'last_event_dt': _fmt_last_event_ist(d.get("last_event_ts")),
        'last_event_dt_w': _fmt_last_event_ist(d.get("last_event_ts_w")),
        'timing_last_tag': _ttd,
        'timing_last_tag_w': _ttw,
        'timing_last_event_dt': _fmt_last_event_ist(_ttd_ts),
        'timing_last_event_dt_w': _fmt_last_event_ist(_ttw_ts),
        'timing_state_name': timing_state_d,
        'timing_state_name_w': timing_state_w,
        'timing_last_tag_color': (
            "#00FF00" if _ttd.startswith("B")
            else "#00E5FF" if _ttd.startswith("CB")
            else "#1565C0" if _is_e9ct_tag(_ttd)
            else "#E65100" if _is_et9dn_wait_tag(_ttd)
            else "#6A1B9A" if _ttd.startswith("E21C")
            else "#C62828" if _ttd.startswith("RST")
            else "#888888"
        ),
        'timing_last_tag_color_w': (
            "#00FF00" if _ttw.startswith("B")
            else "#00E5FF" if _ttw.startswith("CB")
            else "#1565C0" if _is_e9ct_tag(_ttw)
            else "#E65100" if _is_et9dn_wait_tag(_ttw)
            else "#6A1B9A" if _ttw.startswith("E21C")
            else "#C62828" if _ttw.startswith("RST")
            else "#888888"
        ),
        'timing_age_mins': (
            f"{int(max(0.0, (time.time() - _ttd_ts) / 60.0))}m" if _ttd_ts > 0 else "—"
        ),
        'timing_age_mins_w': (
            f"{int(max(0.0, (time.time() - _ttw_ts) / 60.0))}m" if _ttw_ts > 0 else "—"
        ),
        'setup_score': _sc,
        'setup_score_ui': setup_score_ui,
        'setup_score_color': setup_score_color,
    })
    d.pop("_wcycle_v", None)
    return d
