#!/usr/bin/env python3
"""
Download official Nifty **sectoral** index constituent CSVs from niftyindices.com.

Source listing: https://www.niftyindices.com/indices/equity/sectoral-indices

Each index page embeds a link like:
  https://www.niftyindices.com/IndexConstituent/ind_<name>.csv

This script discovers that filename from the HTML (no hardcoded guesses), then
saves files under ``data/nifty_sectoral/``.

Usage (from repo root, or anywhere with PYTHONPATH=stock_scanner_sovereign)::

    cd stock_scanner_sovereign && PYTHONPATH=. python3 scripts/fetch_nifty_sectoral_constituents.py

Optional: ``--dry-run`` only prints discovered URLs.
"""
from __future__ import annotations

import argparse
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://www.niftyindices.com"
LIST_URL = f"{BASE}/indices/equity/sectoral-indices"
CONSTITUENT_RE = re.compile(
    r"https?://(?:www\.)?niftyindices\.com/IndexConstituent/(ind_[^\s\"'<>]+\.csv)",
    re.I,
)
REL_CONSTITUENT_RE = re.compile(r"/IndexConstituent/(ind_[^\s\"'<>]+\.csv)", re.I)

# Fallback slugs if the listing page changes (must match site paths under sectoral-indices/).
SECTORAL_SLUGS: tuple[str, ...] = (
    "nifty-auto",
    "nifty-bank",
    "nifty-cement",
    "nifty-chemicals",
    "nifty-financial-services",
    "nifty-financial-services-25-50-index",
    "nifty-financial--services-ex-bank",
    "nifty-fmcg",
    "nifty-healthcare-index",
    "nifty-it",
    "nifty-media",
    "nifty-metal",
    "nifty-pharma",
    "nifty-private-bank",
    "nifty-psu-bank",
    "nifty-realty",
    "nifty-reits-realty",
    "nifty-consumer-durables-index",
    "nifty-oil-and-gas-index",
    "nifty500-healthcare",
    "nifty-midsmall--financial-services",
    "nifty-midsmallhealthcare",
    "nifty-midsmall--it-telecom",
)


def _fetch(url: str, timeout: int = 45) -> str:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; RS_PROJECT/constituent-fetch)",
            "Accept": "text/html,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="replace")


def discover_csv_for_slug(slug: str, timeout: int) -> tuple[str, str] | None:
    page_url = f"{BASE}/indices/equity/sectoral-indices/{slug}"
    try:
        html = _fetch(page_url, timeout=timeout)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
        print(f"  SKIP slug={slug!r} page fetch failed: {e}")
        return None
    for m in CONSTITUENT_RE.finditer(html):
        return m.group(1), f"{BASE}/IndexConstituent/{m.group(1)}"
    for m in REL_CONSTITUENT_RE.finditer(html):
        return m.group(1), f"{BASE}/IndexConstituent/{m.group(1)}"
    print(f"  SKIP slug={slug!r} no IndexConstituent CSV link in HTML")
    return None


def discover_all_slugs_from_listing(timeout: int) -> list[str]:
    try:
        html = _fetch(LIST_URL, timeout=timeout)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
        print(f"Listing fetch failed ({e}), using built-in SECTORAL_SLUGS.")
        return list(SECTORAL_SLUGS)
    slugs: list[str] = []
    for m in re.finditer(
        r"/indices/equity/sectoral-indices/([a-z0-9][a-z0-9\-]*)\s*[\"\']",
        html,
        re.I,
    ):
        s = m.group(1).strip().lower()
        if s and s not in slugs:
            slugs.append(s)
    if not slugs:
        print("No slugs parsed from listing; using built-in SECTORAL_SLUGS.")
        return list(SECTORAL_SLUGS)
    return slugs


def download_csv(url: str, dest: Path, timeout: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; RS_PROJECT/constituent-fetch)",
            "Accept": "text/csv,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f"  Wrote {dest.name} ({len(data)} bytes)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch Nifty sectoral constituent CSVs.")
    ap.add_argument("--dry-run", action="store_true", help="Print URLs only; do not download.")
    ap.add_argument("--timeout", type=int, default=45, help="HTTP timeout seconds (default 45).")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: stock_scanner_sovereign/data/nifty_sectoral).",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = args.out_dir or (root / "data" / "nifty_sectoral")

    slugs = discover_all_slugs_from_listing(args.timeout)
    seen_files: set[str] = set()
    print(f"Output: {out_dir}\nDiscovering {len(slugs)} sector index pages…")

    for slug in slugs:
        found = discover_csv_for_slug(slug, args.timeout)
        if not found:
            continue
        fname, csv_url = found
        if fname in seen_files:
            continue
        seen_files.add(fname)
        dest = out_dir / fname
        print(f"{slug}: {csv_url}")
        if args.dry_run:
            continue
        try:
            download_csv(csv_url, dest, args.timeout)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            print(f"  ERROR download {fname}: {e}")

    if args.dry_run:
        print("\nDry run — no files written.")


if __name__ == "__main__":
    main()
