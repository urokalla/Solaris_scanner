import os
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

_IST = ZoneInfo("Asia/Kolkata")

from utils.quant_breakout_config import get_breakout_window_dict


def collapse_sidecar_buffer_to_daily_ohlc(hv: np.ndarray | None) -> np.ndarray | None:
    """
    Sidecar tape mixes Parquet **daily** rows with many **live** rows (each tick as O=H=L=C=LTP).

    Collapse to **one OHLCV bar per IST calendar day** (Asia/Kolkata) so pivot highs, EMAs, and week
    maps match an **NSE-style daily** chart (e.g. TradingView 20-session high excluding today).

    Input/output columns: ``[timestamp, open, high, low, close, volume]`` (same as PipelineBridge).
    """
    if hv is None or len(hv) < 1:
        return None
    rows: list[tuple] = []
    for row in hv:
        try:
            ts = float(row[0])
            o, hi, lo, cl = float(row[1]), float(row[2]), float(row[3]), float(row[4])
            vol = float(row[5]) if row.shape[0] > 5 else 0.0
        except Exception:
            continue
        if not np.isfinite(ts) or not all(np.isfinite(x) for x in (o, hi, lo, cl)):
            continue
        if hi < lo or hi <= 0:
            continue
        d = datetime.fromtimestamp(ts, tz=_IST).date()
        rows.append((d, ts, o, hi, lo, cl, vol))
    if not rows:
        return None
    out: list[list[float]] = []
    cur_d = None
    bucket: list[float] | None = None
    for d, ts, o, hi, lo, cl, vol in rows:
        if cur_d is None:
            cur_d = d
            bucket = [ts, o, hi, lo, cl, vol]
        elif d != cur_d:
            if bucket is not None:
                out.append(bucket)
            cur_d = d
            bucket = [ts, o, hi, lo, cl, vol]
        else:
            if bucket is None:
                bucket = [ts, o, hi, lo, cl, vol]
            else:
                bucket[2] = max(bucket[2], hi)
                bucket[3] = min(bucket[3], lo)
                bucket[4] = cl
                bucket[5] += vol
                bucket[0] = ts
    if bucket is not None:
        out.append(bucket)
    if len(out) < 1:
        return None
    return np.asarray(out, dtype=np.float64)


def detect_pivot_high(arr, window=20):
    """Vectorized pivot high detection (<50 lines). Always returns a native Python float (Reflex JSON)."""
    if len(arr) < window:
        return 0.0
    return float(np.max(arr[-window:]))


def effective_pivot_window(n_bars: int, pivot_w: int) -> int | None:
    """
    Donchian-style lookback on **completed** bars: we compute pivot from ``h[:-1, 2]`` (excludes the
    current / forming bar), so usable width is ``n_bars - 1``.

    Use ``min(pivot_w, n_completed)`` — not ``n_bars - 2`` — so e.g. 20 prior sessions + today
    yields a full **20-day** high, matching typical daily-chart breakout levels.
    """
    if n_bars < 2:
        return None
    n_completed = n_bars - 1
    w = min(int(pivot_w), n_completed)
    return max(1, w)


def trim_series_after_corporate_action(
    h: np.ndarray | None, drop_threshold: float = 0.60, up_threshold: float = 2.50
) -> np.ndarray | None:
    """
    Trim price series to the most recent regime after a split/bonus-like jump.

    We detect abrupt close-to-close jumps and keep bars after the latest event:
    - large down jump (default <= -60%)
    - large up jump   (default >= +250%)
    """
    if h is None or len(h) < 3:
        return h
    try:
        c = np.asarray(h[:, 4], dtype=np.float64)
    except Exception:
        return h
    if c.size < 3:
        return h
    prev = c[:-1]
    curr = c[1:]
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = (curr / prev) - 1.0
    evt = np.where((ret <= -abs(drop_threshold)) | (ret >= abs(up_threshold)))[0]
    if evt.size == 0:
        return h
    cut = int(evt[-1] + 1)
    # Need enough bars for pivot calculations after trim.
    if cut >= len(h) - 1:
        return h
    return h[cut:]


def compute_mrs_signal_line(mrs_history, period: int) -> float:
    """SMA of the last ``period`` MRS samples; if fewer samples, use the last value."""
    if mrs_history is None:
        return 0.0
    seq = np.asarray(list(mrs_history), dtype=np.float64)
    if seq.size == 0:
        return 0.0
    if len(seq) >= period:
        return float(np.mean(seq[-period:]))
    return float(seq[-1])


def session_rvol(session_cumulative_volume, avg_daily_volume_21d: float) -> float:
    """
    Single source for RVOL: today's cumulative session volume / 21-day average daily volume.
    Used by MasterScanner SHM and any breakout/UI path that imports this helper.
    """
    a = float(avg_daily_volume_21d) if avg_daily_volume_21d is not None else 0.0
    if not np.isfinite(a) or a <= 0:
        return 0.0
    if session_cumulative_volume is None:
        return 0.0
    s = float(session_cumulative_volume)
    if not np.isfinite(s) or s < 0:
        return 0.0
    return s / a


