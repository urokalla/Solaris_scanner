import reflex as rx

from .breakout_engine_manager import get_breakout_scanner
from .breakout_timing_tasks import poll_breakout_timing_handler
from .state import State


class BreakoutTimingState(rx.State):
    """Sidecar page: when the last daily / weekly cycle event occurred (IST from bar timestamp)."""

    universe: str = "Nifty 50"
    search_query: str = ""
    timing_filter: str = "ALL"
    results: list[dict] = []
    total_count: int = 0
    current_page: int = 1
    page_size: int = 100
    filter_brk_stage: str = "ALL"
    filter_mrs_grid: str = "ALL"
    filter_m_rsi2: str = "ALL"
    filter_profile: str = "ALL"
    status_message: str = "Offline"
    last_sync: str = "-"
    sort_timing_key: str = "last_ts"
    sort_timing_desc: bool = True
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

    async def on_load(self):
        main = await self.get_state(State)
        u = main.universe
        async with self:
            self.universe = u
        brk = get_breakout_scanner(universe=u)
        brk.update_universe(u, None)
        return BreakoutTimingState.poll_timing

    def set_universe(self, u: str):
        self.universe, self.current_page = u, 1
        # Clear any symbol filter carried over from the previous universe so switching
        # (e.g. Nifty 500 → Nifty 50) doesn't leave the grid stuck on a symbol that no
        # longer exists in the new universe.
        self.search_query = ""
        get_breakout_scanner(universe=u).update_universe(u, None)

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

    @rx.event(background=True)
    async def poll_timing(self):
        await poll_breakout_timing_handler(self)
