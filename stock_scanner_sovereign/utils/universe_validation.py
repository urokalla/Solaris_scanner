"""
Layer-1 checks: compare Postgres `universe_members` to canonical CSV for **Nifty 50** and **Nifty 500** only.

Other universes / indices are out of scope here on purpose (see `DASHBOARD_BENCHMARK_MAP` in `utils.constants`).
"""
from __future__ import annotations

import csv
import os
from typing import Any

from utils.constants import CANONICAL_MEMBERSHIP_UNIVERSES, SYMBOL_GROUPS


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _symbols_from_csv_path(path: str) -> set[str]:
    """Same normalization rules as `scripts/seed_universes.py`."""
    sn: list[str] = []
    if path.endswith(".txt"):
        with open(path) as f:
            sn = [l.strip().upper() for l in f if l.strip()]
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
) -> dict[str, dict[str, Any]]:
    """
    For each universe in CANONICAL_MEMBERSHIP_UNIVERSES, diff DB `universe_members`
    vs the corresponding file in SYMBOL_GROUPS.

    Returns per-universe dicts: ok, db_count, csv_count, missing_in_db, extra_in_db, csv_path, error.
    """
    from backend.database import DatabaseManager

    db = db or DatabaseManager()
    base = _repo_root()
    out: dict[str, dict[str, Any]] = {}

    for display_name in CANONICAL_MEMBERSHIP_UNIVERSES:
        rel = SYMBOL_GROUPS.get(display_name)
        if not rel:
            out[display_name] = {"ok": False, "error": f"No SYMBOL_GROUPS entry for {display_name!r}"}
            continue
        path = os.path.join(base, rel)
        if not os.path.isfile(path):
            out[display_name] = {"ok": False, "error": f"Missing CSV: {path}", "csv_path": path}
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
