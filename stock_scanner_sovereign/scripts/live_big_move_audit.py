#!/usr/bin/env python3
"""
Live "big move" audit (NO dashboard changes):

- Reads live % change from SHM (scanner_results.mmap): `change_pct`, `rv`, `mrs`, `status`.
- Filters *stocks* (NSE:...-EQ) moving >= threshold% right now.
- For each live mover, loads daily Parquet history and computes "yesterday setup" features:
  - Near 20D / 52W / multi-year highs
  - Compression (10D/20D vol contraction)
  - Volume expansion (yesterday vol vs 20D avg)
  - Range vs ATR(14)

Goal: answer "If it's up big today, what did it look like yesterday and what are we missing?"

Examples:
  cd stock_scanner_sovereign
  python3 scripts/live_big_move_audit.py --threshold 10
  python3 scripts/live_big_move_audit.py --threshold 10 --max 30 --years 3
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

SOV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOV)

from backend.scanner_shm import SHMBridge  # noqa: E402
from config.settings import settings  # noqa: E402
from utils.universe_history_audit import resolve_parquet_path  # noqa: E402


def _decode_shm_str(x) -> str:
    if x is None:
        return ""
    try:
        if isinstance(x, (bytes, bytearray)):
            return x.decode("utf-8", errors="ignore").strip("\x00").strip()
        if hasattr(x, "tobytes"):
            return x.tobytes().decode("utf-8", errors="ignore").strip("\x00").strip()
    except Exception:
        return str(x).strip()
    return str(x).strip()


def _atr14(df: pd.DataFrame) -> pd.Series:
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    c = df["close"].astype(float)
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(14, min_periods=14).mean()


def _rolling_std(x: np.ndarray) -> float:
    if x.size == 0:
        return float("nan")
    return float(np.std(x, ddof=0))


def _load_daily_ohlcv(symbol: str, data_dir: str) -> pd.DataFrame | None:
    path = resolve_parquet_path(symbol, data_dir)
    if not path:
        return None
    try:
        df = pd.read_parquet(path)
    except Exception:
        return None
    cols = {c.lower(): c for c in df.columns}
    ts_col = cols.get("timestamp") or cols.get("ts")
    o_col = cols.get("open")
    h_col = cols.get("high")
    l_col = cols.get("low")
    c_col = cols.get("close")
    v_col = cols.get("volume")
    if not all([ts_col, o_col, h_col, l_col, c_col]):
        return None
    keep = [ts_col, o_col, h_col, l_col, c_col] + ([v_col] if v_col else [])
    out = df[keep].copy()
    out.columns = ["timestamp", "open", "high", "low", "close"] + (["volume"] if v_col else [])
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"])
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    if out.empty:
        return None
    return out.set_index("timestamp")


@dataclass
class LiveMoverAuditRow:
    symbol: str
    live_chg_pct: float
    live_rv: float | None
    live_mrs: float | None
    live_status: str
    setup_score: int
    setup_points: str
    y_date: str
    y_close: float
    y_vol_x20: float | None
    y_rng_x_atr14: float | None
    y_near_20d_high: bool
    y_near_52w_high: bool
    y_near_multiy_high: bool
    y_compress_10d: bool
    y_compress_20d: bool


def _bool_tag(b: bool) -> str:
    return "YES" if b else "NO"


def _score_setup(
    *,
    years: int,
    live_rv: float | None,
    y_vol_x20: float | None,
    y_rng_x_atr14: float | None,
    y_near_20d_high: bool,
    y_near_52w_high: bool,
    y_near_multiy_high: bool,
    y_compress_10d: bool,
    y_compress_20d: bool,
) -> tuple[int, list[str]]:
    """
    Points model (tunable, but intentionally simple + explainable):
    - Higher timeframe highs matter most (multi-year > 52W > 20D).
    - Compression matters (VCP-style).
    - Volume/range expansion yesterday are strong tells.
    - Live RV gives an intraday "confirmation" point.
    """
    pts = 0
    why: list[str] = []

    # Highs / breakout context
    if y_near_multiy_high:
        pts += 4
        why.append(f"{years}Y_HIGH(+4)")
    elif y_near_52w_high:
        pts += 3
        why.append("52W_HIGH(+3)")
    elif y_near_20d_high:
        pts += 2
        why.append("20D_HIGH(+2)")

    # Compression
    if y_compress_20d:
        pts += 2
        why.append("COMP20(+2)")
    if y_compress_10d:
        pts += 2
        why.append("COMP10(+2)")

    # Volume expansion yesterday
    if y_vol_x20 is not None and np.isfinite(y_vol_x20):
        if y_vol_x20 >= 3.0:
            pts += 3
            why.append("Y_VOLx20>=3(+3)")
        elif y_vol_x20 >= 2.0:
            pts += 2
            why.append("Y_VOLx20>=2(+2)")
        elif y_vol_x20 >= 1.5:
            pts += 1
            why.append("Y_VOLx20>=1.5(+1)")

    # Range / ATR expansion yesterday
    if y_rng_x_atr14 is not None and np.isfinite(y_rng_x_atr14):
        if y_rng_x_atr14 >= 2.0:
            pts += 3
            why.append("Y_RNG/ATR>=2(+3)")
        elif y_rng_x_atr14 >= 1.5:
            pts += 2
            why.append("Y_RNG/ATR>=1.5(+2)")
        elif y_rng_x_atr14 >= 1.2:
            pts += 1
            why.append("Y_RNG/ATR>=1.2(+1)")

    # Live confirmation (intraday)
    if live_rv is not None and np.isfinite(live_rv):
        if live_rv >= 2.0:
            pts += 2
            why.append("LIVE_RV>=2(+2)")
        elif live_rv >= 1.5:
            pts += 1
            why.append("LIVE_RV>=1.5(+1)")

    return int(pts), why


def _compute_yesterday_features(df: pd.DataFrame, years: int) -> dict | None:
    if df is None or df.empty or len(df) < 80:
        return None

    # Yesterday = last completed daily bar present in Parquet.
    i_y = int(len(df) - 1)
    if i_y < 25:
        return None

    o = df["open"].astype(float).to_numpy()
    h = df["high"].astype(float).to_numpy()
    l = df["low"].astype(float).to_numpy()
    c = df["close"].astype(float).to_numpy()
    v = df["volume"].astype(float).to_numpy() if "volume" in df.columns else None
    idx = df.index

    y_close = float(c[i_y])
    if not np.isfinite(y_close) or y_close <= 0:
        return None

    # y_vol_x20 = yesterday volume / avg volume of prior 20 sessions (excluding yesterday)
    y_vol_x20 = None
    if v is not None and i_y >= 21:
        base = v[i_y - 20 : i_y]
        denom = float(np.mean(base)) if base.size else 0.0
        if np.isfinite(denom) and denom > 0 and np.isfinite(v[i_y]):
            y_vol_x20 = float(v[i_y] / denom)

    # y_rng_x_atr14 = yesterday range / ATR14 (as of yesterday)
    y_rng_x_atr14 = None
    if i_y >= 16:
        atr = _atr14(df).to_numpy()
        if np.isfinite(atr[i_y]) and atr[i_y] > 0:
            y_rng = float(h[i_y] - l[i_y])
            y_rng_x_atr14 = float(y_rng / float(atr[i_y]))

    # near highs (use highs up to yesterday)
    y_near_20d_high = False
    if i_y >= 20:
        hh20 = float(np.nanmax(h[i_y - 19 : i_y + 1]))
        if np.isfinite(hh20) and hh20 > 0:
            y_near_20d_high = y_close >= 0.98 * hh20

    # 52-week ~ 252 trading days
    y_near_52w_high = False
    win_52w = 252
    if i_y >= min(win_52w, len(df) - 1):
        start = max(0, i_y - win_52w + 1)
        hh = float(np.nanmax(h[start : i_y + 1]))
        if np.isfinite(hh) and hh > 0:
            y_near_52w_high = y_close >= 0.98 * hh

    # Multi-year high (years * 252)
    y_near_multiy_high = False
    win_my = int(max(252, years * 252))
    if i_y >= min(win_my, len(df) - 1):
        start = max(0, i_y - win_my + 1)
        hh = float(np.nanmax(h[start : i_y + 1]))
        if np.isfinite(hh) and hh > 0:
            y_near_multiy_high = y_close >= 0.98 * hh

    # Compression: 10d/20d std of returns is low vs prior window
    rets = np.zeros_like(c)
    rets[1:] = np.where(c[:-1] > 0, (c[1:] / c[:-1] - 1.0), 0.0)
    y_compress_10d = False
    y_compress_20d = False
    if i_y >= 40:
        r10 = rets[i_y - 9 : i_y + 1]
        r10_prev = rets[i_y - 19 : i_y - 9]
        s10 = _rolling_std(r10)
        s10p = _rolling_std(r10_prev)
        if np.isfinite(s10) and np.isfinite(s10p) and s10p > 0:
            y_compress_10d = s10 <= 0.6 * s10p
        r20 = rets[i_y - 19 : i_y + 1]
        r20_prev = rets[i_y - 39 : i_y - 19]
        s20 = _rolling_std(r20)
        s20p = _rolling_std(r20_prev)
        if np.isfinite(s20) and np.isfinite(s20p) and s20p > 0:
            y_compress_20d = s20 <= 0.6 * s20p

    return {
        "y_date": str(idx[i_y].date()),
        "y_close": y_close,
        "y_vol_x20": y_vol_x20,
        "y_rng_x_atr14": y_rng_x_atr14,
        "y_near_20d_high": bool(y_near_20d_high),
        "y_near_52w_high": bool(y_near_52w_high),
        "y_near_multiy_high": bool(y_near_multiy_high),
        "y_compress_10d": bool(y_compress_10d),
        "y_compress_20d": bool(y_compress_20d),
    }


def _iter_live_movers(threshold: float) -> list[dict]:
    shm = SHMBridge()
    shm.setup(is_master_hint=False)

    out = []
    for r in shm.arr:
        sym = _decode_shm_str(r["symbol"])
        if not sym or not sym.endswith("-EQ"):
            continue  # "stock" only
        try:
            chg = float(r["change_pct"])
        except Exception:
            continue
        if not np.isfinite(chg) or chg < threshold:
            continue

        def _f(k):
            try:
                v = float(r[k])
                return v if np.isfinite(v) else None
            except Exception:
                return None

        out.append(
            {
                "symbol": sym,
                "change_pct": float(chg),
                "rv": _f("rv"),
                "mrs": _f("mrs"),
                "status": _decode_shm_str(r["status"]),
            }
        )

    out.sort(key=lambda x: x["change_pct"], reverse=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit live >=X% movers and print yesterday setup features.")
    ap.add_argument("--threshold", type=float, default=10.0, help="Live CHG%% >= threshold (from SHM).")
    ap.add_argument("--max", type=int, default=25, help="Max movers to print.")
    ap.add_argument("--years", type=int, default=3, help="Multi-year breakout window (years * 252 bars).")
    ap.add_argument("--data-dir", default=None, help="Override Parquet dir (defaults to settings.PIPELINE_DATA_DIR).")
    ap.add_argument("--min-score", type=int, default=0, help="Only show rows with setup score >= this.")
    args = ap.parse_args()

    thr = float(args.threshold)
    max_n = int(args.max)
    years = int(args.years)
    data_dir = os.path.abspath(args.data_dir or settings.PIPELINE_DATA_DIR)

    movers = _iter_live_movers(thr)[:max_n]
    print(f"Live movers >= {thr:.2f}%: {len(movers)} (showing up to {max_n})")
    print(f"Parquet dir: {data_dir}")
    if not movers:
        return

    rows: list[LiveMoverAuditRow] = []
    for m in movers:
        sym = m["symbol"]
        df = _load_daily_ohlcv(sym, data_dir)
        feats = _compute_yesterday_features(df, years=years)
        if not feats:
            score, why = _score_setup(
                years=years,
                live_rv=m.get("rv"),
                y_vol_x20=None,
                y_rng_x_atr14=None,
                y_near_20d_high=False,
                y_near_52w_high=False,
                y_near_multiy_high=False,
                y_compress_10d=False,
                y_compress_20d=False,
            )
            rows.append(
                LiveMoverAuditRow(
                    symbol=sym,
                    live_chg_pct=float(m["change_pct"]),
                    live_rv=m.get("rv"),
                    live_mrs=m.get("mrs"),
                    live_status=str(m.get("status") or "").strip(),
                    setup_score=int(score),
                    setup_points=",".join(why) if why else "—",
                    y_date="NA",
                    y_close=float("nan"),
                    y_vol_x20=None,
                    y_rng_x_atr14=None,
                    y_near_20d_high=False,
                    y_near_52w_high=False,
                    y_near_multiy_high=False,
                    y_compress_10d=False,
                    y_compress_20d=False,
                )
            )
            continue
        score, why = _score_setup(
            years=years,
            live_rv=m.get("rv"),
            y_vol_x20=feats["y_vol_x20"],
            y_rng_x_atr14=feats["y_rng_x_atr14"],
            y_near_20d_high=bool(feats["y_near_20d_high"]),
            y_near_52w_high=bool(feats["y_near_52w_high"]),
            y_near_multiy_high=bool(feats["y_near_multiy_high"]),
            y_compress_10d=bool(feats["y_compress_10d"]),
            y_compress_20d=bool(feats["y_compress_20d"]),
        )
        rows.append(
            LiveMoverAuditRow(
                symbol=sym,
                live_chg_pct=float(m["change_pct"]),
                live_rv=m.get("rv"),
                live_mrs=m.get("mrs"),
                live_status=str(m.get("status") or "").strip(),
                setup_score=int(score),
                setup_points=",".join(why) if why else "—",
                y_date=str(feats["y_date"]),
                y_close=float(feats["y_close"]),
                y_vol_x20=feats["y_vol_x20"],
                y_rng_x_atr14=feats["y_rng_x_atr14"],
                y_near_20d_high=bool(feats["y_near_20d_high"]),
                y_near_52w_high=bool(feats["y_near_52w_high"]),
                y_near_multiy_high=bool(feats["y_near_multiy_high"]),
                y_compress_10d=bool(feats["y_compress_10d"]),
                y_compress_20d=bool(feats["y_compress_20d"]),
            )
        )

    rows.sort(key=lambda r: (r.setup_score, r.live_chg_pct), reverse=True)
    min_score = int(args.min_score)
    rows = [r for r in rows if int(r.setup_score) >= min_score]

    # Print scored report
    for r in rows:
        print(
            f"\n[{r.setup_score:02d}] {r.symbol} | LIVE chg={r.live_chg_pct:.2f}%"
            f" rv={(f'{r.live_rv:.2f}x' if r.live_rv is not None else 'NA')}"
            f" mrs={(f'{r.live_mrs:.2f}' if r.live_mrs is not None else 'NA')}"
            f" status={r.live_status or '—'}"
        )
        print(f"  points: {r.setup_points}")
        print(
            f"  yesterday {r.y_date} close={(f'{r.y_close:.2f}' if np.isfinite(r.y_close) else 'NA')}"
            f" | vol_x20={(f'{r.y_vol_x20:.2f}' if r.y_vol_x20 is not None else 'NA')}"
            f" rng_x_atr14={(f'{r.y_rng_x_atr14:.2f}' if r.y_rng_x_atr14 is not None else 'NA')}"
        )
        print(
            "  near_highs:"
            f" 20D={_bool_tag(r.y_near_20d_high)}"
            f" 52W={_bool_tag(r.y_near_52w_high)}"
            f" {years}Y={_bool_tag(r.y_near_multiy_high)}"
            f" | compress: 10D={_bool_tag(r.y_compress_10d)} 20D={_bool_tag(r.y_compress_20d)}"
        )


if __name__ == "__main__":
    main()

