import reflex as rx

from .breakout_engine_manager import get_breakout_scanner
from .breakout_timing_tasks import poll_breakout_timing_handler
from .breakout_handlers import download_timing_excel_handler
from .state import State


class BreakoutClockState(rx.State):
    """Shared breakout clock fields and actions (daily / weekly pages use subclasses)."""

    clock_timeframe: str = ""
    universe: str = "Nifty 500"
    search_query: str = ""
    timing_filter: str = "ALL"
    results: list[dict] = []
    total_count: int = 0
    live_struct_rows: int = 0
    live_struct_rows_raw: int = 0
    current_page: int = 1
    page_size: int = 50
    filter_brk_stage: str = "ALL"
    filter_mrs_grid: str = "ALL"
    filter_wmrs_slope: str = "ALL"
    filter_m_rsi2: str = "ALL"
    filter_profile: str = "ALL"
    status_message: str = "Offline"
    last_sync: str = "-"
    eod_sync_status: str = "EOD_SYNC_UNKNOWN"
    eod_expected_date: str = "-"
    eod_fresh_count: int = 0
    eod_total_count: int = 0
    eod_stale_count: int = 0
    eod_sync_pct: float = 0.0
    eod_last_checked_ist: str = "-"
    sort_timing_key: str = "last_ts"
    sort_timing_desc: bool = True
    last_non_empty_signature: str = ""
    last_non_empty_results: list[dict] = []
    results_signature: str = ""

    @rx.var
    def total_pages(self) -> int:
        ps = max(1, int(self.page_size))
        return max(1, (int(self.total_count) + ps - 1) // ps)

    @rx.var
    def when_d_sort_arrow(self) -> str:
        if self.sort_timing_key != "last_ts":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def when_w_sort_arrow(self) -> str:
        if self.sort_timing_key != "last_ts_w":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def rs_rating_sort_arrow(self) -> str:
        if self.sort_timing_key != "rs_rating":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def setup_score_sort_arrow(self) -> str:
        if self.sort_timing_key != "setup_score":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def symbol_sort_arrow(self) -> str:
        if self.sort_timing_key != "symbol":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def ltp_sort_arrow(self) -> str:
        if self.sort_timing_key != "ltp":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def chp_sort_arrow(self) -> str:
        if self.sort_timing_key != "chp":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def rvol_sort_arrow(self) -> str:
        if self.sort_timing_key != "rv":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def wmrs_sort_arrow(self) -> str:
        if self.sort_timing_key != "wmrs":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def last_tag_d_sort_arrow(self) -> str:
        if self.sort_timing_key != "last_tag_d":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def last_tag_w_sort_arrow(self) -> str:
        if self.sort_timing_key != "last_tag_w":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def pct_from_b_d_sort_arrow(self) -> str:
        if self.sort_timing_key != "pct_from_b_d":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def pct_live_d_sort_arrow(self) -> str:
        if self.sort_timing_key != "pct_live_d":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def pct_from_b_w_sort_arrow(self) -> str:
        if self.sort_timing_key != "pct_from_b_w":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    @rx.var
    def pct_live_w_sort_arrow(self) -> str:
        if self.sort_timing_key != "pct_live_w":
            return ""
        return "▼" if self.sort_timing_desc else "▲"

    async def on_load(self):
        main = await self.get_state(State)
        u = main.universe
        async with self:
            self.universe = u
        brk = get_breakout_scanner(universe=u, role="timing")
        brk.update_universe(u, None)
        # Reflex requires a class-referenced EventHandler, not `self.poll_timing` (plain function).
        return type(self).poll_timing

    def set_universe(self, u: str):
        self.universe, self.current_page = u, 1
        self.search_query = ""
        get_breakout_scanner(universe=u, role="timing").update_universe(u, None)

    def set_search_query(self, q: str):
        self.search_query, self.current_page = (q or ""), 1

    def set_filter_profile(self, v: str):
        self.filter_profile, self.current_page = (v or "ALL").strip().upper(), 1

    def set_timing_filter(self, v: str):
        self.timing_filter, self.current_page = (v or "ALL").strip().upper(), 1

    def set_filter_brk_stage(self, v: str):
        self.filter_brk_stage, self.current_page = (v or "ALL"), 1

    def set_filter_mrs_grid(self, v: str):
        self.filter_mrs_grid, self.current_page = (v or "ALL").strip().upper(), 1

    def set_filter_wmrs_slope(self, v: str):
        self.filter_wmrs_slope, self.current_page = (v or "ALL").strip().upper(), 1

    def set_filter_m_rsi2(self, v: str):
        self.filter_m_rsi2, self.current_page = (v or "ALL"), 1

    def toggle_sort_when_d(self):
        if self.sort_timing_key == "last_ts":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "last_ts"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_when_w(self):
        if self.sort_timing_key == "last_ts_w":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "last_ts_w"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_rs_rating(self):
        if self.sort_timing_key == "rs_rating":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "rs_rating"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_setup_score(self):
        if self.sort_timing_key == "setup_score":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "setup_score"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_symbol(self):
        if self.sort_timing_key == "symbol":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "symbol"
            self.sort_timing_desc = False
        self.current_page = 1

    def toggle_sort_ltp(self):
        if self.sort_timing_key == "ltp":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "ltp"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_chp(self):
        if self.sort_timing_key == "chp":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "chp"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_rvol(self):
        if self.sort_timing_key == "rv":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "rv"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_wmrs(self):
        if self.sort_timing_key == "wmrs":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "wmrs"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_last_tag_d(self):
        if self.sort_timing_key == "last_tag_d":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "last_tag_d"
            self.sort_timing_desc = False
        self.current_page = 1

    def toggle_sort_last_tag_w(self):
        if self.sort_timing_key == "last_tag_w":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "last_tag_w"
            self.sort_timing_desc = False
        self.current_page = 1

    def toggle_sort_pct_from_b_d(self):
        if self.sort_timing_key == "pct_from_b_d":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "pct_from_b_d"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_pct_live_d(self):
        if self.sort_timing_key == "pct_live_d":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "pct_live_d"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_pct_from_b_w(self):
        if self.sort_timing_key == "pct_from_b_w":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "pct_from_b_w"
            self.sort_timing_desc = True
        self.current_page = 1

    def toggle_sort_pct_live_w(self):
        if self.sort_timing_key == "pct_live_w":
            self.sort_timing_desc = not self.sort_timing_desc
        else:
            self.sort_timing_key = "pct_live_w"
            self.sort_timing_desc = True
        self.current_page = 1

    def next_page(self):
        self.current_page = min(self.total_pages, self.current_page + 1)

    def prev_page(self):
        self.current_page = max(1, self.current_page - 1)

    def open_tradingview(self, symbol: str):
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
        idx_alias = {
            "NIFTY50": "NIFTY",
            "NIFTYBANK": "BANKNIFTY",
        }
        tv_sym = idx_alias.get(base, base)
        return rx.redirect(f"https://www.tradingview.com/chart/?symbol=NSE:{tv_sym}", is_external=True)

    def download_excel(self):
        return download_timing_excel_handler(self)

    @rx.event(background=True)
    async def poll_timing(self):
        await poll_breakout_timing_handler(self)


class BreakoutTimingDailyState(BreakoutClockState):
    clock_timeframe: str = "daily"


class BreakoutTimingWeeklyState(BreakoutClockState):
    clock_timeframe: str = "weekly"
    sort_timing_key: str = "last_ts_w"


BreakoutTimingState = BreakoutTimingDailyState


class BreakoutTimingLegacyRedirectState(rx.State):
    async def on_load(self):
        return rx.redirect("/breakout-clock-daily", is_external=False)
