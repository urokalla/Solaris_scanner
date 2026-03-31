#!/usr/bin/env python3
"""
Fetch latest Screener concall links for a company.

What it does:
- Pulls https://www.screener.in/company/<SYMBOL>/consolidated/
- Parses the "Concalls" section
- Returns latest month + transcript/PPT/REC links as JSON
- Optionally downloads the latest transcript PDF
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import requests


SCREENER_URL_TMPL = "https://www.screener.in/company/{symbol}/consolidated/"


@dataclass
class ConcallRow:
    month_label: str
    transcript_url: Optional[str]
    ppt_url: Optional[str]
    rec_url: Optional[str]
    ai_summary_path: Optional[str]


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract_concalls_section(html: str) -> str:
    m = re.search(r"<h3[^>]*>\s*Concalls\s*</h3>(.*?)</section>", html, re.I | re.S)
    if not m:
        raise ValueError("Could not locate Concalls section in Screener HTML.")
    return m.group(1)


def _extract_latest_row(sec: str) -> ConcallRow:
    li_m = re.search(r"<li[^>]*>(.*?)</li>", sec, re.I | re.S)
    if not li_m:
        raise ValueError("No concall rows found in Concalls section.")
    li = li_m.group(1)

    month_m = re.search(
        r'<div[^>]*style="width:\s*74px"[^>]*>(.*?)</div>', li, re.I | re.S
    )
    month_label = _clean(month_m.group(1)) if month_m else "Unknown"

    def _href_for_anchor_text(text: str) -> Optional[str]:
        m = re.search(
            rf'<a[^>]+href="([^"]+)"[^>]*>\s*{re.escape(text)}\s*</a>',
            li,
            re.I | re.S,
        )
        return _clean(m.group(1)) if m else None

    transcript_url = _href_for_anchor_text("Transcript")
    ppt_url = _href_for_anchor_text("PPT")
    rec_url = _href_for_anchor_text("REC")

    ai_m = re.search(
        r'<button[^>]+data-url="([^"]+)"[^>]*>\s*AI Summary\s*</button>',
        li,
        re.I | re.S,
    )
    ai_summary_path = _clean(ai_m.group(1)) if ai_m else None

    return ConcallRow(
        month_label=month_label,
        transcript_url=transcript_url,
        ppt_url=ppt_url,
        rec_url=rec_url,
        ai_summary_path=ai_summary_path,
    )


def _download_file(url: str, out_path: Path, timeout_s: int, referer: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": referer,
        "Accept": "application/pdf,application/octet-stream,*/*",
    }
    with requests.get(url, timeout=timeout_s, stream=True, headers=headers) as r:
        r.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch latest Screener concall links for one symbol.")
    ap.add_argument("--symbol", required=True, help="Screener symbol slug, e.g. JINDALSAW, RELIANCE")
    ap.add_argument(
        "--download-transcript",
        action="store_true",
        help="Download latest transcript PDF if transcript URL exists.",
    )
    ap.add_argument(
        "--download-dir",
        default="data/concall_transcripts",
        help="Relative output directory for downloaded transcript PDFs.",
    )
    ap.add_argument(
        "--out-json",
        default="",
        help="Optional JSON output path (relative to repo root).",
    )
    ap.add_argument("--timeout-s", type=int, default=25)
    args = ap.parse_args()

    sym = args.symbol.strip().upper()
    url = SCREENER_URL_TMPL.format(symbol=sym)
    repo_root = Path(__file__).resolve().parents[2]

    r = requests.get(
        url,
        timeout=args.timeout_s,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        },
    )
    r.raise_for_status()
    html = r.text

    sec = _extract_concalls_section(html)
    latest = _extract_latest_row(sec)

    payload = {
        "symbol": sym,
        "screener_url": url,
        "latest_concall": asdict(latest),
        "downloaded_transcript_path": None,
    }

    if args.download_transcript and latest.transcript_url:
        out_name = f"{sym}_{latest.month_label.replace(' ', '_')}_transcript.pdf"
        out_path = (repo_root / args.download_dir / out_name).resolve()
        _download_file(latest.transcript_url, out_path, args.timeout_s, referer=url)
        payload["downloaded_transcript_path"] = str(out_path)

    out_json = args.out_json.strip()
    if out_json:
        out_path = (repo_root / out_json).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

