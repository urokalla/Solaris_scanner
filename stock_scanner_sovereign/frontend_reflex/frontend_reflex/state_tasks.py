import asyncio, time, pandas as pd, io, reflex as rx
from config.settings import settings
from .engine import get_scanner

async def poll_results_handler(self):
    interval = max(1.0, float(settings.DASHBOARD_POLL_INTERVAL_SEC))
    while True:
        await asyncio.sleep(interval)
        # Snapshot current UI filters/state quickly under lock.
        async with self:
            filters = {
                "universe": self.universe,
                "sector": self.dashboard_sector,
                "benchmark": self.benchmark,
                "search": self.search_query,
                "profile": self.filter_profile,
                "status": self.filter_status,
                "mrs_min": self.filter_mrs,
                "rv_min": self.filter_rv,
                "mrs_rcvr": self.filter_mrs_rcvr,
                "sort_key": self.grid_sort_key,
                "sort_desc": self.grid_sort_desc,
            }
            page = self.current_page
            page_size = self.page_size

        # Run heavy scanner query off the async event loop to avoid UI hangs.
        view = await asyncio.to_thread(
            get_scanner().get_ui_view,
            filters=filters,
            page=page,
            page_size=page_size,
        )

        async with self:
            self.scanner_results = view.get("results", [])
            self.alpha_signals = view.get("pulse", [])
            self.pulse_data = [i for i in self.alpha_signals if "NIFTY" in i.get("symbol", "")]
            self.result_count = view.get("total_count", 0)
            self.total_pages = max(1, (self.result_count + self.page_size - 1) // self.page_size)
            self.benchmark_ltp = view.get("bench_ltp") or "₹0.00"
            self.benchmark_change = view.get("bench_change") or "0.00%"
            self.benchmark_is_up = view.get("bench_up") if view.get("bench_up") is not None else True
            self.status_message = view.get("status", "Active")
            self.sync_in_progress = "Active" not in self.status_message

def download_excel_logic(results):
    df = pd.DataFrame(results)
    cols = ["symbol", "ltp", "rs_rating", "mrs", "mrs_prev_day_str", "mrs_daily_str", "w_rsi2_str", "rv", "profile", "status"]
    for c in cols:
        if c not in df.columns:
            df[c] = "—"
    df = df[cols].copy()
    df.columns = ["TICKER", "PRICE", "RS_RATING", "W_mRS", "PREV_W_mRS", "D_mRS", "W_RSI2", "RVOL", "PROFILE", "STATUS"]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False, sheet_name='Solaris')
    return rx.download(data=output.getvalue(), filename=f"Solaris_Export_{time.strftime('%H%M')}.xlsx")
