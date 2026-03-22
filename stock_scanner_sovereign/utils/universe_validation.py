"""
Layer-1 checks: compare Postgres `universe_members` to CSV files listed in `SYMBOL_GROUPS`.

By default `validate_universe_members_vs_canonical_csv` still targets **Nifty 50** and **Nifty 500** only
(`CANONICAL_MEMBERSHIP_UNIVERSES`) so existing CI/scripts keep the same behavior. Pass an explicit
`universe_names` list (e.g. all keys from `SYMBOL_GROUPS`) to validate every sidebar universe.
"""
from __future__ import annotations

import csv
import os
from typing import Any, Sequence

from utils.constants import CANONICAL_MEMBERSHIP_UNIVERSES, SYMBOL_GROUPS


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def expected_symbols_for_universe(display_name: str) -> set[str]:
    """Symbols from the canonical membership file for `display_name` (empty if missing)."""
    path = canonical_csv_path_for_universe(display_name)
    if not path:
        return set()
    return _symbols_from_csv_path(path)


def canonical_csv_path_for_universe(display_name: str) -> str | None:
    """
    Resolved path to the membership file for `display_name`, using the same fallbacks as
    `scripts/seed_universes.py` (e.g. `available_symbols.txt` when `NSE_EQ.csv` is missing).
    """
    base = _repo_root()
    rel = SYMBOL_GROUPS.get(display_name)
    if not rel:
        return None
    p = os.path.join(base, rel)
    if not os.path.isfile(p) and display_name == "All NSE Stocks":
        alt = os.path.join(base, "data/available_symbols.txt")
        if os.path.isfile(alt):
            return alt
    return p if os.path.isfile(p) else None


def _symbols_from_csv_path(path: str) -> set[str]:
    """Same normalization rules as `scripts/seed_universes.py` (incl. bare tickers -> NSE:…-EQ)."""
    sn: list[str] = []
    if path.endswith(".txt"):
        with open(path) as f:
            for line in f:
                s = line.strip().upper()
                if not s:
                    continue
                # Match CSV branch: Parquet / Fyers use NSE:SYMBOL-EQ, not bare 20MICRONS
                sn.append(
                    s
                    if s.startswith("NSE:")
                    else (f"NSE:{s}" if "INDEX" in s else f"NSE:{s}-EQ")
                )
    else:
        with open(path, encoding="utf-8-sig") as f:
            r = csv.DictReader(f)
            c = next((h for h in r.fieldnames if h.lower() == "symbol"), r.fieldnames[0])
            for row in r:
                v = row.get(c)
                s = v.strip().upper() if v else ""
                if s:
                    sn.append(
                        s
                        if s.startswith("NSE:")
                        else (f"NSE:{s}" if "INDEX" in s else f"NSE:{s}-EQ")
                    )
    return set(sn)


def validate_universe_members_vs_canonical_csv(
    db: Any | None = None,
    universe_names: Sequence[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    For each universe in `universe_names` (default: `CANONICAL_MEMBERSHIP_UNIVERSES` only), diff DB
    `universe_members` vs the canonical file (see `canonical_csv_path_for_universe`).

    Returns per-universe dicts: ok, db_count, csv_count, missing_in_db, extra_in_db, csv_path, error.
    """
    from backend.database import DatabaseManager

    db = db or DatabaseManager()
    names = tuple(universe_names) if universe_names is not None else CANONICAL_MEMBERSHIP_UNIVERSES
    out: dict[str, dict[str, Any]] = {}

    for display_name in names:
        path = canonical_csv_path_for_universe(display_name)
        if not path:
            rel = SYMBOL_GROUPS.get(display_name, "")
            out[display_name] = {
                "ok": False,
                "error": f"Missing or unknown membership file for {display_name!r} ({rel})",
                "csv_path": os.path.join(_repo_root(), rel) if rel else "",
            }
            continue
        try:
            expected = _symbols_from_csv_path(path)
            actual = set(db.get_symbols_by_universe(display_name))
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            out[display_name] = {
                "ok": len(missing) == 0 and len(extra) == 0,
                "db_count": len(actual),
                "csv_count": len(expected),
                "missing_in_db": missing,
                "extra_in_db": extra,
                "csv_path": path,
            }
        except Exception as e:
            out[display_name] = {"ok": False, "error": str(e), "csv_path": path}
    return out
