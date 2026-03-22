import reflex as rx
from .breakout_engine_manager import get_breakout_scanner
from .breakout_handlers import update_engine_config_handler, download_excel_handler
from .breakout_tasks import poll_sidecar_handler

class BreakoutState(rx.State):
    universe, search_query, bench = "Nifty 50", "", "Nifty 50"
    status_message, last_sync = "Offline", "-"
    results: list[dict] = []
    total_count: int = 0
    current_page, page_size = 1, 50
    filter_trend, filter_rv, filter_status = "ALL", "ALL", "ALL"
    filter_min_price, filter_max_price = "0.0", "100000.0"

    def on_load(self): return BreakoutState.poll_sidecar
    @rx.var
    def result_count(self) -> int: return self.total_count
    @rx.var
    def alpha_breakouts(self) -> list[dict]: return [r for r in self.results if r.get("is_breakout")]
    @rx.var
    def total_pages(self) -> int: return max(1, (self.total_count + 49) // 50)
    @rx.var
    def paginated_results(self) -> list[dict]: return self.results
    
    def next_page(self): self.current_page = min(self.total_pages, self.current_page + 1)
    def prev_page(self): self.current_page = max(1, self.current_page - 1)
    def set_universe(self, u): self.universe, self.current_page = u, 1; get_breakout_scanner(universe=u).update_universe(u)
    def update_engine_config(self, f): update_engine_config_handler(self, f)
    def download_excel(self): return download_excel_handler(self)

    @rx.event(background=True)
    async def poll_sidecar(self): await poll_sidecar_handler(self)
