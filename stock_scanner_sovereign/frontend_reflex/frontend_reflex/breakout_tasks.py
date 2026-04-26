import asyncio, time
from .breakout_engine_manager import get_breakout_scanner
from config.settings import settings
async def poll_sidecar_handler(self):
    while True:
        # Keep breakout poll cadence aligned with dashboard env tuning.
        await asyncio.sleep(max(0.5, float(settings.DASHBOARD_POLL_INTERVAL_SEC)))
        async with self:
            view = get_breakout_scanner(universe=self.universe).get_ui_view(
                page=self.current_page,
                page_size=self.page_size,
                search=self.search_query,
                profile=self.filter_profile,
                brk_stage=self.filter_brk_stage,
                filter_mrs_grid=self.filter_mrs_grid,
                filter_m_rsi2=self.filter_m_rsi2,
                preset=str(getattr(self, "preset_mode", None) or "ALL").strip(),
                sort_key=self.sort_sidecar_key,
                sort_desc=self.sort_sidecar_desc,
                mode="strategy",
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
