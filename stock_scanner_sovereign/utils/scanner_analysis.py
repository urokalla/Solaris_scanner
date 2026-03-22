import numpy as np
from .rs_rating import get_rs_rating

# Column Indices for Zero-Pandas Logic
TS_IDX, OPEN_IDX, HIGH_IDX, LOW_IDX, CLOSE_IDX, VOL_IDX = 0, 1, 2, 3, 4, 5


def compute_trading_profile(rs_rating: int, mrs: float, mrs_daily: float) -> str:
    """
    Display-only bucket for the SHM `profile` field (S20). Uses only outputs already
    produced by RSMathEngine (rs_rating, weekly mRS, daily mRS). Does not run extra
    benchmark or universe passes; does not alter RS math.
    """
    r = int(np.clip(int(rs_rating), 0, 100))
    m = float(mrs) if np.isfinite(mrs) else 0.0
    d = float(mrs_daily) if np.isfinite(mrs_daily) else 0.0
    # Priority: top RS bands → negative momentum → weak RS / deep negative mRS → positive dual momentum → default
    if r >= 95:
        return "ELITE"
    if r >= 82:
        return "LEADER"
    if m < 0 and d < 0:
        return "FADING"
    if r <= 22 or m < -1.5:
        return "LAGGARD"
    if m > 0 and d > 0:
        return "RISING"
    return "BASELINE"


def profile_label_to_shm(label: str) -> bytes:
    """UTF-8 bytes padded to 20 for numpy `S20` `profile` column."""
    raw = label.encode("utf-8")[:20]
    return raw.ljust(20, b" ")


def fast_ema_np(data, span):
    if len(data) == 0: return np.array([])
    alpha = 2 / (span + 1)
    output = np.zeros_like(data)
    output[0] = data[0]
    for i in range(1, len(data)):
        output[i] = (data[i] * alpha) + (output[i-1] * (1 - alpha))
    return output

def align_numpy(s_data, b_data):
    if s_data.size == 0 or b_data.size == 0: return np.array([]), np.array([])
    def dedupe(arr):
        ts = arr[:, TS_IDX].astype(np.int64)
        _, idx = np.unique(ts[::-1], return_index=True)
        return arr[np.sort(len(ts) - 1 - idx)]
    s_clean = dedupe(s_data)
    b_clean = dedupe(b_data)
    s_ts, b_ts = s_clean[:, TS_IDX].astype(np.int64), b_clean[:, TS_IDX].astype(np.int64)
    common_ts = np.intersect1d(s_ts, b_ts)
    if len(common_ts) == 0: return s_clean[-1:], b_clean[-1:]
    return s_clean[np.isin(s_ts, common_ts)], b_clean[np.isin(b_ts, common_ts)]

def calculate_signals_np(symbol, s_arr, b_arr, params):
    """Sovereign Signal Engine: Zero-Pandas."""
    try:
        if s_arr.size == 0: return None
        price = float(s_arr[-1, CLOSE_IDX])
        ticker_short = symbol.upper().replace("NSE:", "").split("-")[0]
        rs_rating = get_rs_rating(ticker_short, universe=params.get("universe", "Nifty 500"))
        
        # Simple Logic for Analysis
        ema50 = fast_ema_np(s_arr[:, CLOSE_IDX], 50)
        trend_up = price > ema50[-1] if len(ema50) > 0 else False
        
        return {
            "symbol": symbol, "ltp": price, "rs_rating": rs_rating,
            "status": "Trending" if trend_up else "Neutral",
            "ema_ok": trend_up
        }
    except Exception: return None
