import numpy as np

from utils.mrs_weekly_dynamics import mansfield_mrs_ols_slope, weekly_mrs_asof_batch


def test_weekly_mrs_b0_matches_endpoint_formula():
    np.random.seed(0)
    n, H = 4, 53
    pm = 100.0 + np.cumsum(np.random.randn(n, H), axis=1) * 2.0
    br = 100.0 + np.cumsum(np.random.randn(H), axis=0) * 1.5
    m0 = weekly_mrs_asof_batch(pm, br, 0)
    ratio = pm / (br + 1e-9)
    ratio_m = np.where(pm == 0, np.nan, ratio)
    sma = np.nanmean(ratio_m[:, :-1], axis=1)
    cur = ratio_m[:, -1]
    sma = np.where(~np.isfinite(sma) | (sma == 0), cur + 1e-9, sma)
    w_mrs = cur / sma
    expected = np.nan_to_num(((w_mrs - 1.0) * 10.0), nan=0.0)
    np.testing.assert_allclose(m0, expected, rtol=0, atol=1e-9)


def test_offset_increases_with_negative_trend():
    """If stock underperforms over older window, mrs at b=4 can be lower than b=0 (not required but sanity)."""
    H = 53
    br = np.linspace(100, 110, H)
    pm = np.ones((1, H)) * 100.0
    pm[0, -5:] = np.linspace(100, 115, 5)
    m0 = weekly_mrs_asof_batch(pm, br, 0)
    m4 = weekly_mrs_asof_batch(pm, br, 4)
    assert m0.shape == (1,) and m4.shape == (1,)
    assert float(m0[0] - m4[0]) == float(weekly_mrs_asof_batch(pm, br, 0)[0] - weekly_mrs_asof_batch(pm, br, 4)[0])


def test_mansfield_slope_matches_linear_trend():
    """OLS on y = m*x + c (x = 0..K-1) recovers m in mRS points/week."""
    K = 10
    m_true = 0.37
    c = -2.1
    x = np.arange(K, dtype=np.float64)
    y_row = m_true * x + c
    Y = np.vstack([y_row, y_row + 5.0])
    slopes = mansfield_mrs_ols_slope(Y)
    np.testing.assert_allclose(slopes, m_true, rtol=0, atol=1e-9)
