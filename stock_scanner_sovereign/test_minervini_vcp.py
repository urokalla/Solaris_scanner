"""Quick checks for Minervini-style VCP proxy."""
import numpy as np

from utils.minervini_vcp import vcp_features


def _synthetic_coiling(n: int = 90, seed: int = 0) -> np.ndarray:
    """Three phases: wide → mid → tight range + volume fades (VCP-like)."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        if i < 30:
            spread = 0.045
            base_v = 1_000_000.0
        elif i < 60:
            spread = 0.028
            base_v = 750_000.0
        else:
            spread = 0.012
            base_v = 450_000.0
        c = 100.0 + i * 0.05 + rng.normal(0, 0.02)
        noise = rng.normal(0, spread * 0.08)
        h = c * (1.0 + spread / 2 + noise)
        l = c * (1.0 - spread / 2 + noise)
        o = c + rng.normal(0, spread * 0.01)
        v = base_v * (1.0 + rng.normal(0, 0.05))
        rows.append([float(i), o, h, l, c, max(v, 1.0)])
    return np.array(rows, dtype=np.float64)


def _synthetic_expanding(n: int = 90, seed: int = 1) -> np.ndarray:
    """Volatility expands each third — should fail VCP."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        if i < 30:
            spread = 0.012
        elif i < 60:
            spread = 0.028
        else:
            spread = 0.050
        c = 100.0 + i * 0.05
        h = c * (1.0 + spread / 2)
        l = c * (1.0 - spread / 2)
        rows.append([float(i), c, h, l, c, 1e6])
    return np.array(rows, dtype=np.float64)


def test_vcp_detects_coiling():
    o = _synthetic_coiling()
    r = vcp_features(o, n_segments=3, lookback=90, min_relax_step=0.05)
    assert r["vcp_ok"] is True, r
    assert len(r["vcp_range_medians"]) == 3
    m = r["vcp_range_medians"]
    assert m[0] > m[1] > m[2]


def test_vcp_rejects_expanding():
    o = _synthetic_expanding()
    r = vcp_features(o, n_segments=3, lookback=90, min_relax_step=0.05)
    assert r["vcp_ok"] is False


def test_vcp_insufficient_data():
    o = np.zeros((10, 6), dtype=np.float64)
    r = vcp_features(o, lookback=90)
    assert r["vcp_ok"] is False
    assert r["vcp_note"] == "insufficient_bars"
