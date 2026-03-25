"""
Minervini-style VCP (volatility contraction pattern) — screening proxy.

This is not a proprietary rule engine; it encodes a common *quant* reading of public
VCP ideas: several successive *tightenings* of day-to-day volatility inside a base,
often with fading volume, before a pivot / breakout attempt.

OHLCV layout matches :class:`PipelineBridge.get_historical_data` output:
``[ts, open, high, low, close, volume]`` (float rows, oldest first).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

_I_O, _I_H, _I_L, _I_C, _I_V = 1, 2, 3, 4, 5


def vcp_features(
    ohlcv: np.ndarray | None,
    *,
    n_segments: int = 3,
    lookback: int = 90,
    min_relax_step: float = 0.07,
    volume_dryup_ratio: float | None = 0.88,
    near_high_lookback: int = 25,
    near_high_max_pct: float = 0.12,
    require_constructive: bool = True,
) -> dict[str, Any]:
    """
    Parameters
    ----------
    n_segments
        How many consecutive windows (oldest → newest) must show *strictly*
        tightening typical range. Minervini often describes 2–4 contractions; 3 is a
        practical default.
    lookback
        Trading days in the base window (most recent ``lookback`` bars).
    min_relax_step
        Each segment median range must be at least this fraction *smaller* than the
        prior segment (e.g. 0.07 ⇒ 7% tightening minimum step).
    volume_dryup_ratio
        If set, newest segment median volume must be ≤ this × oldest segment median
        volume. ``None`` skips volume (e.g. bad/missing vol).
    near_high_lookback / near_high_max_pct
        Constructive check: last close within ``near_high_max_pct`` of the
        ``near_high_lookback``-day high (price not deep in the base).
    require_constructive
        If False, skip the near-high check (pure contraction geometry).
    """
    out: dict[str, Any] = {
        "vcp_ok": False,
        "vcp_segments": n_segments,
        "vcp_range_medians": None,
        "vcp_vol_medians": None,
        "vcp_constructive": False,
        "vcp_dist_to_high_pct": None,
        "vcp_note": "",
    }
    if ohlcv is None or len(ohlcv) < max(lookback, near_high_lookback + 5, n_segments * 5):
        out["vcp_note"] = "insufficient_bars"
        return out

    w = ohlcv[-lookback:]
    h = w[:, _I_H].astype(np.float64)
    low = w[:, _I_L].astype(np.float64)
    c = w[:, _I_C].astype(np.float64)
    c_safe = np.where(np.abs(c) < 1e-12, np.nan, c)
    rng = (h - low) / c_safe
    rng = rng[np.isfinite(rng) & (rng >= 0)]

    if rng.size < n_segments * 3:
        out["vcp_note"] = "insufficient_range_bars"
        return out

    # Re-align rng with valid close mask on w
    ok = np.isfinite(c_safe) & (c_safe != 0) & np.isfinite(h) & np.isfinite(low)
    w2 = w[ok]
    if len(w2) < n_segments * 3:
        out["vcp_note"] = "insufficient_after_mask"
        return out
    h, low, c = w2[:, _I_H], w2[:, _I_L], w2[:, _I_C]
    rng = (h - low) / c

    edges = np.linspace(0, len(rng), n_segments + 1, dtype=int)
    med_ranges: list[float] = []
    med_vols: list[float] = []
    for s in range(n_segments):
        a, b = edges[s], edges[s + 1]
        seg = rng[a:b]
        if seg.size < 2:
            out["vcp_note"] = "empty_segment"
            return out
        med_ranges.append(float(np.median(seg)))
        if w2.shape[1] > _I_V:
            v = w2[a:b, _I_V].astype(np.float64)
            v = v[np.isfinite(v) & (v >= 0)]
            med_vols.append(float(np.median(v)) if v.size else float("nan"))
        else:
            med_vols.append(float("nan"))

    out["vcp_range_medians"] = med_ranges
    out["vcp_vol_medians"] = med_vols

    tightens = True
    for i in range(1, n_segments):
        prev, cur = med_ranges[i - 1], med_ranges[i]
        if prev <= 0 or not math.isfinite(prev) or not math.isfinite(cur):
            tightens = False
            break
        if cur > prev * (1.0 - min_relax_step):
            tightens = False
            break

    vol_ok = True
    if volume_dryup_ratio is not None and w2.shape[1] > _I_V:
        v0, v1 = med_vols[0], med_vols[-1]
        if not math.isfinite(v0) or not math.isfinite(v1) or v0 <= 0:
            vol_ok = True
        else:
            vol_ok = v1 <= v0 * float(volume_dryup_ratio)

    hi_recent = float(np.max(w2[-near_high_lookback:, _I_H]))
    last_c = float(w2[-1, _I_C])
    if hi_recent > 0 and math.isfinite(last_c):
        dist = (hi_recent - last_c) / hi_recent
        out["vcp_dist_to_high_pct"] = float(dist)
        out["vcp_constructive"] = dist <= float(near_high_max_pct)
    else:
        out["vcp_constructive"] = False

    constructive_ok = out["vcp_constructive"] if require_constructive else True

    out["vcp_ok"] = bool(tightens and vol_ok and constructive_ok)
    parts = []
    if tightens:
        parts.append("tighten")
    else:
        parts.append("no_monotone_tighten")
    if volume_dryup_ratio is not None and w2.shape[1] > _I_V:
        parts.append("vol_dry" if vol_ok else "vol_no_dry")
    if require_constructive:
        parts.append("constructive" if out["vcp_constructive"] else "not_near_high")
    out["vcp_note"] = "|".join(parts)
    return out


def vcp_ok(ohlcv: np.ndarray | None, **kwargs: Any) -> bool:
    return bool(vcp_features(ohlcv, **kwargs).get("vcp_ok"))
