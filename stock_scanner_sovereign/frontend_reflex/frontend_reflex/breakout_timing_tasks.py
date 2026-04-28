import asyncio
import time

from config.settings import settings

from .breakout_engine_manager import get_breakout_scanner


async def poll_breakout_timing_handler(self):
    while True:
        await asyncio.sleep(max(0.5, float(settings.DASHBOARD_POLL_INTERVAL_SEC)))
        async with self:
            scanner = get_breakout_scanner(universe=self.universe, role="timing")
            view = scanner.get_ui_view(
                page=self.current_page,
                page_size=self.page_size,
                search=self.search_query,
                profile=self.filter_profile,
                brk_stage=self.filter_brk_stage,
                filter_mrs_grid=self.filter_mrs_grid,
                wmrs_slope=self.filter_wmrs_slope,
                filter_m_rsi2=self.filter_m_rsi2,
                preset="ALL",
                sort_key=self.sort_timing_key,
                sort_desc=self.sort_timing_desc,
                timing_filter=self.timing_filter,
                mode="timing",
            )
            new_results = view.get("results", [])
            new_total = int(view.get("total_count", 0) or 0)
            query_sig = "|".join(
                [
                    str(self.universe),
                    str(self.search_query or ""),
                    str(self.filter_profile or "ALL"),
                    str(self.filter_brk_stage or "ALL"),
                    str(self.filter_mrs_grid or "ALL"),
                    str(getattr(self, "filter_wmrs_slope", "ALL") or "ALL"),
                    str(self.filter_m_rsi2 or "ALL"),
                    str(self.timing_filter or "ALL"),
                    str(self.sort_timing_key or ""),
                    str(bool(self.sort_timing_desc)),
                    str(int(self.current_page)),
                    str(int(self.page_size)),
                ]
            )
            if new_total > 0 and not new_results and int(self.current_page) > 1:
                self.current_page = 1
                view = scanner.get_ui_view(
                    page=1,
                    page_size=self.page_size,
                    search=self.search_query,
                    profile=self.filter_profile,
                    brk_stage=self.filter_brk_stage,
                    filter_mrs_grid=self.filter_mrs_grid,
                    wmrs_slope=getattr(self, "filter_wmrs_slope", "ALL"),
                    filter_m_rsi2=self.filter_m_rsi2,
                    preset="ALL",
                    sort_key=self.sort_timing_key,
                    sort_desc=self.sort_timing_desc,
                    timing_filter=self.timing_filter,
                    mode="timing",
                )
                new_results = view.get("results", [])
                new_total = int(view.get("total_count", 0) or 0)
            if new_results:
                self.last_non_empty_signature = query_sig
                self.last_non_empty_results = new_results
            elif (
                query_sig == str(getattr(self, "last_non_empty_signature", "") or "")
                and bool(getattr(self, "last_non_empty_results", []))
            ):
                new_results = list(self.last_non_empty_results)
                new_total = len(new_results)
            changed = new_results != self.results
            self.total_count = new_total
            if changed:
                self.results = new_results
            self.status_message = "✅ Active" if self.total_count > 0 else "📡 Syncing..."
            if changed:
                self.last_sync = time.strftime("%H:%M:%S")
