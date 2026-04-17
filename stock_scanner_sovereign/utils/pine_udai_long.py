"""
Daily Pine-style logic (Udai Long): EMA trend filter, Donchian breakout, ATR trailing stop.
Uses ascending daily OHLCV (Parquet) + live LTP from SHM — not intraday bar EMAs.

- Donchian: prior ``breakout_period`` highs (excluding current bar); cross when LTP clears that level.
- Trend: EMA(fast) > EMA(slow); optional strict filter: LTP above both EMAs (``require_price_above_emas``).

Enable with SIDECAR_UDAI_PINE=1 (see config.settings).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

# Columns from PipelineBridge: timestamp, open, high, low, close, volume
_I_O, _I_H, _I_L, _I_C = 1, 2, 3, 4


def _ema_np(close: np.ndarray, period: int) -> np.ndarray:
    """EMA(close, period); seeds from first bar (stable for live updates)."""
    n = len(close)
    out = np.zeros(n, dtype=np.float64)
    if n == 0:
        return out
    alpha = 2.0 / (period + 1)
    out[0] = float(close[0])
    for i in range(1, n):
        out[i] = alpha * float(close[i]) + (1 - alpha) * out[i - 1]
    return out


def _atr_wilder(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder ATR (RMA of true range), same family as Pine ta.atr."""
    n = len(close)
    out = np.zeros(n, dtype=np.float64)
    if n < 2:
        return out
    tr = np.zeros(n, dtype=np.float64)
    tr[0] = float(high[0] - low[0])
    for i in range(1, n):
        hl = float(high[i] - low[i])
        hc = abs(float(high[i] - close[i - 1]))
        lc = abs(float(low[i] - close[i - 1]))
        tr[i] = max(hl, hc, lc)
    out[: period - 1] = np.nan
    out[period - 1] = float(np.mean(tr[1:period]))
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def donchian_level_excluding_last(high: np.ndarray, lookback: int) -> float:
    """Max high over prior `lookback` bars (excludes current bar's high). Pine Donchian-style."""
    if len(high) < lookback + 1:
        return float("nan")
    window = high[-(lookback + 1) : -1]
    return float(np.max(window))


def compute_udai_pine(
    ohlcv: np.ndarray | None,
    live_ltp: float,
    state: dict[str, Any],
    *,
    ema_fast: int = 9,
    ema_slow: int = 21,
    breakout_period: int = 20,
    require_price_above_emas: bool = True,
    atr_period: int = 9,
    atr_mult: float = 3.0,
    risk_pct: float = 1.0,
    account_equity: float = 1_000_000.0,
) -> dict[str, Any]:
    """
    Returns fields merged into sidecar `results[s]`; updates `state` in place for trail/position.
    """
    out: dict[str, Any] = {
        "udai_ok": False,
        "udai_trend_long": False,
        "udai_price_above_emas": False,
        "udai_entry_signal": False,
        "udai_in_pos": bool(state.get("in_pos", False)),
        "udai_trail": state.get("trail"),
        "udai_atr": None,
        "udai_hh_level": None,
        "udai_suggested_qty": None,
        "udai_ui": "—",
        "stop_price": None,
    }
    if ohlcv is None or len(ohlcv) < max(ema_slow, breakout_period + 2, atr_period) + 2:
        return out

    high = ohlcv[:, _I_H].astype(np.float64)
    low = ohlcv[:, _I_L].astype(np.float64)
    close = ohlcv[:, _I_C].astype(np.float64)

    c_live = close.copy()
    c_live[-1] = float(live_ltp)

    ema_f = _ema_np(c_live, ema_fast)
    ema_s = _ema_np(c_live, ema_slow)
    ema9 = float(ema_f[-1])
    ema21 = float(ema_s[-1])
    curr = float(live_ltp)
    long_trend = ema9 > ema21
    price_above_emas = (curr > ema9) and (curr > ema21)

    hh = donchian_level_excluding_last(high, breakout_period)
    prev_c = float(close[-2])
    crossed = (not math.isnan(hh)) and (prev_c <= hh) and (curr > hh)

    atr_ser = _atr_wilder(high, low, close, atr_period)
    atr_val = float(atr_ser[-1]) if len(atr_ser) and not math.isnan(atr_ser[-1]) else float("nan")
    if math.isnan(atr_val) or atr_val <= 0:
        atr_val = float(atr_ser[-2]) if len(atr_ser) > 1 else 0.0

    out["udai_ok"] = True
    out["udai_trend_long"] = long_trend
    out["udai_price_above_emas"] = price_above_emas
    out["udai_hh_level"] = hh if not math.isnan(hh) else None
    out["udai_atr"] = atr_val

    risk_amt = float(account_equity) * (float(risk_pct) / 100.0)
    stop_dist = atr_val * float(atr_mult)
    if stop_dist > 0:
        out["udai_suggested_qty"] = int(round(risk_amt / stop_dist))

    in_pos = bool(state.get("in_pos", False))
    trail = state.get("trail")

    if in_pos and trail is not None:
        cur_stop = curr - float(atr_mult) * atr_val
        trail = max(float(cur_stop), float(trail))
        state["trail"] = trail
        out["udai_trail"] = trail
        out["udai_in_pos"] = True
        if curr < trail:
            state["in_pos"] = False
            state["trail"] = None
            out["udai_in_pos"] = False
            out["udai_trail"] = None
            out["udai_ui"] = "EXIT ATR"
        else:
            out["udai_ui"] = f"HOLD tr={trail:.2f}"

    if not state.get("in_pos", False):
        ema_filter = long_trend and (price_above_emas if require_price_above_emas else True)
        entry_cond = ema_filter and crossed
        if entry_cond:
            state["in_pos"] = True
            state["trail"] = curr - float(atr_mult) * atr_val
            out["udai_in_pos"] = True
            out["udai_trail"] = state["trail"]
            out["udai_entry_signal"] = True
            out["udai_ui"] = "ENTRY"
        else:
            out["udai_entry_signal"] = False
            if out.get("udai_ui") in (None, "—"):
                if require_price_above_emas and long_trend and not price_above_emas:
                    out["udai_ui"] = "BO but <EMA"
                else:
                    out["udai_ui"] = "FLAT" if long_trend else "NO TREND"
    else:
        out.setdefault("udai_entry_signal", False)

    # Dashboard stop line: trailing when long, else preliminary (matches Pine table)
    if out.get("udai_ok") and atr_val > 0:
        if out.get("udai_in_pos") and out.get("udai_trail") is not None:
            out["stop_price"] = float(out["udai_trail"])
        else:
            out["stop_price"] = curr - float(atr_mult) * atr_val

    return out