def compute_rvol_vectorized(vol, avg_vol):
    """Same formula as live grid; rounds for breakout batch code."""
    return round(session_rvol(vol, avg_vol), 2)


def generate_breakout_signal(symbol, h, bench_h, params):
    """Pro Edition Signature: Price Breakout + RS Stage 2."""
    wd = get_breakout_window_dict()
    raw_pw = int(params.get("pivot_high_window", wd["pivot_high_window"]))
    pivot_w = max(1, min(raw_pw, 500))
    min_bars = int(params.get("min_intraday_bars_for_breakout", wd["min_intraday_bars_for_breakout"]))

    h_raw = h
    h_daily = collapse_sidecar_buffer_to_daily_ohlc(h_raw) if h_raw is not None else None
    if h_daily is not None and len(h_daily) >= 2:
        h = trim_series_after_corporate_action(h_daily)
        # Today + pivot_w completed dailies is enough for a full pivot_w Donchian on ``h[:-1]``.
        min_need = max(pivot_w + 1, 15)
    else:
        h = trim_series_after_corporate_action(h_raw)
        min_need = min_bars

    # Provide basic status even if history is still syncing
    rs_info = params.get("rs_rating_info", {})
    mrs = float(rs_info.get("mrs", 0.0))
    stage1_box = bool(rs_info.get("stage1_box", False))
    mrs_neg_ma10_rising = bool(rs_info.get("mrs_neg_ma10_rising", False))

    # Pivot / "breakout level": use adaptive window when tape is shorter than pivot_w+1 bars.
    def _pivot_break_level():
        if h is None:
            return None
        pw_use = effective_pivot_window(len(h), pivot_w)
        if pw_use is None:
            return None
        return float(detect_pivot_high(h[:-1, 2], pw_use))

    brk_lvl = _pivot_break_level()

    mrs_rcvr = bool(rs_info.get("mrs_rcvr", False))
    if h is None or len(h) < min_need:
        if mrs > 0:
            return {"status": "STAGE 2", "trend_up": True, "mrs": mrs, "brk_lvl": brk_lvl}
        if mrs_rcvr:
            return {"status": "STAGE 1", "trend_up": False, "mrs": mrs, "brk_lvl": brk_lvl}
        return {"status": "STAGE 4", "trend_up": False, "mrs": mrs, "brk_lvl": brk_lvl}

    curr = h[-1, 4]
    pw_use = effective_pivot_window(len(h), pivot_w) or pivot_w
    high_prior = detect_pivot_high(h[:-1, 2], pw_use)
    
    # RS Info from SHM (Single Source of Truth)
    rs_info = params.get("rs_rating_info", {})
    mrs = float(rs_info.get("mrs", 0.0))
    mrs_prev = float(rs_info.get("mrs_prev", 0.0))
    mrs_sig = float(rs_info.get("mrs_signal", 0.0))
    mrs_rcvr = bool(rs_info.get("mrs_rcvr", False))
    stage1_box = bool(rs_info.get("stage1_box", False))
    mrs_neg_ma10_rising = bool(rs_info.get("mrs_neg_ma10_rising", False))
    stage2_confirm = bool(rs_info.get("stage2_confirm", False))
    
    # Stage 2 Entry: Cross 0 OR (Cross Signal Line and MRS > 0)
    # Note: mrs_signal would normally be an SMA of MRS. 
    # For this atomic check, we prioritize the 0-cross which is the primary driver.
    sig = "N.A."
    if stage2_confirm:
        sig = "STAGE2_CONFIRMED"
    elif (mrs > 0 and mrs_prev <= 0) or (mrs > mrs_sig and mrs_prev <= mrs_sig and mrs > 0):
        sig = "BUY NOW"
    elif curr > high_prior:
        sig = "BREAKOUT"
    elif curr > high_prior * 0.95:
        # Price inside (95%, 100%] of pivot high — not a trade “buy”; avoid clashing with MRS STATUS BUY
        sig = "NEAR BRK"
    elif mrs > 0:
        sig = "STAGE 2"
    else:
        strict_stage1 = os.getenv("STAGE1_STRICT_AND_RS", "true").strip().lower() in ("1", "true", "yes")
        stage1_ok = (stage1_box and mrs_neg_ma10_rising) if strict_stage1 else (stage1_box or mrs_neg_ma10_rising)
        if stage1_ok:
            sig = "STAGE 1"
        elif mrs_rcvr:
            sig = "STAGE 1"
        else:
            sig = "STAGE 4"
        
    return {
        "status": sig,
        "is_breakout": sig in ("BREAKOUT", "STAGE2_CONFIRMED"),
        "ltp": float(curr),
        "trend_up": mrs > 0,
        "mrs": mrs,
        "brk_lvl": float(high_prior),
    }
