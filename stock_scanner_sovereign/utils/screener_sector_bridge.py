"""
Screener.in **Browse sectors** are labels only (~59). We map each to a coarse
Nifty-equivalent ``Industry`` string that appears on NSE index constituent CSVs
in this repo, then join to ``symbol_industry_master.csv`` for names + history keys.

Refresh master: ``python3 scripts/build_symbol_industry_master.py``
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

_PKG = Path(__file__).resolve().parents[1]
SCREENER_SECTORS_FILE = _PKG / "data" / "screener_browse_sectors.txt"
SCREENER_TO_NIFTY_FILE = _PKG / "data" / "screener_sector_to_nifty_industry.csv"
DEFAULT_MASTER_FILE = _PKG / "data" / "symbol_industry_master.csv"


def load_screener_sectors(path: Path | None = None) -> list[str]:
    p = path or SCREENER_SECTORS_FILE
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


def load_screener_to_nifty(path: Path | None = None) -> dict[str, str]:
    p = path or SCREENER_TO_NIFTY_FILE
    out: dict[str, str] = {}
    with p.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            s = (row.get("screener_sector") or "").strip()
            n = (row.get("nifty_industry") or "").strip()
            if s and n:
                out[s] = n
    return out


def load_symbol_industry_master(path: Path | None = None) -> list[dict[str, str]]:
    p = path or DEFAULT_MASTER_FILE
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def iter_symbols_for_screener_sector(
    screener_sector: str,
    *,
    master: list[dict[str, str]] | None = None,
    mapping: dict[str, str] | None = None,
) -> Iterator[dict[str, str]]:
    m = master if master is not None else load_symbol_industry_master()
    mp = mapping if mapping is not None else load_screener_to_nifty()
    nifty = mp.get(screener_sector.strip())
    if nifty:
        for row in m:
            if (row.get("industry") or "").strip() == nifty:
                yield row


def symbols_for_screener_sector(
    screener_sector: str,
    *,
    master: list[dict[str, str]] | None = None,
    mapping: dict[str, str] | None = None,
) -> list[str]:
    return [r["symbol_nse"] for r in iter_symbols_for_screener_sector(screener_sector, master=master, mapping=mapping)]
