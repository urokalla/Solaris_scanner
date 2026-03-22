import asyncio, time
from .breakout_engine_manager import get_breakout_scanner
async def poll_sidecar_handler(self):
    while True:
        await asyncio.sleep(1.2)
        async with self:
            view = get_breakout_scanner(universe=self.universe).get_ui_view(
                page=self.current_page, search=self.search_query,
                status=self.filter_status, trend=self.filter_trend,
                rv=self.filter_rv, min_p=float(self.filter_min_price or 0), 
                max_p=float(self.filter_max_price or 1000000)
            )
            self.results = view.get("results", [])
            self.total_count = view.get("total_count", 0)
            self.status_message = "✅ Active" if self.total_count > 0 else "📡 Syncing..."
            self.last_sync = time.strftime("%H:%M:%S")

def breakout_vars_logic(self):
    """Atomic variable logic."""
    self.alpha_breakouts = [r for r in self.results if r.get("is_breakout")]
