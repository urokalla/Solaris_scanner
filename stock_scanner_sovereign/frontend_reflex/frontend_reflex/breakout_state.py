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
    filter_brk_stage = "ALL"
    sort_sidecar_key: str = ""
    sort_sidecar_desc: bool = False

    def on_load(self): return BreakoutState.poll_sidecar
    @rx.var
    def result_count(self) -> int: return self.total_count
    @rx.var
    def alpha_breakouts(self) -> list[dict]: return [r for r in self.results if r.get("is_breakout")]
    @rx.var
    def total_pages(self) -> int: return max(1, (self.total_count + 49) // 50)
    @rx.var
    def paginated_results(self) -> list[dict]: return self.results
    @rx.var
    def mrs_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "mrs":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"
    @rx.var
    def udai_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "udai":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"
    
    def next_page(self): self.current_page = min(self.total_pages, self.current_page + 1)
    def prev_page(self): self.current_page = max(1, self.current_page - 1)
    def set_universe(self, u):
        self.universe, self.current_page = u, 1
        self.sort_sidecar_key, self.sort_sidecar_desc = "", False
        get_breakout_scanner(universe=u).update_universe(u)
    def set_search_query(self, q: str): self.search_query, self.current_page = (q or ""), 1
    def set_filter_brk_stage(self, v: str): self.filter_brk_stage, self.current_page = (v or "ALL"), 1
    def toggle_sort_mrs(self):
        if self.sort_sidecar_key == "mrs":
            self.sort_sidecar_desc = not self.sort_sidecar_desc
        else:
            self.sort_sidecar_key = "mrs"
            self.sort_sidecar_desc = True
        self.current_page = 1
    def toggle_sort_udai(self):
        if self.sort_sidecar_key == "udai":
            self.sort_sidecar_desc = not self.sort_sidecar_desc
        else:
            self.sort_sidecar_key = "udai"
            self.sort_sidecar_desc = False
        self.current_page = 1
    def update_engine_config(self, f): update_engine_config_handler(self, f)
    def download_excel(self): return download_excel_handler(self)

    @rx.event(background=True)
    async def poll_sidecar(self): await poll_sidecar_handler(self)
