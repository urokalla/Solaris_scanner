import reflex as rx, asyncio, time
from .engine import get_scanner; from .breakout_engine_manager import get_breakout_scanner
from .state_tasks import poll_results_handler, download_excel_logic

class State(rx.State):
    scanner_results: list[dict] = []
    alpha_signals: list[dict] = []
    pulse_data: list[dict] = []
    universe: str = "Nifty 500"
    benchmark_name, benchmark, status_message = "Nifty 50", "NSE:NIFTY50-INDEX", "Ready"
    result_count, current_page, page_size, total_pages = 0, 1, 50, 1
    search_query, filter_profile, filter_status, filter_mrs, filter_rv = "", "ALL", "ALL", "ALL", "ALL"
    benchmark_ltp, benchmark_change, benchmark_is_up, sync_in_progress = "₹0.00", "0.00%", True, False

    def on_load(self):
        from utils.constants import DASHBOARD_BENCHMARK_MAP
        if self.benchmark_name not in DASHBOARD_BENCHMARK_MAP:
            self.benchmark_name = "Nifty 50"
            self.benchmark = DASHBOARD_BENCHMARK_MAP["Nifty 50"]
            get_scanner().update_params(benchmark=self.benchmark)
        yield State.poll_results
    def set_universe(self, u): self.universe, self.current_page = u, 1; get_scanner(universe=u); get_breakout_scanner(universe=u).update_universe(u)
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
