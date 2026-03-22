import asyncio, time
from .breakout_engine_manager import get_breakout_scanner
async def poll_sidecar_handler(self):
    while True:
        await asyncio.sleep(1.2)
        async with self:
            view = get_breakout_scanner(universe=self.universe).get_ui_view(
                page=self.current_page,
                page_size=self.page_size,
                search=self.search_query,
                brk_stage=self.filter_brk_stage,
                sort_key=self.sort_sidecar_key,
                sort_desc=self.sort_sidecar_desc,
            )
            self.results = view.get("results", [])
            self.total_count = view.get("total_count", 0)
            self.status_message = "✅ Active" if self.total_count > 0 else "📡 Syncing..."
            self.last_sync = time.strftime("%H:%M:%S")

def breakout_vars_logic(self):
    """Atomic variable logic."""
    self.alpha_breakouts = [r for r in self.results if r.get("is_breakout")]
