import asyncio
import time

from config.settings import settings

from .breakout_engine_manager import get_breakout_scanner


async def poll_breakout_timing_handler(self):
    while True:
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
                preset="ALL",
                sort_key=self.sort_timing_key,
                sort_desc=self.sort_timing_desc,
                timing_filter=self.timing_filter,
                mode="timing",
            )
            new_results = view.get("results", [])
            changed = new_results != self.results
            self.total_count = view.get("total_count", 0)
            if changed:
                self.results = new_results
            self.status_message = "✅ Active" if self.total_count > 0 else "📡 Syncing..."
            if changed:
                self.last_sync = time.strftime("%H:%M:%S")
