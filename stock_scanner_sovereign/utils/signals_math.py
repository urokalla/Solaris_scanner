import numpy as np
import os

from utils.quant_breakout_config import get_breakout_window_dict


def detect_pivot_high(arr, window=20):
    """Vectorized pivot high detection (<50 lines). Always returns a native Python float (Reflex JSON)."""
    if len(arr) < window:
        return 0.0
    return float(np.max(arr[-window:]))


def effective_pivot_window(n_bars: int, pivot_w: int) -> int | None:
    """
    Use a shorter pivot when the tape has fewer than pivot_w+1 rows (still >= 2 bars).
    Avoids BRK_LVL staying empty while mRS/SHM are already live.
    """
    if n_bars < 2:
        return None
    w = max(1, min(int(pivot_w), max(1, n_bars - 2)))
    if n_bars - 1 < w:
        w = max(1, n_bars - 1)
    return w


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
    if h is None or len(h) < min_bars:
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
