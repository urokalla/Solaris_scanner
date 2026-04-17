#!/usr/bin/env python3
"""
After fetch_nse_corporate_announcements.py runs, summarize new PDF attachments once each.

- Downloads PDF via same NSE session pattern as fetch_nse_corporate_announcements.py
- Extracts text with PyMuPDF
- Writes extractive summary (no external LLM) into a JSON sidecar so the CSV can keep being overwritten

Cache: ``<same folder as CSV>/nse_corporate_announcement_summaries.json`` (override with ``--cache``).

  python3 scripts/nse_announcement_summarize.py --max-new 10 --sleep-sec 0.5
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

NSE_HOME = "https://www.nseindia.com"
DEFAULT_CSV = "data/nse_corporate_announcements.csv"
# Default: JSON is written next to the CSV (same dir the dashboard reads).
MAX_PDF_BYTES = 18 * 1024 * 1024


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def row_key(symbol: str, an_dt: str, url: str) -> str:
    raw = f"{(symbol or '').strip().upper()}|{(an_dt or '').strip()}|{(url or '').strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _looks_like_pdf_url(url: str) -> bool:
    u = (url or "").strip().split("?", 1)[0].lower()
    return u.endswith(".pdf")


def _nse_session(timeout: int) -> requests.Session:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{NSE_HOME}/companies-listing/corporate-filings-announcements",
    }
    s = requests.Session()
    s.headers.update(headers)
    s.get(NSE_HOME, timeout=timeout)
    return s


def _pdf_text(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise RuntimeError("Install pymupdf: pip install pymupdf") from e
    doc = fitz.open(stream=data, filetype="pdf")
    parts: list[str] = []
    try:
        for i in range(min(doc.page_count, 40)):
            parts.append(doc.load_page(i).get_text("text") or "")
    finally:
        doc.close()
    return "\n".join(parts)


_WS = re.compile(r"\s+")


def _clean_text(t: str) -> str:
    t = _WS.sub(" ", (t or "").replace("\x00", "")).strip()
    return t


def _extractive_summary(text: str, desc: str, max_chars: int = 420) -> str:
    body = _clean_text(text)
    if not body:
        d = _clean_text(desc)
        return (d + " — PDF had no extractable text.") if d else "PDF had no extractable text."

    # Prefer first sentences from body; fall back to prefix.
    sentences = re.split(r"(?<=[.!?])\s+", body)
    out: list[str] = []
    n = 0
    for s in sentences:
        s = _clean_text(s)
        if not s:
            continue
        if n + len(s) + 1 > max_chars:
            break
        out.append(s)
        n += len(s) + 1
        if n >= max_chars * 0.85:
            break
    joined = " ".join(out).strip()
    if len(joined) < 40:
        joined = body[:max_chars]
    if len(joined) > max_chars:
        joined = joined[: max_chars - 1].rstrip() + "…"
    return joined


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            lk = {str(k or "").strip().lower(): v for k, v in row.items()}
            rows.append(
                {
                    "symbol": str(lk.get("symbol") or "").strip().upper(),
                    "desc": str(lk.get("desc") or ""),
                    "an_dt": str(lk.get("an_dt") or ""),
                    "attchmntFile": str(lk.get("attchmntfile") or lk.get("attchmnt_file") or "").strip(),
                }
            )
    return rows


def _load_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default=DEFAULT_CSV, help="Relative to stock_scanner_sovereign")
    p.add_argument(
        "--cache",
        default="",
        help="Summaries JSON path relative to stock_scanner_sovereign (default: same folder as --csv)",
    )
    p.add_argument("--max-new", type=int, default=10, help="Max new PDFs to process this run")
    p.add_argument("--sleep-sec", type=float, default=0.35, help="Pause between downloads")
    p.add_argument("--timeout", type=int, default=45)
    args = p.parse_args()

    repo = _repo_root()
    csv_path = (repo / args.csv).resolve()
    if (args.cache or "").strip():
        cache_path = (repo / args.cache.strip()).resolve()
    else:
        cache_path = (csv_path.parent / "nse_corporate_announcement_summaries.json").resolve()
    if not csv_path.exists():
        print(f"skip: csv missing {csv_path}", file=sys.stderr)
        return 0

    cache = _load_cache(cache_path)
    rows = _read_csv_rows(csv_path)
    session = _nse_session(args.timeout)
    done = 0
    for r in rows:
        if done >= max(0, int(args.max_new)):
            break
        url = r["attchmntFile"]
        if not url or not _looks_like_pdf_url(url):
            continue
        k = row_key(r["symbol"], r["an_dt"], url)
        if k in cache and isinstance(cache[k], dict) and str(cache[k].get("summary") or "").strip():
            continue
        try:
            resp = session.get(
                url,
                timeout=args.timeout,
                stream=True,
                headers={"Referer": f"{NSE_HOME}/"},
            )
            resp.raise_for_status()
            clen = resp.headers.get("Content-Length")
            if clen and clen.isdigit() and int(clen) > MAX_PDF_BYTES:
                cache[k] = {
                    "symbol": r["symbol"],
                    "an_dt": r["an_dt"],
                    "url": url,
                    "summary": f"Skipped large PDF ({clen} bytes). Open link to read.",
                }
                _write_cache(cache_path, cache)
                done += 1
                time.sleep(args.sleep_sec)
                continue
            buf = bytearray()
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                buf.extend(chunk)
                if len(buf) > MAX_PDF_BYTES:
                    break
            data = bytes(buf)
            if len(data) > MAX_PDF_BYTES:
                cache[k] = {
                    "symbol": r["symbol"],
                    "an_dt": r["an_dt"],
                    "url": url,
                    "summary": "PDF too large to auto-summarize here; use open link.",
                }
            else:
                text = _pdf_text(data)
                cache[k] = {
                    "symbol": r["symbol"],
                    "an_dt": r["an_dt"],
                    "url": url,
                    "summary": _extractive_summary(text, r["desc"]),
                }
            _write_cache(cache_path, cache)
            done += 1
            print(f"summarized {done}: {r['symbol']} {r['an_dt']}")
        except Exception as e:
            cache[k] = {
                "symbol": r["symbol"],
                "an_dt": r["an_dt"],
                "url": url,
                "summary": f"Summary failed: {e}",
            }
            _write_cache(cache_path, cache)
            done += 1
            print(f"fail {r['symbol']}: {e}", file=sys.stderr)
        time.sleep(max(0.0, float(args.sleep_sec)))

    print(f"nse_announcement_summarize: processed {done} new/changed rows, cache {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
