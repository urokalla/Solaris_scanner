"""
Golden vectors for breakout / MRS signal windows (no live SHM or DB).
Run: cd stock_scanner_sovereign && python -m pytest test_breakout_quant_golden.py -v
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.breakout_math import calculate_breakout_signals, compute_mrs_signal_line
from utils.quant_breakout_config import get_breakout_window_dict, merge_params_with_windows


def _bars(n: int, high: float = 100.0, close: float = 99.0) -> np.ndarray:
    """Synthetic tape: [ts, o, h, l, c, v]."""
    t = np.arange(n, dtype=np.float64).reshape(-1, 1)
    o = np.full((n, 1), close)
    h = np.full((n, 1), high)
    l = np.full((n, 1), close - 1.0)
    c = np.full((n, 1), close)
    v = np.ones((n, 1))
    return np.hstack([t, o, h, l, c, v])


def test_get_breakout_window_dict_keys():
    d = get_breakout_window_dict()
    assert set(d.keys()) == {
        "mrs_signal_period",
        "mrs_history_buffer_max",
        "pivot_high_window",
        "min_intraday_bars_for_breakout",
    }
    assert d["mrs_history_buffer_max"] >= d["mrs_signal_period"]


def test_merge_params_with_windows_overrides():
    base = {"mrs_signal_period": 14, "foo": 1}
    m = merge_params_with_windows(base)
    assert m["mrs_signal_period"] == 14
    assert m["mrs_history_buffer_max"] >= 24
    assert m["foo"] == 1


def test_compute_mrs_signal_line_full_period():
    period = 30
    hist = list(range(period))
    assert compute_mrs_signal_line(hist, period) == float(np.mean(hist))


def test_compute_mrs_signal_line_partial_uses_last():
    assert compute_mrs_signal_line([1.0, 2.0, 3.0], 30) == 3.0


def test_golden_insufficient_history_mrs_positive():
    wd = get_breakout_window_dict()
    min_b = wd["min_intraday_bars_for_breakout"]
    h = _bars(min_b - 1)
    params = merge_params_with_windows(
        {"rs_rating_info": {"mrs": 1.0, "mrs_prev": -1.0, "mrs_signal": 0.0}}
    )
    r = calculate_breakout_signals("NSE:TEST-EQ", h, None, params)
    assert r["status"] == "STAGE 2"
    assert r["trend_up"] is True


def test_golden_insufficient_history_mrs_negative():
    wd = get_breakout_window_dict()
    h = _bars(wd["min_intraday_bars_for_breakout"] - 1)
    params = merge_params_with_windows(
        {"rs_rating_info": {"mrs": -1.0, "mrs_prev": -1.0, "mrs_signal": 0.0}}
    )
    r = calculate_breakout_signals("NSE:TEST-EQ", h, None, params)
    assert r["status"] == "STAGE 4"
    assert r["trend_up"] is False


def test_golden_breakout_price_above_pivot():
    wd = get_breakout_window_dict()
    n = wd["min_intraday_bars_for_breakout"]
    h = _bars(n, high=100.0, close=99.0)
    h[-1, 2] = 100.0
    h[-1, 4] = 101.0
    params = merge_params_with_windows(
        {"rs_rating_info": {"mrs": -1.0, "mrs_prev": -1.0, "mrs_signal": 0.0}}
    )
    r = calculate_breakout_signals("NSE:TEST-EQ", h, None, params)
    assert r["status"] == "BREAKOUT"
    assert r["is_breakout"] is True


def test_golden_buy_now_mrs_cross_zero():
    wd = get_breakout_window_dict()
    h = _bars(wd["min_intraday_bars_for_breakout"])
    params = merge_params_with_windows(
        {"rs_rating_info": {"mrs": 1.0, "mrs_prev": -0.5, "mrs_signal": 0.0}}
    )
    r = calculate_breakout_signals("NSE:TEST-EQ", h, None, params)
    assert r["status"] == "BUY NOW"


def test_golden_near_brk_95_percent_band():
    """Close above 95% of pivot high but not above full pivot — label NEAR BRK (weekly mRS can be < 0)."""
    wd = get_breakout_window_dict()
    n = wd["min_intraday_bars_for_breakout"]
    h = _bars(n, high=100.0, close=99.0)
    h[-1, 4] = 96.0  # > 95, not > 100
    params = merge_params_with_windows(
        {"rs_rating_info": {"mrs": -1.0, "mrs_prev": -1.0, "mrs_signal": 0.0}}
    )
    r = calculate_breakout_signals("NSE:TEST-EQ", h, None, params)
    assert r["status"] == "NEAR BRK"
    assert r["is_breakout"] is False


def test_golden_custom_pivot_window():
    """Narrow pivot window: 10 bars with max high 50; close 60 -> BREAKOUT."""
    wd = get_breakout_window_dict()
    n = max(wd["min_intraday_bars_for_breakout"], 15)
    h = _bars(n, high=50.0, close=49.0)
    h[-1, 4] = 60.0
    params = merge_params_with_windows(
        {
            "pivot_high_window": 10,
            "rs_rating_info": {"mrs": -1.0, "mrs_prev": -1.0, "mrs_signal": 0.0},
        }
    )
    r = calculate_breakout_signals("NSE:TEST-EQ", h, None, params)
    assert r["status"] == "BREAKOUT"


def test_golden_brk_lvl_populated_below_min_bars():
    """BRK_LVL uses pivot window only; tape can be shorter than min_intraday_bars."""
    wd = get_breakout_window_dict()
    min_b = wd["min_intraday_bars_for_breakout"]
    n = max(wd["pivot_high_window"] + 2, min_b - 20)
    h = _bars(n, high=222.0, close=200.0)
    params = merge_params_with_windows(
        {"rs_rating_info": {"mrs": 1.0, "mrs_prev": -1.0, "mrs_signal": 0.0}}
    )
    r = calculate_breakout_signals("NSE:TEST-EQ", h, None, params)
    assert len(h) < min_b
    assert r["brk_lvl"] is not None
    assert abs(r["brk_lvl"] - 222.0) < 1e-6
