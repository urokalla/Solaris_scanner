#!/usr/bin/env python3
"""CLI: validate universe_members (Nifty 50 + Nifty 500 only) vs canonical CSV. Run with DB env set (e.g. inside compose)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.universe_validation import validate_universe_members_vs_canonical_csv


def main() -> None:
    r = validate_universe_members_vs_canonical_csv()
    print(json.dumps(r, indent=2))
    bad = [k for k, v in r.items() if not v.get("ok")]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
