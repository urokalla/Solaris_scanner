"""
Weekly Mansfield-style mRS at historical week ends (same math as RSMathEngine.calculate_rs).

Used to measure slope *before* the line crosses 0 — e.g. rising from a trough while still negative,
similar to Weinstein / Mansfield RS chart behaviour.
"""
from __future__ import annotations

import numpy as np


def weekly_mrs_asof_batch(
    price_matrix_w: np.ndarray,
    bench_prices_w: np.ndarray,
    b: int,
) -> np.ndarray:
    """
    Vectorized weekly mRS as if the "current" bar were ``b`` weeks before the latest column.

    ``b=0`` matches the live endpoint formula: SMA over all prior columns in the window, vs last ratio.

    Parameters
    ----------
    price_matrix_w
        (n_symbols, H) weekly closes, oldest → newest.
    bench_prices_w
        (H,) benchmark weekly closes.
    b
        0 = use full matrix; 1 = pretend last week is T-1, etc.
    """
    pm = np.asarray(price_matrix_w, dtype=np.float64)
    br = np.asarray(bench_prices_w, dtype=np.float64)
    if pm.ndim != 2 or br.ndim != 1:
        return np.zeros(pm.shape[0] if pm.ndim == 2 else 0, dtype=np.float64)
    n, H = pm.shape[0], pm.shape[1]
    if H < 3 or br.shape[0] < H:
        return np.zeros(n, dtype=np.float64)
    b = int(max(0, b))
    end = H - 1 - b
    if end < 1:
        return np.zeros(n, dtype=np.float64)
    sub = pm[:, : end + 1]
    bench_seg = br[: end + 1]
    ratio = sub / (bench_seg + 1e-9)
    ratio_m = np.where(sub == 0, np.nan, ratio)
    sma = np.nanmean(ratio_m[:, :-1], axis=1)
    cur = ratio_m[:, -1]
    sma = np.where(~np.isfinite(sma) | (sma == 0), np.nan_to_num(cur, nan=1e-9) + 1e-9, sma)
    w_mrs = cur / sma
    return np.nan_to_num(((w_mrs - 1.0) * 10.0), nan=0.0).astype(np.float64)


def weekly_mrs_trailing_series(
    price_matrix_w: np.ndarray,
    bench_prices_w: np.ndarray,
    k: int,
) -> np.ndarray:
    """
    Stack weekly mRS for the last ``k`` week endpoints, **oldest → newest** (last column = live mRS).

    Each column uses the same Mansfield normalisation as ``weekly_mrs_asof_batch`` for offset ``b``.
    """
    k = int(max(2, k))
    cols = []
    for b in range(k - 1, -1, -1):
        cols.append(weekly_mrs_asof_batch(price_matrix_w, bench_prices_w, b))
    return np.column_stack(cols)


def mansfield_mrs_ols_slope(y: np.ndarray) -> np.ndarray:
    """
    Ordinary least-squares slope of weekly mRS vs time, **oldest → newest**.

    ``y`` shape ``(n_sym, K)``. Returns slope in **mRS points per week** (toward the present).
    Positive ⇒ the Mansfield-style line is rising over the window (even if still below 0).
    """
    y = np.asarray(y, dtype=np.float64)
    if y.ndim != 2 or y.shape[1] < 2:
        return np.zeros(y.shape[0] if y.ndim == 2 else 0, dtype=np.float64)
    n, K = y.shape
    x = np.arange(K, dtype=np.float64)
    xm = x.mean()
    xv = x - xm
    ssx = float(np.dot(xv, xv))
    if ssx <= 0:
        return np.zeros(n, dtype=np.float64)
    y_f = np.where(np.isfinite(y), y, np.nan)
    y_mean = np.nanmean(y_f, axis=1, keepdims=True)
    yc = np.where(np.isfinite(y_f), y_f - y_mean, 0.0)
    num = (xv * yc).sum(axis=1)
    return (num / ssx).astype(np.float64)
