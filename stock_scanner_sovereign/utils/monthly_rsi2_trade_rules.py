"""
Mechanical monthly RSI(2) + take-profit rules for research and sidecar alignment.

- Monthly: month-end close, Wilder RSI period=2.
- Signal: RSI2 <= rsi_threshold at that month-end.
- Entry modes:
    signal_month_close — buy at the **close** of the last daily bar of the signal month (matches prior event-study anchor).
    next_session_close — buy at the **close** of the **next** trading day after that bar.
- Exit:
    TP20_CLOSE — first later day whose **close** >= entry * (1 + take_profit_pct).
    TP20_LIMIT — first day whose **high** >= entry * (1 + take_profit_pct); assume fill exactly at the limit price.
    TIMEOUT — flat at **close** after max_hold_trading_days if TP not hit.

All times use the instrument's daily index (EOD).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dt_time
from typing import Literal
from utils.zone_info import ZoneInfo

import numpy as np
import pandas as pd

EntryMode = Literal["signal_month_close", "next_session_close"]
ExitMode = Literal["close", "limit_hit"]


def rsi_wilder(close: pd.Series, period: int = 2) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_g = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_l = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_g / avg_l.replace(0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    out = out.where(avg_l != 0, 100.0)
    out = out.where(avg_g != 0, 0.0)
    return out


def month_end_close(daily_close: pd.Series) -> pd.Series:
    """
    Last daily **close** per calendar month (pandas ``freq='ME'``).

    For the **current** month, the bucket’s value is the **latest available** daily close in that
    month (e.g. **today’s** bar after EOD sync) — not a future calendar month-end price.
    The row label is still the month-end **timestamp** for that bucket.
    """
    return daily_close.resample("ME").last().dropna()


def week_end_close(daily_close: pd.Series) -> pd.Series:
    """
    Last daily close per ISO week (label = Friday, **Asia/Kolkata**).

    The **current** week’s bucket is the latest daily close available in that week (Connors-style
    weekly RSI uses completed weeks; blending today’s LTP into daily closes feeds this bucket).
    """
    if daily_close.empty:
        return daily_close
    s = daily_close.astype(float).sort_index()
    if s.index.tz is None:
        s = s.tz_localize("UTC")
    s_ist = s.tz_convert("Asia/Kolkata")
    return s_ist.resample("W-FRI", label="right", closed="right").last().dropna()


def latest_weekly_rsi2(
    daily_close: pd.Series, *, period: int = 2
) -> tuple[pd.Timestamp, float, pd.Timestamp, float] | None:
    """
    Wilder RSI(period) on ``week_end_close`` (IST week buckets).

    Returns
        (week_bucket_label, rsi_value, last_daily_ts, last_daily_close)
    """
    if daily_close.empty:
        return None
    asof_ts = daily_close.index[-1]
    asof_c = float(daily_close.iloc[-1])
    w = week_end_close(daily_close)
    if len(w) < period + 2:
        return None
    r = rsi_wilder(w, period=period)
    if r.empty:
        return None
    last = r.iloc[-1]
    if pd.isna(last):
        return None
    return r.index[-1], float(last), asof_ts, asof_c


def latest_monthly_rsi2(
    daily_close: pd.Series, *, period: int = 2
) -> tuple[pd.Timestamp, float, pd.Timestamp, float] | None:
    """
    Wilder RSI(period) on ``month_end_close`` series.

    Returns
        (month_bucket_label, rsi_value, last_daily_ts, last_daily_close)
    where ``last_daily_*`` is the freshest bar in ``daily_close`` (the bar feeding the current month).
    """
    if daily_close.empty:
        return None
    asof_ts = daily_close.index[-1]
    asof_c = float(daily_close.iloc[-1])
    m = month_end_close(daily_close)
    if len(m) < period + 2:
        return None
    r = rsi_wilder(m, period=period)
    if r.empty:
        return None
    last = r.iloc[-1]
    if pd.isna(last):
        return None
    return r.index[-1], float(last), asof_ts, asof_c


def daily_close_series_from_ohlcv(ohlcv: np.ndarray) -> pd.Series | None:
    """OHLCV rows: unix ts, o, h, l, c, v (PipelineBridge / DB shape)."""
    if ohlcv is None or len(ohlcv) < 80:
        return None
    ts = pd.to_datetime(ohlcv[:, 0], unit="s", utc=True)
    close = ohlcv[:, 4].astype(float)
    s = pd.Series(close, index=ts).sort_index().drop_duplicates(keep="last")
    return s if len(s) >= 80 else None


def blend_last_daily_bar_with_ltp(s: pd.Series, live_ltp: float) -> pd.Series:
    """
    Use live LTP as today's close for the monthly RSI bucket: either replace today's bar or append if EOD not in file yet.
    """
    if s is None or len(s) == 0 or live_ltp <= 0:
        return s
    ist = ZoneInfo("Asia/Kolkata")
    now_utc = pd.Timestamp.now(tz="UTC")
    today_ist = now_utc.tz_convert(ist).date()
    last_ts = s.index[-1]
    last_ist = last_ts.tz_convert(ist).date()
    out = s.copy()
    if last_ist == today_ist:
        out.iloc[-1] = float(live_ltp)
    else:
        out = pd.concat([out, pd.Series([float(live_ltp)], index=[now_utc])]).sort_index()
    return out


def sidecar_live_rsi2_window_ok(
    *,
    hour: int = 14,
    minute: int = 45,
) -> bool:
    """Weekday IST and clock >= hour:minute (e.g. 14:45 for live LTP blend)."""
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    if now_ist.weekday() >= 5:
        return False
    return now_ist.time() >= dt_time(hour, minute)


def signal_month_to_last_daily_ix(daily_close: pd.Series, month_end_ts: pd.Timestamp) -> int | None:
    ts = pd.Timestamp(month_end_ts)
    pos = int(daily_close.index.searchsorted(ts, side="right") - 1)
    if pos < 0:
        return None
    return pos


@dataclass
class MonthlyRsi2Trade:
    symbol: str
    signal_month_end: pd.Timestamp
    rsi2_monthly: float
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp | None
    exit_price: float | None
    ret: float | None
    exit_reason: str
    bars_held: int


def simulate_monthly_rsi2_trades(
    symbol: str,
    daily_close: pd.Series,
    daily_high: pd.Series,
    *,
    rsi_threshold: float = 2.0,
    take_profit_pct: float = 0.20,
    entry_mode: EntryMode = "signal_month_close",
    exit_mode: ExitMode = "close",
    max_hold_trading_days: int = 252,
) -> list[MonthlyRsi2Trade]:
    """
    One position at a time; skip new signals until after the previous trade's exit bar.
    """
    close = daily_close.astype(float).sort_index()
    high = daily_high.reindex(close.index).astype(float)
    high = high.fillna(close)

    mclose = month_end_close(close)
    rsi_m = rsi_wilder(mclose, period=2)

    signals: list[tuple[pd.Timestamp, float, int]] = []
    for m_ts, rsi_val in rsi_m.items():
        if pd.isna(rsi_val) or float(rsi_val) > rsi_threshold:
            continue
        sig_ix = signal_month_to_last_daily_ix(close, m_ts)
        if sig_ix is None:
            continue
        signals.append((m_ts, float(rsi_val), sig_ix))

    signals.sort(key=lambda x: x[2])

    trades: list[MonthlyRsi2Trade] = []
    last_exit_ix = -1
    n = len(close)
    idx = close.index

    for m_ts, rsi_val, sig_ix in signals:
        if entry_mode == "signal_month_close":
            entry_ix = sig_ix
        else:
            entry_ix = sig_ix + 1

        if entry_ix >= n or entry_ix < 0:
            continue
        if entry_ix <= last_exit_ix:
            continue

        entry_price = float(close.iloc[entry_ix])
        if not np.isfinite(entry_price) or entry_price <= 0:
            continue

        tp_line = entry_price * (1.0 + take_profit_pct)
        exit_ix: int | None = None
        exit_price: float | None = None
        reason = ""

        last_j = min(entry_ix + max_hold_trading_days, n - 1)
        for j in range(entry_ix + 1, n):
            if exit_mode == "close":
                if float(close.iloc[j]) >= tp_line:
                    exit_ix = j
                    exit_price = float(close.iloc[j])
                    reason = "TP20_CLOSE"
                    break
            else:
                if float(high.iloc[j]) >= tp_line:
                    exit_ix = j
                    exit_price = tp_line
                    reason = "TP20_LIMIT"
                    break
            if j >= last_j:
                exit_ix = j
                exit_price = float(close.iloc[j])
                reason = "TIMEOUT"
                break

        if exit_ix is None:
            continue

        last_exit_ix = exit_ix
        assert exit_price is not None
        ret = exit_price / entry_price - 1.0
        trades.append(
            MonthlyRsi2Trade(
                symbol=symbol,
                signal_month_end=m_ts,
                rsi2_monthly=rsi_val,
                entry_date=idx[entry_ix],
                entry_price=entry_price,
                exit_date=idx[exit_ix],
                exit_price=exit_price,
                ret=ret,
                exit_reason=reason,
                bars_held=int(exit_ix - entry_ix),
            )
        )

    return trades
