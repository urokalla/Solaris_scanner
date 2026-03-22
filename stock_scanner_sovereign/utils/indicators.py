import numpy as np

def crossover(s1, s2):
    """Sovereign Crossover: Zero-Pandas. Works on Numpy/Lists."""
    if len(s1) < 2: return False
    
    # Handle both series and scalars for s2
    v2_m1 = s2[-1] if hasattr(s2, '__len__') and not isinstance(s2, str) else s2
    v2_m2 = s2[-2] if hasattr(s2, '__len__') and not isinstance(s2, str) else s2
    
    return s1[-2] <= v2_m2 and s1[-1] > v2_m1

def crossunder(s1, s2):
    """Sovereign Crossunder: Zero-Pandas."""
    if len(s1) < 2: return False
    
    v2_m1 = s2[-1] if hasattr(s2, '__len__') and not isinstance(s2, str) else s2
    v2_m2 = s2[-2] if hasattr(s2, '__len__') and not isinstance(s2, str) else s2
    
    return s1[-2] >= v2_m2 and s1[-1] < v2_m1
