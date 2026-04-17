import reflex as rx
from .state import State, screener_in_url
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
    filter_m_rsi2 = "ALL"
    filter_min_price, filter_max_price = "0.0", "100000.0"
    filter_brk_stage = "ALL"
    filter_mrs_grid: str = "ALL"
    preset_mode: str = "ALL"
    sort_sidecar_key: str = ""
    sort_sidecar_desc: bool = False

    async def on_load(self):
        """Align sidecar universe with main dashboard; refresh engine when opening /breakout."""
        main = await self.get_state(State)
        u = main.universe
        async with self:
            self.universe = u
        brk = get_breakout_scanner(universe=u)
        if getattr(brk, "universe", None) != u:
            brk.update_universe(u)
        return BreakoutState.poll_sidecar
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
    @rx.var
    def mrsi2_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "mrsi2":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"

    @rx.var
    def ltp_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "ltp":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"

    @rx.var
    def chp_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "chp":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"

    @rx.var
    def brk_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "brk":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"

    @rx.var
    def tf_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "tf":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"

    @rx.var
    def stage_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "status":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"

    @rx.var
    def symbol_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "symbol":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"

    @rx.var
    def mrs_grid_sort_arrow(self) -> str:
        if self.sort_sidecar_key != "mrs_grid":
            return ""
        return "▼" if self.sort_sidecar_desc else "▲"

    def next_page(self): self.current_page = min(self.total_pages, self.current_page + 1)
    def prev_page(self): self.current_page = max(1, self.current_page - 1)
    def set_universe(self, u):
        self.universe, self.current_page = u, 1
        self.sort_sidecar_key, self.sort_sidecar_desc = "", False
        self.filter_m_rsi2 = "ALL"
        self.filter_mrs_grid = "ALL"
        get_breakout_scanner(universe=u).update_universe(u)
    def set_search_query(self, q: str): self.search_query, self.current_page = (q or ""), 1
    def set_filter_brk_stage(self, v: str):
        self.filter_brk_stage, self.current_page = (v or "ALL"), 1

    def set_filter_mrs_grid(self, v: str):
        self.filter_mrs_grid, self.current_page = (v or "ALL").strip().upper(), 1

    def set_filter_m_rsi2(self, v: str):
        self.filter_m_rsi2, self.current_page = (v or "ALL"), 1

    def set_preset_mode(self, v: str):
        mode = (v or "ALL").strip().upper()
        self.preset_mode = mode
        self.search_query = ""
        self.current_page = 1

        # Presets are independent from BRK STAGE dropdown; backend applies preset filters.
        if mode == "EARLY":
            self.sort_sidecar_key = "mrs"
            self.sort_sidecar_desc = False
            return
        if mode == "BREAKOUT":
            self.sort_sidecar_key = "chp"
            self.sort_sidecar_desc = True
            return
        if mode == "STAGE 2":
            self.sort_sidecar_key = "mrs"
            self.sort_sidecar_desc = False
            return
        if mode == "RETEST":
            self.sort_sidecar_key = ""
            self.sort_sidecar_desc = False
            return
        if mode == "STRONG_RETEST":
            self.sort_sidecar_key = ""
            self.sort_sidecar_desc = False
            return
        if mode == "FAST20":
            self.sort_sidecar_key = ""
            self.sort_sidecar_desc = False
            return
        if mode == "HIGH10":
            self.sort_sidecar_key = ""
            self.sort_sidecar_desc = False
            return
        if mode == "HIGH10_LITE":
            self.sort_sidecar_key = ""
            self.sort_sidecar_desc = False
            return
        if mode == "BUYNOW_CROSS":
            self.sort_sidecar_key = ""
            self.sort_sidecar_desc = False
            return
        if mode == "ALL":
            return
        self.sort_sidecar_key = ""
        self.sort_sidecar_desc = False
    def toggle_sort(self, key: str):
        if self.sort_sidecar_key == key:
            self.sort_sidecar_desc = not self.sort_sidecar_desc
        else:
            self.sort_sidecar_key = key
            # Numeric / priority columns: descend first; pure text: ascend first.
            self.sort_sidecar_desc = key not in ("symbol", "trend_text", "udai", "status", "mrsi2")
        self.current_page = 1
    def toggle_sort_mrs(self):
        self.toggle_sort("mrs")
    def toggle_sort_udai(self):
        self.toggle_sort("udai")
    def toggle_sort_mrsi2(self):
        self.toggle_sort("mrsi2")

    def toggle_sort_ltp(self):
        self.toggle_sort("ltp")

    def toggle_sort_chp(self):
        self.toggle_sort("chp")

    def toggle_sort_brk(self):
        self.toggle_sort("brk")

    def toggle_sort_tf(self):
        self.toggle_sort("tf")

    def toggle_sort_stage(self):
        self.toggle_sort("status")

    def toggle_sort_symbol(self):
        self.toggle_sort("symbol")

    def toggle_sort_mrs_grid(self):
        self.toggle_sort("mrs_grid")

    def update_engine_config(self, f): update_engine_config_handler(self, f)
    def download_excel(self): return download_excel_handler(self)

    def open_tradingview(self, symbol: str):
        """Open TradingView chart in a new tab for sidecar symbol values."""
        s = str(symbol or "").strip().upper()
        if not s:
            return
        if ":" in s:
            base = s.split(":", 1)[1]
        else:
            base = s
        base = base.replace("_", "-")
        if base.endswith("-EQ"):
            base = base[:-3]
        elif base.endswith("-INDEX"):
            base = base[:-6]
        idx_alias = {
            "NIFTY50": "NIFTY",
            "NIFTYBANK": "BANKNIFTY",
        }
        tv_sym = idx_alias.get(base, base)
        return rx.redirect(f"https://www.tradingview.com/chart/?symbol=NSE:{tv_sym}", is_external=True)

    def open_screener_in(self, symbol: str):
        return rx.redirect(screener_in_url(symbol), is_external=True)

    def sidecar_snapshot_alert(
        self,
        symbol: str,
        ltp,
        chp: str,
        brk_lvl,
        mrs_weekly: str,
        trend_text: str,
        status: str,
        mrs_grid_status: str,
    ):
        msg = (
            "Sidecar snapshot (technicals)\n\n"
            f"{symbol}\n"
            f"LTP: {ltp}  |  CHG%: {chp}\n"
            f"BRK: {brk_lvl}  |  W mRS: {mrs_weekly}\n"
            f"Trend: {trend_text}  |  Stage: {status}\n"
            f"Grid: {mrs_grid_status}\n\n"
            "Fundamentals → use [sc] next to symbol (opens Screener.in)."
        )
        return rx.window_alert(msg)

    @rx.event(background=True)
    async def poll_sidecar(self): await poll_sidecar_handler(self)
