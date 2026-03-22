"""
Single source for breakout/MRS window parameters.

Values default from config.settings (env-overridable). Per-process overrides can be
passed through BreakoutScanner.update_params() using the same keys; they merge in
breakout_logic before calling calculate_breakout_signals.
"""
from __future__ import annotations

from typing import Any, Mapping

from config.settings import settings


def mrs_history_buffer_max(mrs_signal_period: int | None = None) -> int:
    """Ring length for streaming MRS samples (must be >= mrs_signal_period)."""
    p = mrs_signal_period if mrs_signal_period is not None else settings.BREAKOUT_MRS_SIGNAL_PERIOD
    return max(40, p + 10)


def get_breakout_window_dict() -> dict[str, int]:
    return {
        "mrs_signal_period": settings.BREAKOUT_MRS_SIGNAL_PERIOD,
        "mrs_history_buffer_max": mrs_history_buffer_max(settings.BREAKOUT_MRS_SIGNAL_PERIOD),
        "pivot_high_window": settings.BREAKOUT_PIVOT_HIGH_WINDOW,
        "min_intraday_bars_for_breakout": settings.BREAKOUT_MIN_INTRADAY_BARS,
    }


def merge_params_with_windows(base: Mapping[str, Any] | None) -> dict[str, Any]:
    """Window defaults first, then base (e.g. self.params) so update_params can override."""
    out: dict[str, Any] = {**get_breakout_window_dict()}
    if base:
        out.update(dict(base))
    try:
        mp = out.get("mrs_signal_period")
        if mp is not None:
            out["mrs_history_buffer_max"] = mrs_history_buffer_max(int(mp))
    except (TypeError, ValueError):
        pass
    return out
