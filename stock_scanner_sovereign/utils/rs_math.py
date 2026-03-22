import os, json, time, numpy as np, threading
from concurrent.futures import ThreadPoolExecutor
from .pipeline_bridge import PipelineBridge; from .constants import BENCHMARK_MAP; from .symbols import get_nifty_symbols

def compute_rs_logic(idx, p_data):
    bridge = PipelineBridge(); syms = get_nifty_symbols(idx)
    f_s = list(set([s for s in syms] + [BENCHMARK_MAP.get(idx, "NSE:NIFTY50-INDEX")]))
    def _j(s):
        d = bridge.get_historical_data(s, limit=255)
        return (s, d) if d is not None else (s, None)
    all_d = p_data if p_data else {s: d for s, d in ThreadPoolExecutor(20).map(_j, f_s) if d is not None}
    b_f = BENCHMARK_MAP.get(idx, "NSE:NIFTY50-INDEX"); b_df = all_d.get(b_f)
    if b_df is None: return {}
    v_d = [(s, d[:, 4]) for s, d in all_d.items() if len(d) >= 50 and s != b_f]
    if not v_d: return {}
    s_l, pm = zip(*[(s, [c[-1], c[-63] if len(c)>=63 else c[0], c[-126] if len(c)>=126 else c[0], 
                         c[-189] if len(c)>=189 else c[0], c[-252] if len(c)>=252 else c[0]]) for s, c in v_d])
    P = np.array(pm); R = ((P[:, 0:1] / P[:, 1:]) - 1) * 100
    sc = R @ np.array([0.4, 0.2, 0.2, 0.2])
    ra = np.argsort(np.argsort(sc)) + 1
    pr = np.clip((ra / len(ra) * 99).round().astype(int), 1, 99)
    mrs = ((P[:, 0] / b_df[-1, 4]) / (P[:, 1] / b_df[-63, 4] if len(b_df)>63 else b_df[0, 4]) - 1) * 100
    return {s_l[i]: {"rs_rating": int(pr[i]), "mrs": float(mrs[i])} for i in range(len(s_l))}
