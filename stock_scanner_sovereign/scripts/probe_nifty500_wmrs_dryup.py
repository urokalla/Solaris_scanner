#!/usr/bin/env python3
from datetime import datetime

import numpy as np

from frontend_reflex.breakout_engine_manager import get_breakout_scanner


def weekly_close_vol(hv):
    wk = {}
    for r in hv:
        try:
            ts = float(r[0])
            close = float(r[4])
            vol = float(r[5]) if len(r) > 5 else 0.0
        except Exception:
            continue
        if not np.isfinite(ts) or not np.isfinite(close) or close <= 0:
            continue
        d = datetime.fromtimestamp(ts)
        y, w, _ = d.isocalendar()
        key = (int(y), int(w))
        prev = wk.get(key)
        if prev is None:
            wk[key] = [close, max(0.0, vol)]
        else:
            prev[0] = close
            prev[1] += max(0.0, vol)
    keys = sorted(wk.keys())
    closes = np.array([wk[k][0] for k in keys], dtype=float)
    vols = np.array([wk[k][1] for k in keys], dtype=float)
    return closes, vols


def main():
    dryup_ratio = 0.70
    min_wmrs_delta = 1.0

    sc = get_breakout_scanner(universe="Nifty 500")
    sc.update_universe("Nifty 500", None)

    bench = sc.bench_sym
    b_hv = sc.bridge.get_historical_data(bench, limit=900)
    if b_hv is None or len(b_hv) < 320:
        b_hv = sc.db.get_historical_data(bench, "1d", limit=900)
    if b_hv is None or len(b_hv) < 320:
        print(f"ERROR: benchmark DB history insufficient for {bench}")
        return

    b_close, _ = weekly_close_vol(b_hv)
    rows = []
    checked = 0
    for sym in sc.symbols:
        hv = sc.bridge.get_historical_data(sym, limit=900)
        if hv is None or len(hv) < 320:
            hv = sc.db.get_historical_data(sym, "1d", limit=900)
        if hv is None or len(hv) < 320:
            continue
        checked += 1
        s_close, s_vol = weekly_close_vol(hv)
        n = min(len(s_close), len(b_close))
        if n < 70:
            continue
        s = s_close[-n:]
        b = b_close[-n:]
        v = s_vol[-n:]
        ratio = s / np.maximum(b, 1e-9)
        sma52 = np.convolve(ratio, np.ones(52) / 52.0, mode="valid")
        if len(sma52) < 6:
            continue
        mrs = ((ratio[51:] / np.maximum(sma52, 1e-12)) - 1.0) * 100.0
        if len(mrs) < 4 or len(v) < 14:
            continue

        w0, w1, w2, w3 = float(mrs[-1]), float(mrs[-2]), float(mrs[-3]), float(mrs[-4])
        rising_3w = w0 > w1 > w2 > w3
        delta3 = w0 - w3
        vol_3w = float(np.mean(v[-3:]))
        vol_10w_prev = float(np.mean(v[-13:-3]))
        if not np.isfinite(vol_10w_prev) or vol_10w_prev <= 0:
            continue
        ratio_vol = vol_3w / vol_10w_prev
        dryup = ratio_vol <= dryup_ratio
        if rising_3w and dryup and delta3 >= min_wmrs_delta:
            r = sc.results.get(sym, {})
            rows.append(
                {
                    "symbol": sym,
                    "wmrs": round(w0, 2),
                    "wmrs_3w_delta": round(delta3, 2),
                    "dry_ratio": round(ratio_vol, 2),
                    "chg": round(float(r.get("change_pct", 0.0) or 0.0), 2),
                    "rv": round(float(r.get("rv", 0.0) or 0.0), 2),
                    "last_tag": str(r.get("last_tag", "")),
                    "last_tag_w": str(r.get("last_tag_w", "")),
                }
            )

    rows_sorted = sorted(rows, key=lambda x: (x["rv"], x["chg"]), reverse=True)
    print(f"nifty500_symbols={len(sc.symbols)} checked_with_history={checked}")
    print(f"pass_count={len(rows_sorted)} rule=dry_ratio<={dryup_ratio}, rising3w, delta3>={min_wmrs_delta}")
    for r in rows_sorted[:30]:
        print(r)
    print(f"cohance_pass={any(r['symbol'] == 'NSE:COHANCE-EQ' for r in rows_sorted)}")


if __name__ == "__main__":
    main()
