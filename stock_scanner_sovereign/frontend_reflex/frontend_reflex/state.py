import json
import os
import reflex as rx, asyncio, time
from urllib.parse import quote

from .engine import get_scanner
from .state_tasks import poll_results_handler, download_excel_logic


def screener_in_url(symbol: str) -> str:
    """
    Screener.in: use ``/company/{slug}/consolidated/`` for EQ — that is their default full
    fundamental view (Market Cap, P/E, ROE, Book Value, Pros/Cons, peers, etc.). Bare
    ``/company/{slug}/`` often shows a thinner page; we cannot inject custom screen queries via URL.

    Indices: search (no single company fundamentals page). Tickers may still 404 on Screener
    vs NSE (e.g. some hyphen rules).
    """
    s = str(symbol or "").strip().upper()
    if not s:
        return "https://www.screener.in/"
    if ":" in s:
        s = s.split(":", 1)[1]
    if s.endswith("-INDEX"):
        q = s.replace("-INDEX", "").replace("_", " ").replace("-", " ").strip()
        return f"https://www.screener.in/search/?q={quote(q or 'nifty')}"
    if s.endswith("-EQ"):
        s = s[:-3]
    slug = s.replace("_", "-")
    slug_q = quote(slug, safe="-")
    base = f"https://www.screener.in/company/{slug_q}/consolidated/"
    frag = (os.getenv("SCREENER_IN_URL_FRAGMENT") or "").strip()
    if frag and not frag.startswith("#"):
        frag = "#" + frag
    return base + frag


# Main grid PROFILE tabs (ALL, ELITE, …): each remembers its own sort + filters via JSON below.
_MAIN_PROFILE_TAB_KEYS = ("ALL", "ELITE", "LEADER", "RISING", "LAGGARD", "FADING", "BASELINE")


