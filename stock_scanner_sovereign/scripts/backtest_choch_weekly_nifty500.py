#!/usr/bin/env python3
"""
Weekly backtest: LuxAlgo-style *internal* CHoCH (structure length=5) + Option A EMA sweep.

- CHoCH tag when close crosses pivot *against* prior internal trend (mirrors LuxAlgo displayStructure internal).
- Option A (bullish CHoCH): valid if low < EMA_k and close > EMA_k for some k in {9,10,20,21}; label = argmin_k |low - EMA_k| among valid k.
- Bearish CHoCH: high > EMA_k and close < EMA_k; label = argmin |high - EMA_k|.
- Also: Option A on weeks +1, +2, +3 after CHoCH (same direction rule).

Data: Parquet under fyers_data_pipeline/data/historical (NSE_SYMBOL_EQ.parquet).
Universe: stock_scanner_sovereign/data/nifty500.csv Symbol column.

This is a research script, not trading advice.
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field

import pandas as pd

# Project root: …/RS_PROJECT on host; in pipeline container scripts live under /app/stock_scanner_sovereign → parent is /app (fyers root).
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.isdir(os.path.join(_ROOT, "fyers_data_pipeline", "data", "historical")):
    HIST = os.path.join(_ROOT, "fyers_data_pipeline", "data", "historical")
else:
    HIST = os.environ.get("PIPELINE_DATA_DIR", os.path.join(_ROOT, "data", "historical"))

NIFTY500_CSV = os.path.join(_ROOT, "stock_scanner_sovereign", "data", "nifty500.csv")

INTERNAL_SIZE = 5
EMA_PERIODS = (9, 10, 20, 21)

BEARISH_LEG = 0
BULLISH_LEG = 1
BEARISH = -1
NEUTRAL = 0
BULLISH = 1


def _nan() -> float:
    return float("nan")


@dataclass
class Pivot:
    current: float = field(default_factory=lambda: _nan())
    last: float = field(default_factory=lambda: _nan())
    crossed: bool = False


@dataclass
class Trend:
    bias: int = NEUTRAL


def _leg_at_i(high: pd.Series, low: pd.Series, size: int, i: int, prev_leg: int) -> int:
    if i < size:
        return prev_leg
    h_at = float(high.iloc[i - size])
    max_recent = float(high.iloc[i - size + 1 : i + 1].max())
    new_leg_high = h_at > max_recent
    l_at = float(low.iloc[i - size])
    min_recent = float(low.iloc[i - size + 1 : i + 1].min())
    new_leg_low = l_at < min_recent
    if new_leg_high:
        return BEARISH_LEG
    if new_leg_low:
        return BULLISH_LEG
    return prev_leg


def _crossover(close: pd.Series, level: float, i: int) -> bool:
    if i < 1 or (isinstance(level, float) and math.isnan(level)):
        return False
    return float(close.iloc[i]) > level and float(close.iloc[i - 1]) <= level


def _crossunder(close: pd.Series, level: float, i: int) -> bool:
    if i < 1 or (isinstance(level, float) and math.isnan(level)):
        return False
    return float(close.iloc[i]) < level and float(close.iloc[i - 1]) >= level


def _option_a_bull(low: float, close: float, emas: dict[int, float]) -> tuple[bool, int | None]:
    """Returns (valid, best_k) — best_k = argmin |low - ema| among k satisfying low < ema < close (spring)."""
    valid_ks = []
    for k in EMA_PERIODS:
        e = emas[k]
        if isinstance(e, float) and math.isnan(e):
            continue
        if low < e and close > e:
            valid_ks.append((k, abs(low - e)))
    if not valid_ks:
        return False, None
    valid_ks.sort(key=lambda x: x[1])
    return True, valid_ks[0][0]


def _option_a_bear(high: float, close: float, emas: dict[int, float]) -> tuple[bool, int | None]:
    valid_ks = []
    for k in EMA_PERIODS:
        e = emas[k]
        if isinstance(e, float) and math.isnan(e):
            continue
        if high > e and close < e:
            valid_ks.append((k, abs(high - e)))
    if not valid_ks:
        return False, None
    valid_ks.sort(key=lambda x: x[1])
    return True, valid_ks[0][0]


def load_weekly(symbol_fyers: str) -> pd.DataFrame | None:
    clean = symbol_fyers.replace(":", "_").replace("-", "_")
    path = os.path.join(HIST, f"{clean}.parquet")
    if not os.path.isfile(path):
        return None
    df = pd.read_parquet(path)
    if df.empty or "timestamp" not in df.columns:
        return None
    df = df.sort_values("timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
    df = df.set_index("timestamp")
    w = df.resample("W-FRI").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    w = w.dropna(subset=["close"])
    if len(w) < max(INTERNAL_SIZE + 5, max(EMA_PERIODS) + 5):
        return None
    return w


def simulate_internal_choch_and_sweeps(weekly: pd.DataFrame) -> list[dict]:
    """One pass; returns list of CHoCH events with Option A flags."""
    high = weekly["high"]
    low = weekly["low"]
    close = weekly["close"]
    n = len(weekly)

    ema = {k: close.ewm(span=k, adjust=False).mean() for k in EMA_PERIODS}

    ih, il_ = Pivot(), Pivot()
    it = Trend()

    prev_leg = BEARISH_LEG
    events: list[dict] = []

    for i in range(n):
        leg = _leg_at_i(high, low, INTERNAL_SIZE, i, prev_leg)
        new_pivot = leg != prev_leg
        # LuxAlgo: ta.change(leg)==+1 bullish leg, ==-1 bearish leg
        pivot_low = new_pivot and leg == BULLISH_LEG and prev_leg == BEARISH_LEG
        pivot_high = new_pivot and leg == BEARISH_LEG and prev_leg == BULLISH_LEG

        if pivot_low and i >= INTERNAL_SIZE:
            il_.last = il_.current
            il_.current = float(low.iloc[i - INTERNAL_SIZE])
            il_.crossed = False
        if pivot_high and i >= INTERNAL_SIZE:
            ih.last = ih.current
            ih.current = float(high.iloc[i - INTERNAL_SIZE])
            ih.crossed = False

        prev_leg = leg

        emas_i = {k: float(ema[k].iloc[i]) for k in EMA_PERIODS}
        lo = float(low.iloc[i])
        hi = float(high.iloc[i])
        cl = float(close.iloc[i])

        # Internal bullish structure: cross above internal high
        if not (isinstance(ih.current, float) and math.isnan(ih.current)) and _crossover(close, ih.current, i) and not ih.crossed:
            is_choch = it.bias == BEARISH
            tag = "CHoCH" if is_choch else "BOS"
            ih.crossed = True
            it.bias = BULLISH
            if is_choch:
                ok, k_best = _option_a_bull(lo, cl, emas_i)
                events.append(
                    {
                        "bar": weekly.index[i],
                        "i_idx": i,
                        "dir": "bullish",
                        "tag": tag,
                        "option_a_valid": ok,
                        "option_a_ema": k_best,
                    }
                )

        # Internal bearish: cross under internal low
        if not (isinstance(il_.current, float) and math.isnan(il_.current)) and _crossunder(close, il_.current, i) and not il_.crossed:
            is_choch = it.bias == BULLISH
            tag = "CHoCH" if is_choch else "BOS"
            il_.crossed = True
            it.bias = BEARISH
            if is_choch:
                ok, k_best = _option_a_bear(hi, cl, emas_i)
                events.append(
                    {
                        "bar": weekly.index[i],
                        "i_idx": i,
                        "dir": "bearish",
                        "tag": tag,
                        "option_a_valid": ok,
                        "option_a_ema": k_best,
                    }
                )

    return events


def forward_option_a_flags(weekly: pd.DataFrame, i_ch: int, direction: str) -> dict:
    """Option A on forward weeks 1..3 only (not same week)."""
    close = weekly["close"]
    high = weekly["high"]
    low = weekly["low"]
    n = len(weekly)
    ema = {k: close.ewm(span=k, adjust=False).mean() for k in EMA_PERIODS}
    out: dict[str, bool | None] = {}
    for h in (1, 2, 3):
        j = i_ch + h
        if j >= n:
            out[f"optA_week_plus_{h}"] = None
            continue
        emas_j = {k: float(ema[k].iloc[j]) for k in EMA_PERIODS}
        lo, hi, cl = float(low.iloc[j]), float(high.iloc[j]), float(close.iloc[j])
        if direction == "bullish":
            ok, _ = _option_a_bull(lo, cl, emas_j)
        else:
            ok, _ = _option_a_bear(hi, cl, emas_j)
        out[f"optA_week_plus_{h}"] = ok
    w1, w2, w3 = out.get("optA_week_plus_1"), out.get("optA_week_plus_2"), out.get("optA_week_plus_3")
    any_fwd = any(x is True for x in (w1, w2, w3))
    first = None
    for h in (1, 2, 3):
        k = out.get(f"optA_week_plus_{h}")
        if k is True:
            first = h
            break
    out["optA_any_of_next_3_weeks"] = any_fwd
    out["optA_first_forward_week"] = first
    return out


def main() -> None:
    if not os.path.isfile(NIFTY500_CSV):
        print("Missing nifty500.csv", file=sys.stderr)
        sys.exit(1)
    uni = pd.read_csv(NIFTY500_CSV)
    sym_col = "Symbol" if "Symbol" in uni.columns else uni.columns[2]
    symbols = uni[sym_col].astype(str).str.strip().tolist()

    all_choch: list[dict] = []
    missing: list[str] = []
    for sym in symbols:
        fy = f"NSE:{sym}-EQ"
        w = load_weekly(fy)
        if w is None:
            missing.append(sym)
            continue
        ev = simulate_internal_choch_and_sweeps(w)
        for e in ev:
            e["symbol"] = sym
            if e.get("tag") == "CHoCH" and "i_idx" in e:
                fwd = forward_option_a_flags(w, int(e["i_idx"]), str(e["dir"]))
                e.update(fwd)
            all_choch.append(e)

    df = pd.DataFrame(all_choch)
    if df.empty:
        print("No CHoCH events (no data or no pivots). Missing parquet:", len(missing), "symbols")
        sys.exit(0)

    choch = df[df["tag"] == "CHoCH"].copy()
    n_ch = len(choch)
    n_valid = int(choch["option_a_valid"].sum()) if n_ch else 0

    print("=== Nifty 500 weekly — LuxAlgo-style internal CHoCH (length=5) + Option A EMA sweep ===\n")
    print(f"Universe symbols in CSV: {len(symbols)}")
    print(f"Symbols with missing parquet: {len(missing)}")
    print(f"Total internal CHoCH events (all symbols, all history): {n_ch}")
    print(f"Option A valid sweep same week: {n_valid} ({100 * n_valid / n_ch:.1f}% of CHoCH)\n")

    if n_ch and "optA_any_of_next_3_weeks" in choch.columns:
        n_fwd = int(choch["optA_any_of_next_3_weeks"].sum())
        print("Option A in week +1, +2, or +3 after CHoCH (same rule; not counting same week):")
        print(f"  Hits in at least one of the next 3 weeks: {n_fwd} ({100 * n_fwd / n_ch:.1f}% of CHoCH)")
        for h in (1, 2, 3):
            col = f"optA_week_plus_{h}"
            if col in choch.columns:
                hits = int((choch[col] == True).sum())
                print(f"  Week +{h} specifically: {hits} ({100 * hits / n_ch:.1f}% of CHoCH)")
        if "optA_first_forward_week" in choch.columns:
            fc = choch["optA_first_forward_week"].dropna()
            if len(fc):
                print("\nFirst forward week where Option A hits (only events with ≥1 hit in +1..+3):")
                print(fc.astype(int).value_counts().sort_index().to_string())
        print()

    if n_ch:
        vc = choch["option_a_ema"].value_counts(dropna=True)
        print("Among Option-A–valid CHoCH, which EMA was closest (tie-break):")
        print(vc.to_string())
        print()
        print("Direction split (CHoCH):")
        print(choch["dir"].value_counts().to_string())
        print()

    out_csv = os.path.join(_ROOT, "stock_scanner_sovereign", "data", "backtest_choch_weekly_events.csv")
    df.to_csv(out_csv, index=False)
    print(f"Per-event CSV written: {out_csv}")


if __name__ == "__main__":
    main()
