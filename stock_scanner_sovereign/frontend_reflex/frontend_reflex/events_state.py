import asyncio
import csv
import datetime as dt
from pathlib import Path

import reflex as rx

# Module-level cache only — Reflex background tasks must not assign to State
# attributes outside `async with self`; caching on self trips StateProxy errors.
_NIFTY500_CSV_KEY: str = ""
_NIFTY500_SYMBOLS: frozenset[str] = frozenset()


def _parse_event_dt(s: str) -> dt.datetime:
    x = (s or "").strip()
    if not x:
        return dt.datetime.min
    for fmt in (
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M",
        "%d-%b-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return dt.datetime.strptime(x, fmt)
        except ValueError:
            pass
    return dt.datetime.min


def _load_nifty500_symbols() -> frozenset[str]:
    global _NIFTY500_CSV_KEY, _NIFTY500_SYMBOLS
    root = Path(__file__).resolve().parents[3]
    candidates = [
        (root / "data" / "nifty500.csv").resolve(),
        (root / "stock_scanner_sovereign" / "data" / "nifty500.csv").resolve(),
    ]
    for csv_path in candidates:
        key = str(csv_path)
        if key == _NIFTY500_CSV_KEY and _NIFTY500_SYMBOLS:
            return _NIFTY500_SYMBOLS
        if csv_path.exists():
            syms: set[str] = set()
            with csv_path.open("r", encoding="utf-8-sig") as f:
                r = csv.DictReader(f)
                for row in r:
                    s = str(row.get("Symbol") or "").strip().upper()
                    if s:
                        syms.add(s)
            _NIFTY500_CSV_KEY = key
            _NIFTY500_SYMBOLS = frozenset(syms)
            return _NIFTY500_SYMBOLS
    _NIFTY500_CSV_KEY = ""
    _NIFTY500_SYMBOLS = frozenset()
    return _NIFTY500_SYMBOLS


def _data_roots_for_snapshots() -> list[Path]:
    root = Path(__file__).resolve()
    return [root.parents[3] / "data", root.parents[2] / "data"]


def _find_nse_corporate_announcements_csv() -> Path | None:
    for base in _data_roots_for_snapshots():
        p = (base / "nse_corporate_announcements.csv").resolve()
        if p.exists():
            return p
    return None


def _lower_key_row(row: dict) -> dict:
    return {str(k or "").strip().lower(): v for k, v in row.items()}


class EventsState(rx.State):
    rows: list[dict] = []
    total_count: int = 0
    status_message: str = "Initializing..."
    last_sync: str = "-"
    search_query: str = ""

    def set_search_query(self, q: str):
        self.search_query = q or ""

    @rx.var
    def filtered_rows(self) -> list[dict]:
        q = (self.search_query or "").strip().upper()
        if not q:
            return self.rows
        return [
            r
            for r in self.rows
            if q in str(r.get("symbol", "")).upper() or q in str(r.get("desc", "")).upper()
        ]

    @rx.var
    def filtered_count(self) -> int:
        return len(self.filtered_rows)

    def on_load(self):
        return [EventsState.apply_url_symbol_filter, EventsState.poll_events]

    def apply_url_symbol_filter(self):
        """
        If /events is opened with ?symbol=XXX, prefill the search box so the row is immediately visible.
        Safe no-op when router/query params are unavailable.
        """
        try:
            router = getattr(self, "router", None)
            page = getattr(router, "page", None) if router is not None else None
            params = getattr(page, "params", {}) if page is not None else {}
            if not isinstance(params, dict):
                return
            raw = str(params.get("symbol") or "").strip().upper()
            if raw:
                self.search_query = raw
        except Exception:
            return

    def _tag(self, desc: str) -> tuple[str, str]:
        d = (desc or "").lower()
        # Compliance / administrative announcements are informational, not momentum triggers.
        compliance = (
            "trading window",
            "window closure",
            "board meeting",
            "intimation",
            "record date",
            "closure of trading window",
            "shareholders meeting",
            "loss of share certificates",
        )
        risky = ("penalty", "litigation", "auditor", "resign", "fraud", "default", "pledge")
        good = ("order", "win", "commission", "approval", "capacity", "expansion", "allotment")
        neutral = ("update", "disclosure", "notice")
        if any(k in d for k in compliance):
            return "NEUTRAL", "#B0BEC5"
        if any(k in d for k in risky):
            return "RISKY", "#FF4D4D"
        if any(k in d for k in good):
            return "GOOD", "#00E676"
        if any(k in d for k in neutral):
            return "NEUTRAL", "#B0BEC5"
        return "NEUTRAL", "#B0BEC5"

    def _load_announcements_snapshot(self) -> list[dict]:
        """
        Read data/nse_corporate_announcements.csv only (no NSE from the running app).
        Refresh the file with scripts/fetch_nse_corporate_announcements.py or your own job.
        """
        path = _find_nse_corporate_announcements_csv()
        if path is None:
            raise FileNotFoundError(
                "nse_corporate_announcements.csv not found under data/ — "
                "run stock_scanner_sovereign/scripts/fetch_nse_corporate_announcements.py"
            )
        raw: list[dict] = []
        with path.open("r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                lk = _lower_key_row(dict(row))
                raw.append(
                    {
                        "symbol": str(lk.get("symbol") or "").strip().upper(),
                        "desc": str(lk.get("desc") or ""),
                        "an_dt": str(lk.get("an_dt") or ""),
                        "attchmntFile": str(lk.get("attchmntfile") or lk.get("attchmnt_file") or ""),
                    }
                )
        return raw

    @rx.event(background=True)
    async def poll_events(self):
        while True:
            try:
                n500 = _load_nifty500_symbols()
                if not n500:
                    async with self:
                        self.rows = []
                        self.total_count = 0
                        self.last_sync = dt.datetime.now(dt.UTC).strftime("%H:%M:%S UTC")
                        self.status_message = "⚠️ nifty500.csv not found"
                    await asyncio.sleep(180)
                    continue
                raw = self._load_announcements_snapshot()
                rows: list[dict] = []
                for x in raw:
                    sym = str(x.get("symbol") or "").upper()
                    if not sym or sym not in n500:
                        continue
                    tag, color = self._tag(str(x.get("desc") or ""))
                    rows.append(
                        {
                            "symbol": sym,
                            "desc": str(x.get("desc") or ""),
                            "an_dt": str(x.get("an_dt") or ""),
                            "attchmntFile": str(x.get("attchmntFile") or ""),
                            "tag": tag,
                            "tag_color": color,
                        }
                    )
                rows.sort(key=lambda r: _parse_event_dt(str(r.get("an_dt") or "")), reverse=True)
                async with self:
                    self.rows = rows
                    self.total_count = len(rows)
                    self.last_sync = dt.datetime.now(dt.UTC).strftime("%H:%M:%S UTC")
                    self.status_message = "✅ Active (snapshot)"
            except Exception as e:
                async with self:
                    self.status_message = f"⚠️ {e}"
            await asyncio.sleep(180)

