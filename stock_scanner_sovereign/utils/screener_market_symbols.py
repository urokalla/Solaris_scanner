"""
Screener **market** sector lists under ``data/screener_market/<CODE>.csv``,
registered in ``sector_index.json``.

Used by the main dashboard sector filter: intersect universe ∩ sector tickers.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

from utils.screener_market_csv import load_sector_index

_PKG = Path(__file__).resolve().parents[1]
_MARKET_DIR = _PKG / "data" / "screener_market"


def _nk(x: str) -> str:
    """Match ``scanner.get_ui_view`` naked-key: alphanumeric only, upper."""
    t = str(x or "").upper().strip()
    if ":" in t:
        t = t.split(":", 1)[1]
    t = t.replace("-INDEX", "")
    if "-" in t:
        t = t.rsplit("-", 1)[0]
    return re.sub(r"[^A-Z0-9]", "", t)


@lru_cache(maxsize=1)
def _label_to_code() -> tuple[tuple[str, str], ...]:
    rows = load_sector_index()
    return tuple((s["label"], s["code"]) for s in rows)


@lru_cache(maxsize=128)
def _rows_for_code(code: str) -> tuple[tuple[str, str, str], ...]:
    p = _MARKET_DIR / f"{code}.csv"
    if not p.is_file():
        return ()
    out: list[tuple[str, str, str]] = []
    with p.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sym = (row.get("symbol") or "").strip()
            if sym:
                out.append((sym, (row.get("company_name") or "").strip(), _nk(sym)))
    return tuple(out)


def market_sector_csv_stem(dashboard_sector: str) -> str | None:
    label = (dashboard_sector or "").strip()
    for L, C in _label_to_code():
        if L == label:
            return C
    return None


def symbol_nks_for_dashboard_sector(dashboard_sector: str) -> frozenset[str]:
    code = market_sector_csv_stem(dashboard_sector)
    if not code:
        return frozenset()
    return frozenset(r[2] for r in _rows_for_code(code) if r[2])
