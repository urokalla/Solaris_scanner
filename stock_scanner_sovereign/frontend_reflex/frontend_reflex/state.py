import reflex as rx, asyncio, time
from .engine import get_scanner
from .state_tasks import poll_results_handler, download_excel_logic

class State(rx.State):
    scanner_results: list[dict] = []
    alpha_signals: list[dict] = []
    pulse_data: list[dict] = []
    universe: str = "Nifty 500"
    benchmark_name, benchmark, status_message = "Nifty 50", "NSE:NIFTY50-INDEX", "Ready"
    result_count, current_page, page_size, total_pages = 0, 1, 50, 1
    search_query, filter_profile, filter_status, filter_mrs, filter_rv = "", "ALL", "ALL", "ALL", "ALL"
    filter_mrs_rcvr: str = "ALL"
    grid_sort_key: str = "rs_rating"
    grid_sort_desc: bool = True
    benchmark_ltp, benchmark_change, benchmark_is_up, sync_in_progress = "₹0.00", "0.00%", True, False

    def on_load(self):
        from utils.constants import DASHBOARD_BENCHMARK_MAP
        if self.benchmark_name not in DASHBOARD_BENCHMARK_MAP:
            self.benchmark_name = "Nifty 50"
            self.benchmark = DASHBOARD_BENCHMARK_MAP["Nifty 50"]
            get_scanner().update_params(benchmark=self.benchmark)
        yield State.poll_results
    def set_universe(self, u):
        # Breakout engine syncs when opening /breakout (avoid heavy reset + races from main page).
        self.universe, self.current_page = u, 1
        self.filter_mrs_rcvr = "ALL"
        get_scanner(universe=u)
    def set_benchmark(self, b):
        from utils.constants import DASHBOARD_BENCHMARK_MAP
        sym = DASHBOARD_BENCHMARK_MAP.get(b, DASHBOARD_BENCHMARK_MAP["Nifty 50"])
        self.benchmark_name, self.benchmark = b, sym
        get_scanner().update_params(benchmark=self.benchmark)

    def set_search_query(self, q): self.search_query, self.current_page = q, 1
    def set_filter_profile(self, v): self.filter_profile, self.current_page = v, 1
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
            self.grid_sort_desc = key not in ("symbol", "status", "profile")
        self.current_page = 1

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
