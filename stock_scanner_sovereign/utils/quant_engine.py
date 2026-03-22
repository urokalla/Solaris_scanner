import numpy as np
from numba import njit

@njit(fastmath=True, cache=True)
def calculate_performance_score(close_prices):
    """
    Compiled to MACHINE CODE. 
    Calculates weighted 12-month momentum (O'Neil Style).
    """
    size = len(close_prices)
    if size < 250:
        return 0.0
    
    # Weighted return: 40% (3mo), 20% (6mo), 20% (9mo), 20% (12mo)
    # Note: Using negative indexing on numpy arrays is fast in numba
    p0 = close_prices[-1]
    p3 = close_prices[-63]
    p6 = close_prices[-126]
    p9 = close_prices[-189]
    p12 = close_prices[-250]
    
    # (p0/p3)*2 represents the 40% weighting (doubled relative momentum)
    score = ((p0/p3)*2) + (p0/p6) + (p0/p9) + (p0/p12)
    return score

@njit(fastmath=True)
def check_technical_filters(close_prices, ma_len=50):
    """Fast SMA and Trend filter directly on numpy arrays."""
    if len(close_prices) < ma_len:
        return False
    # Use numpy mean for speed
    sma = np.mean(close_prices[-ma_len:])
    return close_prices[-1] > sma
