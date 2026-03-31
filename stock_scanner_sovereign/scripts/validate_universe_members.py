#!/usr/bin/env python3
"""CLI: validate universe_members vs canonical CSV. Default: Nifty 50 + Nifty 500. Use --all for all sidebar universes."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.constants import SYMBOL_GROUPS
from utils.universe_validation import validate_universe_members_vs_canonical_csv


def main() -> None:
    ap = argparse.ArgumentParser(description="Diff Postgres universe_members vs SYMBOL_GROUPS CSV files.")
    ap.add_argument(
        "--all",
        action="store_true",
        help="Validate all sidebar universes (Nifty 50 … All NSE Stocks)",
    )
    args = ap.parse_args()
    names = tuple(SYMBOL_GROUPS.keys()) if args.all else None
    r = validate_universe_members_vs_canonical_csv(universe_names=names)
    print(json.dumps(r, indent=2))
    bad = [k for k, v in r.items() if not v.get("ok")]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
