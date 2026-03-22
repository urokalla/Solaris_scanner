"""
Parquet history coverage for universe symbols (same paths as `PipelineBridge` / RS baseline load).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd

# Calendar-day span considered "5 years" (allow weekends/holidays slack vs trading-day count).
MIN_YEARS_DEFAULT = 5.0
SLACK_DAYS = 45


def parquet_filename_candidates(symbol: str) -> list[str]:
    """Match `utils.pipeline_bridge.PipelineBridge._files`."""
    c = symbol.strip().upper().replace(":", "_")
    u = c.replace("-", "_")
    while "__" in u:
        u = u.replace("__", "_")
    return [f"{u}.parquet", f"{c}.parquet"]


def _naked_key(text: str) -> str:
    """Same idea as `backend.scanner_math.load_historical_baseline` `get_naked` — map file/symbol to one key."""
    return (
        str(text)
        .upper()
        .replace("NSE:", "")
        .replace("NSE_", "")
        .replace("-EQ", "")
        .replace("_EQ", "")
        .replace("-INDEX", "")
        .replace("_INDEX", "")
        .replace(".PARQUET", "")
        .replace("-", "")
        .replace("_", "")
    )


def resolve_parquet_path(symbol: str, data_dir: str) -> str | None:
    for name in parquet_filename_candidates(symbol):
        p = os.path.join(data_dir, name)
        if os.path.isfile(p):
            return p
    # Bare tickers (e.g. from legacy DB) and `available_symbols.txt` lines: match scanner_math filename scan
    key = _naked_key(symbol)
    if not key or not os.path.isdir(data_dir):
        return None
    try:
        for fn in os.listdir(data_dir):
            if not fn.upper().endswith(".PARQUET"):
                continue
            if _naked_key(fn) == key:
                return os.path.join(data_dir, fn)
    except OSError:
        return None
    return None


def _timestamp_bounds(path: str) -> tuple[datetime | None, datetime | None, int]:
    """Return (min_ts, max_ts, row_count) in UTC-aware datetimes where possible."""
    try:
        part = pd.read_parquet(path)
        ts_col = next((c for c in part.columns if c.lower() in ("timestamp", "ts")), None)
        if ts_col is None:
            return None, None, 0
        n = len(part)
        if n == 0:
            return None, None, 0
        ts = pd.to_datetime(part[ts_col], utc=True)
        mn = ts.min()
        mx = ts.max()
        if pd.isna(mn) or pd.isna(mx):
            return None, None, n
        if isinstance(mn, pd.Timestamp):
            mn = mn.to_pydatetime()
        if isinstance(mx, pd.Timestamp):
            mx = mx.to_pydatetime()
        if getattr(mn, "tzinfo", None) is None:
            mn = mn.replace(tzinfo=timezone.utc)  # type: ignore[union-attr]
        else:
            mn = mn.astimezone(timezone.utc)  # type: ignore[union-attr]
        if getattr(mx, "tzinfo", None) is None:
            mx = mx.replace(tzinfo=timezone.utc)  # type: ignore[union-attr]
        else:
            mx = mx.astimezone(timezone.utc)  # type: ignore[union-attr]
        return mn, mx, n
    except Exception:
        return None, None, 0


def audit_parquet_file(
    path: str,
    min_years: float = MIN_YEARS_DEFAULT,
) -> dict[str, Any]:
    """
    Audit a single `.parquet` file on disk (any filename under the historical tree).
    Same span rule as `audit_symbol_parquet`.
    """
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return {
            "file": path,
            "status": "missing",
            "span_days": None,
            "rows": 0,
            "ok": False,
        }
    mn, mx, rows = _timestamp_bounds(path)
    if mn is None or mx is None or rows == 0:
        return {
            "file": path,
            "status": "empty_or_unreadable",
            "span_days": None,
            "min_ts": None,
            "max_ts": None,
            "rows": rows,
            "ok": False,
        }
    span_days = (mx - mn).days
    need_days = int(min_years * 365) - SLACK_DAYS
    ok = span_days >= need_days
    return {
        "file": path,
        "status": "ok_5y" if ok else "short_span",
        "span_days": span_days,
        "need_days": need_days,
        "min_ts": mn.isoformat(),
        "max_ts": mx.isoformat(),
        "rows": rows,
        "ok": ok,
    }


def audit_symbol_parquet(
    symbol: str,
    data_dir: str,
    min_years: float = MIN_YEARS_DEFAULT,
) -> dict[str, Any]:
    """
    Check whether a symbol has a parquet file under `data_dir` spanning at least `min_years` (calendar).
    New listings may legitimately have less than 5 years — reported as `short_span` with `span_days`.
    """
    path = resolve_parquet_path(symbol, data_dir)
    if not path:
        return {
            "symbol": symbol,
            "status": "missing_file",
            "parquet_path": None,
            "span_days": None,
            "min_ts": None,
            "max_ts": None,
            "rows": 0,
            "ok": False,
        }
    mn, mx, rows = _timestamp_bounds(path)
    if mn is None or mx is None or rows == 0:
        return {
            "symbol": symbol,
            "status": "empty_or_unreadable",
            "parquet_path": path,
            "span_days": None,
            "min_ts": None,
            "max_ts": None,
            "rows": rows,
            "ok": False,
        }
    span_days = (mx - mn).days
    need_days = int(min_years * 365) - SLACK_DAYS
    ok = span_days >= need_days
    status = "ok" if ok else "short_span"
    return {
        "symbol": symbol,
        "status": status,
        "parquet_path": path,
        "span_days": span_days,
        "min_ts": mn.isoformat(),
        "max_ts": mx.isoformat(),
        "rows": rows,
        "ok": ok,
        "need_days": need_days,
    }


def audit_universe_parquet(
    symbols: list[str],
    data_dir: str,
    min_years: float = MIN_YEARS_DEFAULT,
) -> dict[str, Any]:
    """Summary over a list of symbols (e.g. Nifty 50 members)."""
    per = [audit_symbol_parquet(s, data_dir, min_years=min_years) for s in symbols]
    bad = [p for p in per if not p.get("ok")]
    return {
        "data_dir": data_dir,
        "min_years": min_years,
        "symbols_checked": len(per),
        "ok_count": sum(1 for p in per if p.get("ok")),
        "fail_count": len(bad),
        "per_symbol": per,
        "failed_symbols": [p["symbol"] for p in bad],
    }
