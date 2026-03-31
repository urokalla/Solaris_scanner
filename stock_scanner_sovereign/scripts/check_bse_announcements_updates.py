#!/usr/bin/env python3
"""
Check whether latest BSE corporate announcement changed per scrip.

This is a lightweight monitor:
- does NOT download PDF/content
- only checks latest NEWSID/headline/datetime
- maps each scrip to its BSE corp-announcements page URL
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import requests

API_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"


def _today_range(days_back: int = 95) -> tuple[str, str]:
    today = dt.date.today()
    frm = today - dt.timedelta(days=days_back)
    return frm.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def _normalize_quote_url(url: str, scrip: str) -> str:
    u = (url or "").strip()
    if not u:
        return f"https://www.bseindia.com/stock-share-price/-/-/{scrip}/corp-announcements/"
    if not u.endswith("/"):
        u += "/"
    if "corp-announcements" not in u:
        u += "corp-announcements/"
    return u


def fetch_latest_announcement(scrip: str) -> dict[str, Any]:
    frm, to = _today_range()
    params = {
        "strScrip": scrip,
        "strCat": "-1",
        "strPrevDate": frm,
        "strToDate": to,
        "strSearch": "A",
        "strType": "C",
        "pageno": "1",
        "subcategory": "-1",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://www.bseindia.com/stock-share-price/-/-/{scrip}/corp-announcements/",
    }
    r = requests.get(API_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("Table") or []
    if not rows:
        return {
            "scrip": scrip,
            "news_id": None,
            "news_dt": None,
            "headline": None,
            "category": None,
            "attachment_name": None,
            "quote_url": _normalize_quote_url("", scrip),
        }
    row = rows[0]
    quote_url = _normalize_quote_url(str(row.get("NSURL") or ""), scrip)
    return {
        "scrip": scrip,
        "news_id": str(row.get("NEWSID") or ""),
        "news_dt": str(row.get("NEWS_DT") or ""),
        "headline": str(row.get("HEADLINE") or ""),
        "category": str(row.get("CATEGORYNAME") or ""),
        "attachment_name": str(row.get("ATTACHMENTNAME") or ""),
        "quote_url": quote_url,
    }


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Check if latest BSE announcement changed per scrip.")
    ap.add_argument(
        "--scripcodes",
        required=True,
        help='Comma-separated BSE scrip codes, e.g. "500325,500378"',
    )
    ap.add_argument(
        "--state-file",
        default="data/bse_announcements_state.json",
        help="JSON file to persist last seen NEWSID per scrip.",
    )
    ap.add_argument(
        "--out-json",
        default="",
        help="Optional output JSON path for this run.",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    state_path = (repo_root / args.state_file).resolve()
    state = _load_state(state_path)
    prev_ids = state.get("last_newsid_by_scrip", {}) if isinstance(state, dict) else {}

    codes = [c.strip() for c in args.scripcodes.split(",") if c.strip()]
    results: list[dict[str, Any]] = []
    next_ids: dict[str, str] = {}

    for scrip in codes:
        latest = fetch_latest_announcement(scrip)
        prev = str(prev_ids.get(scrip) or "")
        cur = str(latest.get("news_id") or "")
        latest["new_announcement"] = bool(cur) and cur != prev
        results.append(latest)
        if cur:
            next_ids[scrip] = cur

    # Save state for next run
    now_utc = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
    state_obj = {
        "updated_at": now_utc,
        "last_newsid_by_scrip": {**prev_ids, **next_ids},
    }
    _save_state(state_path, state_obj)

    out = {
        "checked_at": now_utc,
        "count": len(results),
        "results": results,
        "state_file": str(state_path),
    }

    if args.out_json.strip():
        out_path = (repo_root / args.out_json).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

