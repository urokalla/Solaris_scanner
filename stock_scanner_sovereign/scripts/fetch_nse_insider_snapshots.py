#!/usr/bin/env python3
"""
Fetch NSE insider snapshots and write CSVs used by Insider page:
  - data/nse_pit_disclosures.csv
  - data/nse_sast_reg29.csv
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

NSE_HOME = "https://www.nseindia.com"
URL_PIT = f"{NSE_HOME}/api/corporates-pit"
URL_SAST29 = f"{NSE_HOME}/api/corporate-sast-reg29"

PIT_COLS = [
    "symbol",
    "raw_company",
    "raw_acqName",
    "raw_personCategory",
    "txn_type",
    "raw_buyQuantity",
    "raw_sellquantity",
    "raw_buyValue",
    "raw_sellValue",
    "raw_secVal",
    "raw_secAcq",
    "raw_date",
    "first_seen_utc",
    "last_refreshed_utc",
    "fetched_at_utc",
    "is_new",
]

SAST_COLS = [
    "symbol",
    "raw_company",
    "raw_acquirerName",
    "raw_promoterType",
    "txn_type",
    "raw_noOfShareAcq",
    "raw_noOfShareSale",
    "raw_timestamp",
    "first_seen_utc",
    "last_refreshed_utc",
    "fetched_at_utc",
    "is_new",
]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{NSE_HOME}/companies-listing/corporate-filings-insider-trading",
        }
    )
    s.get(NSE_HOME, timeout=20)
    return s


def _rows_from_payload(payload: Any) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return [x for x in payload["data"] if isinstance(x, dict)]
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


def _write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def _read_existing_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _pit_key(r: dict) -> tuple[str, str, str]:
    return (
        str(r.get("symbol") or "").strip().upper(),
        str(r.get("raw_date") or r.get("date") or "").strip(),
        str(r.get("raw_acqName") or r.get("acqName") or "").strip(),
    )


def _sast_key(r: dict) -> tuple[str, str, str]:
    return (
        str(r.get("symbol") or "").strip().upper(),
        str(r.get("raw_timestamp") or r.get("timestamp") or "").strip(),
        str(r.get("raw_acquirerName") or r.get("acquirerName") or "").strip(),
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    pit_out = data_dir / "nse_pit_disclosures.csv"
    sast_out = data_dir / "nse_sast_reg29.csv"
    fetched_at_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    s = _session()
    pit_raw = _rows_from_payload(s.get(URL_PIT, timeout=30).json())
    sast_raw = _rows_from_payload(s.get(URL_SAST29, timeout=30).json())

    existing_pit = _read_existing_rows(pit_out)
    existing_sast = _read_existing_rows(sast_out)
    pit_seen = {_pit_key(r): str(r.get("first_seen_utc") or r.get("fetched_at_utc") or "").strip() for r in existing_pit}
    sast_seen = {_sast_key(r): str(r.get("first_seen_utc") or r.get("fetched_at_utc") or "").strip() for r in existing_sast}

    prev_pit_keys = {_pit_key(r) for r in existing_pit}
    prev_sast_keys = {_sast_key(r) for r in existing_sast}

    pit_rows = []
    for d in pit_raw:
        if not str(d.get("symbol") or "").strip():
            continue
        k = (
            str(d.get("symbol") or "").strip().upper(),
            str(d.get("date") or "").strip(),
            str(d.get("acqName") or "").strip(),
        )
        pit_rows.append(
            {
            "symbol": str(d.get("symbol") or "").strip().upper(),
            "raw_company": d.get("company") or "",
            "raw_acqName": d.get("acqName") or "",
            "raw_personCategory": d.get("personCategory") or "",
            "txn_type": d.get("tdpTransactionType") or "",
            "raw_buyQuantity": d.get("buyQuantity") or "",
            "raw_sellquantity": d.get("sellquantity") or "",
            "raw_buyValue": d.get("buyValue") or "",
            "raw_sellValue": d.get("sellValue") or "",
            "raw_secVal": d.get("secVal") or "",
            "raw_secAcq": d.get("secAcq") or "",
            "raw_date": d.get("date") or "",
            "first_seen_utc": pit_seen.get(
                k,
                fetched_at_utc,
            ),
            "last_refreshed_utc": fetched_at_utc,
            "fetched_at_utc": fetched_at_utc,
            "is_new": "1" if k not in prev_pit_keys else "0",
        }
        )

    sast_rows = []
    for d in sast_raw:
        if not str(d.get("symbol") or "").strip():
            continue
        k = (
            str(d.get("symbol") or "").strip().upper(),
            str(d.get("timestamp") or "").strip(),
            str(d.get("acquirerName") or "").strip(),
        )
        sast_rows.append(
            {
            "symbol": str(d.get("symbol") or "").strip().upper(),
            "raw_company": d.get("company") or "",
            "raw_acquirerName": d.get("acquirerName") or "",
            "raw_promoterType": d.get("promoterType") or "",
            "txn_type": d.get("acqSaleType") or "",
            "raw_noOfShareAcq": d.get("noOfShareAcq") if d.get("noOfShareAcq") is not None else "",
            "raw_noOfShareSale": d.get("noOfShareSale") if d.get("noOfShareSale") is not None else "",
            "raw_timestamp": d.get("timestamp") or "",
            "first_seen_utc": sast_seen.get(
                k,
                fetched_at_utc,
            ),
            "last_refreshed_utc": fetched_at_utc,
            "fetched_at_utc": fetched_at_utc,
            "is_new": "1" if k not in prev_sast_keys else "0",
        }
        )

    _write_csv(pit_out, PIT_COLS, pit_rows)
    _write_csv(sast_out, SAST_COLS, sast_rows)

    print(f"Wrote PIT={len(pit_rows)} rows -> {pit_out}")
    print(f"Wrote SAST={len(sast_rows)} rows -> {sast_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

