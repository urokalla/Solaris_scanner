import os, json, time, threading; from .rs_math import compute_rs_logic
_g, _l = {}, threading.RLock(); C = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/cache"))

def compute_rs_ratings(idx="Nifty 500", p_data=None):
    with _l:
        if not p_data and idx in _g: return _g[idx]
    os.makedirs(C, exist_ok=True); c_f = os.path.join(C, f"rs_{idx.lower().replace(' ', '_')}.json")
    if not p_data and os.path.exists(c_f) and (time.time() - os.path.getmtime(c_f)) < 86400:
        try:
            with open(c_f) as f: res = json.load(f); _g[idx] = res; return res
        except: pass
    res = compute_rs_logic(idx, p_data)
    try:
        with open(c_f, 'w') as f: json.dump(res, f)
    except: pass
    with _l: _g[idx] = res
    return res

def get_rs_rating(s, universe="Nifty 500"):
    with _l:
        cache = _g.get(universe)
        if not cache:
            c_f = os.path.join(C, f"rs_{universe.lower().replace(' ', '_')}.json")
            if os.path.exists(c_f):
                try:
                    with open(c_f) as f: cache = json.load(f); _g[universe] = cache
                except: pass
        if not cache: return 0
    s_f = str(s).upper(); e = cache.get(s_f)
    if not e:
        r = s_f.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "").strip()
        e = cache.get(r) or cache.get(f"NSE:{r}-EQ") or 0
    return int(e["rs_rating"]) if isinstance(e, dict) else (int(e) if e else 0)