class State(rx.State):
    scanner_results: list[dict] = []
    alpha_signals: list[dict] = []
    pulse_data: list[dict] = []
    universe: str = "Nifty 500"
    # Screener market sector slice; intersects universe in get_ui_view. Non-(All) defaults sort to W_mRS ↓.
    dashboard_sector: str = "(All)"
    benchmark_name, benchmark, status_message = "Nifty 50", "NSE:NIFTY50-INDEX", "Ready"
    result_count, current_page, page_size, total_pages = 0, 1, 50, 1
    search_query, filter_profile, filter_status, filter_mrs, filter_rv = "", "ALL", "ALL", "ALL", "ALL"
    filter_mrs_rcvr: str = "ALL"
    grid_sort_key: str = "rs_rating"
    grid_sort_desc: bool = True
    benchmark_ltp, benchmark_change, benchmark_is_up, sync_in_progress = "₹0.00", "0.00%", True, False
    # Per PROFILE tab: {"ALL": {"sort_key":..., "filter_status":...}, "ELITE": {...}}
    main_profile_prefs_json: str = "{}"

    def on_load(self):
        from utils.constants import DASHBOARD_BENCHMARK_MAP
        if self.benchmark_name not in DASHBOARD_BENCHMARK_MAP:
            self.benchmark_name = "Nifty 50"
            self.benchmark = DASHBOARD_BENCHMARK_MAP["Nifty 50"]
            get_scanner().update_params(benchmark=self.benchmark)
        if self.grid_sort_key in ("canslim_score", "cs", "canslim"):
            self.grid_sort_key = "rs_rating"
        yield State.poll_results
    def set_universe(self, u):
        # Breakout engine syncs when opening /breakout (avoid heavy reset + races from main page).
        self.universe, self.current_page = u, 1
        self.filter_mrs_rcvr = "ALL"
        get_scanner(universe=u)

    def set_dashboard_sector(self, v: str):
        self.dashboard_sector = str(v or "(All)").strip() or "(All)"
        self.current_page = 1
        # Strongest-in-sector at a glance: weekly Mansfield RS vs benchmark, high → low.
        lab = self.dashboard_sector.strip().upper()
        if lab in ("(ALL)", "ALL"):
            return
        self.grid_sort_key, self.grid_sort_desc = "mrs", True
    def set_benchmark(self, b):
        from utils.constants import DASHBOARD_BENCHMARK_MAP
        sym = DASHBOARD_BENCHMARK_MAP.get(b, DASHBOARD_BENCHMARK_MAP["Nifty 50"])
        self.benchmark_name, self.benchmark = b, sym
        get_scanner().update_params(benchmark=self.benchmark)

    def _main_profile_prefs_dict(self) -> dict:
        try:
            return json.loads(self.main_profile_prefs_json or "{}")
        except json.JSONDecodeError:
            return {}

    def _main_profile_prefs_write(self, d: dict) -> None:
        self.main_profile_prefs_json = json.dumps(d)

    def _snapshot_active_profile_tab(self) -> None:
        cur = self.filter_profile if self.filter_profile in _MAIN_PROFILE_TAB_KEYS else "ALL"
        blob = self._main_profile_prefs_dict()
        blob[cur] = {
            "sort_key": self.grid_sort_key,
            "sort_desc": self.grid_sort_desc,
            "filter_status": self.filter_status,
            "filter_mrs": self.filter_mrs,
            "filter_rv": self.filter_rv,
            "filter_mrs_rcvr": self.filter_mrs_rcvr,
            "search_query": self.search_query,
        }
        self._main_profile_prefs_write(blob)

    def set_search_query(self, q):
        self.search_query, self.current_page = q, 1

    def set_filter_profile(self, v: str):
        p = str(v or "ALL").strip().upper()
        if p not in _MAIN_PROFILE_TAB_KEYS:
            p = "ALL"
        self._snapshot_active_profile_tab()
        self.filter_profile = p
        loaded = self._main_profile_prefs_dict().get(p)
        if isinstance(loaded, dict):
            sk = str(loaded.get("sort_key", "rs_rating"))
            if sk in ("canslim_score", "cs", "canslim"):
                sk = "rs_rating"
            self.grid_sort_key = sk
            self.grid_sort_desc = bool(loaded.get("sort_desc", True))
            self.filter_status = str(loaded.get("filter_status", "ALL"))
            self.filter_mrs = str(loaded.get("filter_mrs", "ALL"))
            self.filter_rv = str(loaded.get("filter_rv", "ALL"))
            fmr = str(loaded.get("filter_mrs_rcvr", "ALL"))
            self.filter_mrs_rcvr = fmr if fmr in ("ALL", "BELOW0_RISING") else "ALL"
            self.search_query = str(loaded.get("search_query", ""))
        else:
            self.grid_sort_key = "rs_rating"
            self.grid_sort_desc = True
            self.filter_status = "ALL"
            self.filter_mrs = "ALL"
            self.filter_rv = "ALL"
            self.filter_mrs_rcvr = "ALL"
            self.search_query = ""
        self.current_page = 1

    def set_filter_status(self, v): self.filter_status, self.current_page = v, 1
    def set_filter_mrs(self, v): self.filter_mrs, self.current_page = v, 1
    def set_filter_rv(self, v): self.filter_rv, self.current_page = v, 1

    def set_filter_mrs_rcvr(self, v):
        s = (v or "ALL").strip()
        self.filter_mrs_rcvr = "ALL" if s.upper() == "ALL" else "BELOW0_RISING"
        self.current_page = 1

    def toggle_grid_sort(self, key: str):
        if self.grid_sort_key == key:
            self.grid_sort_desc = not self.grid_sort_desc
        else:
            self.grid_sort_key = key
            self.grid_sort_desc = key not in ("symbol", "status", "profile", "w_rsi2", "ad_grade")
        self.current_page = 1

    def set_grid_sort_field(self, label: str):
        """Toolbar sort column (synced with column-header sort)."""
        m = {
            "RS": "rs_rating",
            "W_mRS": "mrs",
            "RT Δ": "rs_delta",
            "Prev W_mRS": "mrs_prev_day",
            "D_mRS": "mrs_daily",
            "RVOL": "rv",
            "W_RSI2": "w_rsi2",
            "CHG%": "chg",
            "LTP": "ltp",
            "Ticker": "symbol",
            "Status": "status",
            "Profile": "profile",
            "BRK": "brk_lvl",
            "A/D": "ad_grade",
        }
        key = m.get(str(label or "").strip(), "rs_rating")
        if self.grid_sort_key == key:
            self.current_page = 1
            return
        self.grid_sort_key = key
        self.grid_sort_desc = key not in ("symbol", "status", "profile", "w_rsi2", "ad_grade")
        self.current_page = 1

    def set_grid_sort_order(self, label: str):
        s = str(label or "")
        self.grid_sort_desc = s.startswith("High")
        self.current_page = 1

    @rx.var
    def grid_sort_arrow_sym(self) -> str:
        if self.grid_sort_key != "symbol":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_rs(self) -> str:
        if self.grid_sort_key != "rs_rating":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_mrs(self) -> str:
        if self.grid_sort_key != "mrs":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_rs_delta(self) -> str:
        if self.grid_sort_key != "rs_delta":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_dmrs(self) -> str:
        if self.grid_sort_key != "mrs_daily":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_rv(self) -> str:
        if self.grid_sort_key != "rv":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_w_rsi2(self) -> str:
        if self.grid_sort_key != "w_rsi2":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_chg(self) -> str:
        if self.grid_sort_key != "chg":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_ltp(self) -> str:
        if self.grid_sort_key != "ltp":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_prev_day(self) -> str:
        if self.grid_sort_key != "mrs_prev_day":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_brk(self) -> str:
        if self.grid_sort_key != "brk_lvl":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_ad(self) -> str:
        if self.grid_sort_key != "ad_grade":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_profile(self) -> str:
        if self.grid_sort_key != "profile":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_arrow_status(self) -> str:
        if self.grid_sort_key != "status":
            return ""
        return "▼" if self.grid_sort_desc else "▲"

    @rx.var
    def grid_sort_field_select_label(self) -> str:
        rev = {
            "rs_rating": "RS",
            "mrs": "W_mRS",
            "rs_delta": "RT Δ",
            "mrs_prev_day": "Prev W_mRS",
            "mrs_daily": "D_mRS",
            "rv": "RVOL",
            "w_rsi2": "W_RSI2",
            "chg": "CHG%",
            "ltp": "LTP",
            "symbol": "Ticker",
            "status": "Status",
            "profile": "Profile",
            "brk_lvl": "BRK",
            "ad_grade": "A/D",
        }
        return rev.get(self.grid_sort_key, "RS")

    @rx.var
    def grid_sort_order_select_label(self) -> str:
        return "High → Low" if self.grid_sort_desc else "Low → High"

    @rx.var
    def filter_mrs_rcvr_select_value(self) -> str:
        return "Below0↑" if self.filter_mrs_rcvr == "BELOW0_RISING" else "ALL"

    @rx.var
    def paginated_results(self) -> list[dict]:
        """Direct mirror of backend results (which are already paginated)."""
        return self.scanner_results

    def next_page(self): self.current_page = min(self.total_pages, self.current_page + 1)
    def prev_page(self): self.current_page = max(1, self.current_page - 1)

    @rx.event(background=True)
    async def poll_results(self): await poll_results_handler(self)
    def download_excel(self): 
        try: return download_excel_logic(self.scanner_results)
        except Exception as e: return rx.window_alert(f"Export Error: {e}")

    def open_tradingview(self, symbol: str):
        """Open TradingView chart (NSE) in a new tab."""
        s = str(symbol or "").strip().upper()
        if not s:
            return
        if ":" in s:
            base = s.split(":", 1)[1]
        else:
            base = s
        base = base.replace("_", "-")
        if base.endswith("-EQ"):
            base = base[:-3]
        elif base.endswith("-INDEX"):
            base = base[:-6]
        idx_alias = {"NIFTY50": "NIFTY", "NIFTYBANK": "BANKNIFTY"}
        tv_sym = idx_alias.get(base, base)
        return rx.redirect(f"https://www.tradingview.com/chart/?symbol=NSE:{tv_sym}", is_external=True)

    def open_screener_in(self, symbol: str):
        """Open Screener.in for fundamental checks (separate from TradingView chart)."""
        return rx.redirect(screener_in_url(symbol), is_external=True)

    def open_events_for_symbol(self, symbol: str):
        """
        Open Events page from main grid quick action.
        We pass symbol in query for future deep-linking; page still works even if query is ignored.
        """
        s = str(symbol or "").strip().upper()
        if not s:
            return rx.redirect("/events")
        return rx.redirect(f"/events?symbol={quote(s, safe=':-_')}")

    def scanner_snapshot_alert(
        self,
        symbol: str,
        p1d: str,
        rs_rating,
        mrs_str: str,
        mrs_prev_day_str: str,
        mrs_daily_str: str,
        rv,
        profile: str,
        status: str,
        brk_lvl_str: str,
        mrs_rcvr_str: str,
        w_rsi2_str: str,
    ):
        """Key technicals already in this scanner (not P/E or balance sheet — use sc → Screener)."""
        msg = (
            "Scanner snapshot (technicals from this grid)\n\n"
            f"{symbol}\n"
            f"CHG%: {p1d}  |  RS: {rs_rating}\n"
            f"W_mRS: {mrs_str}  |  Prior EOD mRS: {mrs_prev_day_str}\n"
            f"D_mRS: {mrs_daily_str}  |  RVOL: {rv}\n"
            f"W_RSI2: {w_rsi2_str}  (weekly Wilder RSI period 2)\n"
            f"Profile: {profile}  |  Status: {status}\n"
            f"BRK: {brk_lvl_str}  |  RCVR: {mrs_rcvr_str}\n\n"
            "For PE, ROE, debt, results → click [sc] (Screener.in)."
        )
        return rx.window_alert(msg)
