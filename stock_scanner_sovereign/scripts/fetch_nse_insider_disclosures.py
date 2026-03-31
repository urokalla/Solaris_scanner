#!/usr/bin/env python3
"""
Fetch insider/promoter disclosure-style data and normalize to a CSV.

Why this script exists:
- Many NSE python libs focus on prices/bhavcopy; insider/promoter disclosures are separate.
- NSE endpoints change; this script supports a "generic NSE JSON API URL" mode so you can
  update the URL without rewriting parsing/plumbing.

This is best-effort and subject to NSE ToS, rate limits, and endpoint changes.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests


NSE_HOME = "https://www.nseindia.com"


@dataclass(frozen=True)
class FetchResult:
    rows: List[Dict[str, Any]]
    raw: Any


def _nse_session(user_agent: str, timeout_s: int) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Referer": NSE_HOME + "/",
        }
    )
    # Warm up cookies. NSE APIs often require a valid cookie jar.
    s.get(NSE_HOME, timeout=timeout_s)
    return s


def _try_nselib() -> Optional[FetchResult]:
    """
    Attempt to fetch via nselib if the installed version exposes an appropriate API.
    We keep this intentionally permissive because nselib's surface can change.
    """
    try:
        from nselib import capital_market  # type: ignore
    except Exception:
        return None

    candidates = [
        # naming variants seen in similar libs
        "insider_trading",
        "corporate_pit",
        "pit_disclosures",
        "insider_disclosures",
        "promoter_trades",
    ]

    for name in candidates:
        fn = getattr(capital_market, name, None)
        if callable(fn):
            try:
                df = fn()
                if df is None:
                    continue
                if hasattr(df, "to_dict"):
                    rows = df.to_dict("records")  # type: ignore[no-any-return]
                    return FetchResult(rows=rows, raw=df)
            except Exception:
                continue

    return None


def fetch_from_nse_api_url(
    api_url: str,
    *,
    user_agent: str,
    timeout_s: int,
    pause_s: float,
    params: Optional[Dict[str, Any]] = None,
) -> FetchResult:
    s = _nse_session(user_agent=user_agent, timeout_s=timeout_s)
    time.sleep(max(pause_s, 0.0))
    r = s.get(api_url, params=params or {}, timeout=timeout_s)
    r.raise_for_status()
    raw = r.json()

    if isinstance(raw, dict):
        # Common patterns: {"data":[...]} or {"rows":[...]} or {"items":[...]}
        for k in ("data", "rows", "items", "result", "payload"):
            v = raw.get(k)
            if isinstance(v, list):
                return FetchResult(rows=[x for x in v if isinstance(x, dict)], raw=raw)
        # Sometimes it's a dict per row; normalize.
        return FetchResult(rows=[raw], raw=raw)

    if isinstance(raw, list):
        return FetchResult(rows=[x for x in raw if isinstance(x, dict)], raw=raw)

    return FetchResult(rows=[], raw=raw)


def normalize_rows(rows: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """
    Normalize arbitrary disclosure rows into a consistent flat table.
    We keep all original fields (prefixed with raw_) and derive best-effort standard ones.
    """
    rows = list(rows)
    if not rows:
        return pd.DataFrame(
            columns=[
                "symbol",
                "disclosure_date",
                "txn_type",
                "qty",
                "value",
                "person_category",
                "person_name",
                "raw_json",
            ]
        )

    df = pd.json_normalize(rows, sep=".")
    df.columns = [str(c) for c in df.columns]

    # Keep a compact raw snapshot per row for traceability.
    df["raw_json"] = [json.dumps(r, ensure_ascii=False, default=str) for r in rows]

    def pick_first(col_candidates: List[str]) -> Optional[str]:
        for c in col_candidates:
            if c in df.columns:
                return c
        return None

    # Symbol / company
    symbol_col = pick_first(
        ["symbol", "SYMBOL", "secSymbol", "sec_symbol", "securitySymbol", "securitySymbolName"]
    )
    if symbol_col:
        df["symbol"] = df[symbol_col].astype(str).str.strip()
    else:
        df["symbol"] = ""

    # Date fields (best-effort)
    date_col = pick_first(
        ["disclosureDate", "disclosure_date", "date", "txnDate", "transactionDate", "reportingDate"]
    )
    if date_col:
        df["disclosure_date"] = pd.to_datetime(df[date_col], errors="coerce").dt.date
    else:
        df["disclosure_date"] = pd.NaT

    # Buy/Sell
    txn_col = pick_first(["txnType", "txn_type", "transactionType", "buySell", "acqDisposal", "mode"])
    if txn_col:
        df["txn_type"] = df[txn_col].astype(str).str.strip()
    else:
        df["txn_type"] = ""

    # Quantity / Value
    qty_col = pick_first(["quantity", "qty", "noOfShares", "shares", "securityQty", "txnQty"])
    if qty_col:
        df["qty"] = pd.to_numeric(df[qty_col], errors="coerce")
    else:
        df["qty"] = pd.NA

    val_col = pick_first(["value", "txnValue", "consideration", "amount", "tradeValue"])
    if val_col:
        df["value"] = pd.to_numeric(df[val_col], errors="coerce")
    else:
        df["value"] = pd.NA

    # Person metadata
    cat_col = pick_first(["category", "personCategory", "person_category", "clientType", "designation"])
    if cat_col:
        df["person_category"] = df[cat_col].astype(str).str.strip()
    else:
        df["person_category"] = ""

    name_col = pick_first(["name", "personName", "person_name", "insiderName", "clientName"])
    if name_col:
        df["person_name"] = df[name_col].astype(str).str.strip()
    else:
        df["person_name"] = ""

    keep_cols = [
        "symbol",
        "disclosure_date",
        "txn_type",
        "qty",
        "value",
        "person_category",
        "person_name",
        "raw_json",
    ]
    # Append raw columns (prefixed) for debugging.
    raw_cols = [c for c in df.columns if c not in keep_cols]
    out = df[keep_cols + raw_cols].copy()
    out.rename(columns={c: f"raw_{c}" for c in raw_cols}, inplace=True)
    return out


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch NSE insider/promoter disclosure-style rows and export as CSV."
    )
    p.add_argument(
        "--api-url",
        default="",
        help=(
            "NSE JSON API URL to fetch from. If omitted, we try nselib best-effort. "
            "Example: 'https://www.nseindia.com/api/<endpoint>'"
        ),
    )
    p.add_argument(
        "--params-json",
        default="",
        help="Optional JSON dict of query params to pass to --api-url.",
    )
    p.add_argument(
        "--out",
        default="data/nse_insider_disclosures.csv",
        help="Output CSV path (relative to repo root).",
    )
    p.add_argument("--timeout-s", type=int, default=20, help="HTTP timeout in seconds.")
    p.add_argument(
        "--pause-s",
        type=float,
        default=0.75,
        help="Polite pause between cookie warmup and API call.",
    )
    p.add_argument(
        "--user-agent",
        default=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        help="User-Agent header for NSE.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    out_path = (repo_root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    params: Optional[Dict[str, Any]] = None
    if args.params_json.strip():
        params = json.loads(args.params_json)
        if not isinstance(params, dict):
            raise SystemExit("--params-json must be a JSON object (dict).")

    fetched: Optional[FetchResult] = None

    if args.api_url.strip():
        fetched = fetch_from_nse_api_url(
            args.api_url.strip(),
            user_agent=args.user_agent,
            timeout_s=args.timeout_s,
            pause_s=args.pause_s,
            params=params,
        )
    else:
        fetched = _try_nselib()
        if fetched is None:
            raise SystemExit(
                "No --api-url provided and nselib did not expose an insider/disclosure function. "
                "Provide --api-url for the NSE JSON endpoint you want to use."
            )

    df = normalize_rows(fetched.rows)
    df["fetched_at"] = date.today().isoformat()
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df):,} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

