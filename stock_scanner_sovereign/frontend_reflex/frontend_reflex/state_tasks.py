import asyncio, time, pandas as pd, io, reflex as rx
from .engine import get_scanner
async def poll_results_handler(self):
    while True:
        await asyncio.sleep(2.5)
        async with self:
            filters = {"universe": self.universe, "benchmark": self.benchmark, "search": self.search_query, 
                       "profile": self.filter_profile, "status": self.filter_status, "mrs_min": self.filter_mrs, "rv_min": self.filter_rv}
            view = get_scanner().get_ui_view(filters=filters, page=self.current_page, page_size=self.page_size)
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
    cols = ["symbol", "ltp", "rs_rating", "mrs", "mrs_prev_day_str", "rv", "profile", "status"]
    df = df[cols].copy(); df.columns = ["TICKER", "PRICE", "RS_RATING", "W_mRS", "PREV_W_mRS", "RVOL", "PROFILE", "STATUS"]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False, sheet_name='Solaris')
    return rx.download(data=output.getvalue(), filename=f"Solaris_Export_{time.strftime('%H%M')}.xlsx")
