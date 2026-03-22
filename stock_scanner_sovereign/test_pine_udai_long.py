"""Unit tests for daily Pine Udai Long helper (EMA / Donchian / ATR trail)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from utils.pine_udai_long import compute_udai_pine, donchian_level_excluding_last


def _synth_ohlcv(n: int) -> np.ndarray:
    ts = np.arange(n, dtype=np.float64)
    # Mild uptrend OHLC
    base = 100 + np.linspace(0, 2, n)
    o = base.copy()
    h = base + 0.5
    l = base - 0.5
    c = base + 0.1
    v = np.ones(n) * 1e6
    return np.column_stack([ts, o, h, l, c, v])


def test_donchian_excludes_current_bar():
    h = np.array([1.0, 2.0, 3.0, 10.0, 5.0], dtype=np.float64)
    # Prior 3 highs before last: 2,3,10 -> max 10; last bar high 5 excluded
    assert donchian_level_excluding_last(h, 3) == 10.0


def test_compute_udai_pine_flat_state():
    ohlcv = _synth_ohlcv(80)
    st = {"in_pos": False, "trail": None}
    out = compute_udai_pine(ohlcv, float(ohlcv[-1, 4]), st, ema_fast=9, ema_slow=21, breakout_period=20, atr_period=9)
    assert out["udai_ok"] is True
    assert "udai_ui" in out
    assert st["in_pos"] in (True, False)


def test_trail_exit_clears_state():
    ohlcv = _synth_ohlcv(80)
    lp = float(ohlcv[-1, 4])
    st = {"in_pos": True, "trail": lp + 50.0}  # trail above price -> immediate exit
    out = compute_udai_pine(ohlcv, lp, st, atr_mult=3.0, atr_period=9)
    assert out["udai_in_pos"] is False
    assert st["in_pos"] is False
    assert st["trail"] is None
