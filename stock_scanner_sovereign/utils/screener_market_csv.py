"""
Fetch Screener.in **market** constituent tables (Browse sectors) into CSV files.

Each sector uses a stable filename: last path segment, e.g. ``IN110101.csv`` for Power.
Registry: ``data/screener_market/sector_index.json`` (labels + paths + codes).
"""
from __future__ import annotations

import csv
import html as html_mod
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1]
MARKET_DIR = _PKG / "data" / "screener_market"
SECTOR_INDEX = _PKG / "data" / "screener_market" / "sector_index.json"
EXPLORE_URL = "https://www.screener.in/explore/"

COMPANY_LINK_RE = re.compile(
    r'href="(/company/([^/"]+)/(?:consolidated/)?)"[^>]*>([^<]+)</a>',
    re.I,
)
SECTOR_LINK_RE = re.compile(
    r'<a\s[\s\S]*?href="(/market/(?:IN\d+/){2}IN\d+/)"[\s\S]*?>([^<]+)</a>',
    re.I,
)


def market_https_url(path_or_url: str) -> str:
    s = (path_or_url or "").strip()
    if s.startswith("http"):
        return s.rstrip("/") + "/"
    return "https://www.screener.in" + s.rstrip("/") + "/"


def _fetch(u: str, timeout: int, retries: int = 4) -> str:
    ctx = ssl.create_default_context()
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            u,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RS_PROJECT/sector-fetch)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and attempt + 1 < retries:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
        except Exception as e:
            last_err = e
            raise
    raise last_err  # type: ignore[misc]


def _max_page(html: str) -> int:
    m = re.search(r"page (\d+) of (\d+)", html, re.I)
    if m:
        return int(m.group(2))
    return 1


def parse_company_rows(html: str, page: int) -> list[tuple[str, str, int]]:
    rows: list[tuple[str, str, int]] = []
    for m in COMPANY_LINK_RE.finditer(html):
        slug = html_mod.unescape(m.group(2)).strip()
        name = html_mod.unescape(m.group(3)).strip()
        name = re.sub(r"\s+", " ", name)
        if not slug or not name:
            continue
        rows.append((slug, name, page))
    seen: set[tuple[str, int]] = set()
    out: list[tuple[str, str, int]] = []
    for slug, name, p in rows:
        key = (slug, p)
        if key in seen:
            continue
        seen.add(key)
        out.append((slug, name, p))
    return out


def download_market_sector_csv(*, market_path: str, out_csv: Path, timeout: int = 45) -> int:
    """Download one market listing to CSV. ``market_path`` like ``/market/IN11/IN1101/IN110101/``."""
    base = market_https_url(market_path)
    first = _fetch(base, timeout)
    np = max(1, _max_page(first))
    all_rows: list[tuple[str, str, int]] = parse_company_rows(first, 1)
    for p in range(2, np + 1):
        h = _fetch(f"{base}?page={p}", timeout)
        all_rows.extend(parse_company_rows(h, p))

    by_slug: dict[str, tuple[str, str, int]] = {}
    for slug, name, page in all_rows:
        if slug not in by_slug:
            by_slug[slug] = (slug, name, page)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "company_name", "page"])
        for slug, name, page in sorted(by_slug.values(), key=lambda x: x[0]):
            w.writerow([slug, name, page])
    return len(by_slug)


def discover_browse_sectors_from_explore(timeout: int = 45) -> list[dict[str, str]]:
    """Return sorted list of ``{label, market_path, code}`` from Explore sidebar."""
    raw = _fetch(EXPLORE_URL, timeout)
    start = raw.find("Browse sectors")
    chunk = raw[start : start + 150_000] if start >= 0 else raw
    seen: dict[str, str] = {}
    for m in SECTOR_LINK_RE.finditer(chunk):
        path, label = m.group(1), html_mod.unescape(re.sub(r"\s+", " ", m.group(2)).strip())
        seen[path] = label
    out: list[dict[str, str]] = []
    for path, label in seen.items():
        code = path.rstrip("/").rsplit("/", 1)[-1]
        out.append({"label": label, "market_path": path, "code": code})
    out.sort(key=lambda x: x["label"].lower())
    return out


def write_sector_index(sectors: list[dict[str, str]], path: Path | None = None) -> None:
    p = path or SECTOR_INDEX
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": EXPLORE_URL, "sectors": sectors}
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_sector_index(path: Path | None = None) -> list[dict[str, str]]:
    p = path or SECTOR_INDEX
    if not p.is_file():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("sectors") or [])
