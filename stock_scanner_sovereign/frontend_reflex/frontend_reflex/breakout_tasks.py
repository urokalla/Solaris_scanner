import asyncio, time
from .breakout_engine_manager import get_breakout_scanner
async def poll_sidecar_handler(self):
    while True:
        # Match main dashboard cadence to reduce UI churn/reflow.
        await asyncio.sleep(2.5)
        async with self:
            view = get_breakout_scanner(universe=self.universe).get_ui_view(
                page=self.current_page,
                page_size=self.page_size,
                search=self.search_query,
                brk_stage=self.filter_brk_stage,
                sort_key=self.sort_sidecar_key,
                sort_desc=self.sort_sidecar_desc,
            )
            new_results = view.get("results", [])
            changed = new_results != self.results
            self.total_count = view.get("total_count", 0)
            if changed:
                self.results = new_results
            self.status_message = "✅ Active" if self.total_count > 0 else "📡 Syncing..."
            # Update clock only on material change to avoid repainting every cycle.
            if changed:
                self.last_sync = time.strftime("%H:%M:%S")

def breakout_vars_logic(self):
    """Atomic variable logic."""
    self.alpha_breakouts = [r for r in self.results if r.get("is_breakout")]
