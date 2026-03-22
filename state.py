import reflex as rx
import pandas as pd
import asyncio, time, io
from .engine import get_scanner
from utils.symbols import get_nifty_symbols

class State(rx.State):
    scanner_results: list[dict] = []
    is_loading: bool = False
    status_message: str = "Initializing Engine..."
    search_query: str = ""
    universe: str = "Nifty 500"
    last_sync: str = "Never"
    result_count: int = 0
    pulse_data: list[dict] = []
    audit_history: list[dict] = []
    selected_audit_symbol: str = ""
    tab_value: str = "all"
    display_signals_only: bool = False
    benchmark_name: str = "Nifty 50"
    benchmark: str = "NSE:NIFTY50-INDEX"
    timeframe_name: str = "Daily"
    timeframe: str = "1d"
    processed_count: int = 0
    total_symbols: int = 0
    benchmark_ltp: str = "0.00"
    benchmark_change: str = "0.00%"
    benchmark_is_up: bool = True
    buy_signals_count: int = 0
    breakout_signals_count: int = 0
    elite_count: int = 0
    leader_count: int = 0
    rs_90_count: int = 0
    filter_profile: str = "ALL"
    filter_status: str = "ALL"
    filter_rs_min: int = 0
    filter_rv: str = "ALL"
    filter_mrs: str = "ALL"
    use_ema_filter: bool = False
    ema_period: int = 30
    use_ema_cross_filter: bool = False
    ema_short_period: int = 9
    ema_long_period: int = 21
    ma_length: int = 50
    sig_length: int = 30
    sync_in_progress: bool = False
    command_input: str = ""
    
    # Engine Settings
    engine_config_open: bool = False
    
    # Pagination Support
    current_page: int = 1
    page_size: int = 50

    @rx.var
    def filtered_results(self) -> list[dict]:
        data = self.scanner_results
        
        # 1. Profile Filter (Tabs or Dropdown)
        if self.tab_value != "all":
            if self.tab_value == "elite": data = [r for r in data if "ELITE" in r["profile"].upper()]
            elif self.tab_value == "leaders": data = [r for r in data if "LEADER" in r["profile"].upper()]
            elif self.tab_value == "rising": data = [r for r in data if "RISING" in r["profile"].upper()]
            elif self.tab_value == "laggards": data = [r for r in data if "LAGGARD" in r["profile"].upper() or "FADING" in r["profile"].upper()]
        
        # 2. Advanced Dropdown Filters
        if self.filter_profile != "ALL":
            data = [r for r in data if self.filter_profile in r["profile"].upper()]
        
        if self.filter_status != "ALL":
            data = [r for r in data if self.filter_status in r["status"].upper()]
            
        # 3. RS Rating Filter
        if self.filter_rs_min > 0:
            data = [r for r in data if int(r["rs_rating"]) >= self.filter_rs_min]

        # 4. EMA Filters (Reactive)
        if self.use_ema_filter:
            data = [r for r in data if r.get("ema_ok", True)]
        
        if self.use_ema_cross_filter:
            data = [r for r in data if r.get("ema_cross_ok", True)]
            
        # 5. Symbol Search
        if self.search_query:
            q = self.search_query.lower()
            data = [r for r in data if q in r["symbol"].lower()]
            
        # 6. Relative Volume (RV) Filter
        if self.filter_rv != "ALL":
            try:
                threshold = float(self.filter_rv.replace(">", "").strip())
                data = [r for r in data if float(r.get("rv", 0)) >= threshold]
            except ValueError:
                pass
            
        # 7. RS Value (mRS) Filter
        if self.filter_mrs != "ALL":
            try:
                threshold = float(self.filter_mrs.replace(">", "").strip())
                data = [r for r in data if float(r.get("mrs", 0)) >= threshold]
            except Exception:
                pass
        
        # Reset page if filters change
        # self.current_page = 1 # Can't do inside @rx.var
        
        return data

    @rx.var
    def paginated_results(self) -> list[dict]:
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        return self.filtered_results[start:end]

    @rx.var
    def total_pages(self) -> int:
        return (len(self.filtered_results) + self.page_size - 1) // self.page_size

    @rx.var
    def alpha_signals(self) -> list[dict]:
        try:
            # Safely filter and sort alpha signals
            sigs = [r for r in self.scanner_results if ("BUY" in str(r.get("status", "")) or "BREAKOUT" in str(r.get("status", ""))) and float(r.get("mrs_val", 0)) > 0]
            return sorted(sigs, key=lambda x: float(x.get("mrs_val", 0)), reverse=True)[:4]
        except Exception as e:
            return []

    @rx.var
    def all_symbols(self) -> list[str]: return [r.get("symbol", "") for r in self.scanner_results]

    @rx.event
    def on_load(self):
        get_scanner()
        yield State.sync_results
        yield State.poll_results

    @rx.event
    def set_search_query(self, query: str): self.search_query = query

    @rx.event
    def set_command_input(self, val: str): self.command_input = val

    @rx.event
    def handle_command(self):
        cmd = self.command_input.upper().strip()
        if "<GO>" in cmd:
            universe_map = {
                "NIFTY50": "Nifty 50",
                "NIFTY100": "Nifty 100",
                "NIFTY500": "Nifty 500",
                "NIFTYMIDCAP100": "Nifty Midcap 100",
                "MIDCAP100": "Nifty Midcap 100",
                "SMALLCAP100": "Nifty Smallcap 100",
                "NIFTYSMALLCAP100": "Nifty Smallcap 100",
                "ALLNSE": "All NSE Stocks",
                "ALL": "All NSE Stocks"
            }
            target = cmd.replace("<GO>", "").strip()
            if target in universe_map:
                yield State.set_universe(universe_map[target])
            else:
                yield rx.window_alert(f"Unknown Command: {target}")
        self.command_input = ""

    @rx.event
    def on_key_down(self, key: str):
        if key == "Enter":
            yield State.handle_command
        elif key == "F9":
            yield State.force_refresh
        elif key == "F12":
            self.scanner_results = []
            self.result_count = 0
            self.status_message = "Screen Cleared (F12)"

    @rx.event
    def set_tab_value(self, val: str): 
        self.tab_value = val
        self.current_page = 1

    @rx.event
    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1

    @rx.event
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1

    @rx.event
    def set_page(self, page: int):
        self.current_page = page

    @rx.event
    def set_display_signals_only(self, val: bool): self.display_signals_only = val

    @rx.event
    def set_filter_profile(self, val: str): self.filter_profile = val

    @rx.event
    def set_filter_status(self, val: str): self.filter_status = val

    @rx.event
    def set_filter_rs_min(self, val: str):
        self.filter_rs_min = int(val) if val.isdigit() else 0

    @rx.event
    def set_filter_mrs(self, val: str):
        self.filter_mrs = val
        self.current_page = 1

    @rx.event
    def set_use_ema_filter(self, val: bool):
        self.use_ema_filter = val
        yield State.update_scanner_params

    @rx.event
    def set_use_ema_cross_filter(self, val: bool):
        self.use_ema_cross_filter = val
        yield State.update_scanner_params

    @rx.event
    def force_refresh(self): yield State.sync_results

    @rx.event
    def set_benchmark(self, bench: str):
        from utils.constants import BENCHMARK_MAP
        self.benchmark_name, self.benchmark = bench, BENCHMARK_MAP.get(bench, bench)
        yield State.update_scanner_params

    @rx.event
    def set_timeframe(self, tf: str):
        self.timeframe_name, self.timeframe = tf, "1d" if tf == "Daily" else "1w"
        yield State.update_scanner_params

    @rx.event
    def set_ma_length(self, val: str):
        self.ma_length = int(val) if val.isdigit() else 50
        yield State.update_scanner_params

    @rx.event
    def set_sig_length(self, val: str):
        self.sig_length = int(val) if val.isdigit() else 30
        yield State.update_scanner_params

    @rx.event
    def set_ema_period(self, val: str):
        self.ema_period = int(val) if val.isdigit() else 30
        yield State.update_scanner_params

    @rx.event
    def set_ema_short_period(self, val: str):
        self.ema_short_period = int(val) if val.isdigit() else 9
        yield State.update_scanner_params

    @rx.event
    def set_ema_long_period(self, val: str):
        self.ema_long_period = int(val) if val.isdigit() else 21
        yield State.update_scanner_params

    @rx.event
    def set_mansfield_preset(self, val: str):
        if val == "Standard (50/30)": self.ma_length, self.sig_length = 50, 30
        elif val == "Aggressive (10/10)": self.ma_length, self.sig_length = 10, 10
        elif val == "Trend (100/50)": self.ma_length, self.sig_length = 100, 50
        yield State.update_scanner_params

    @rx.event
    def set_universe(self, universe: str):
        self.universe, self.scanner_results, self.status_message = universe, [], "Switching universe..."
        symbols = get_nifty_symbols(universe)
        # Handle engine logic centrally
        get_scanner(symbols=symbols, universe=universe)
        yield State.update_scanner_params

    @rx.event
    def update_scanner_params(self):
        if not self.universe or not self.benchmark or not self.timeframe:
            return rx.window_alert("Missing Parameters: Please select a Universe, Benchmark, and Timeframe.")
        
        get_scanner().update_params(
            benchmark=self.benchmark, 
            universe=self.universe,
            timeframe=self.timeframe,
            ma_length=int(self.ma_length), 
            sig_length=int(self.sig_length), 
            use_ema_filter=self.use_ema_filter, 
            ema_period=int(self.ema_period), 
            use_ema_cross_filter=self.use_ema_cross_filter, 
            ema_short_period=int(self.ema_short_period), 
            ema_long_period=int(self.ema_long_period)
        )
        yield State.sync_results

    @rx.event
    def download_excel(self):
        """Export current filtered results to Excel."""
        if not self.filtered_results:
            return rx.window_alert("No data to export.")

        try:
            # 1. Prepare Data
            df = pd.DataFrame(self.filtered_results)
            
            # 2. Clean/Select Columns
            cols = ["symbol", "ltp", "p1d", "rs_rating", "mrs", "mrs_daily", "rv", "profile", "status"]
            df = df[cols].copy()
            
            # Rename for Excel clarity
            df.columns = ["TICKER", "PRICE", "CHG%", "RS_RATING", "W_mRS", "D_mRS", "RVOL", "PROFILE", "STATUS"]
            
            # 3. Create Excel in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Solaris_Scan')
                
                # Formatting
                workbook = writer.book
                worksheet = writer.sheets['Solaris_Scan']
                header_format = workbook.add_format({'bold': True, 'bg_color': '#000080', 'font_color': 'white'})
                
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    worksheet.set_column(col_num, col_num, 15)

            # 4. Trigger Download
            return rx.download(
                data=output.getvalue(),
                filename=f"Solaris_Export_{time.strftime('%Y%m%d_%H%M')}.xlsx",
            )
        except Exception as e:
            print(f"Excel Export Error: {e}")
            return rx.window_alert(f"Export failed: {str(e)}")

    @rx.event(background=True)
    async def poll_results(self):
        while True:
            # Optimized polling: 2.0s to reduce frontend CPU load
            await asyncio.sleep(2.0)
            async with self: self.sync_results()

    @rx.event
    def sync_results(self):
        """Efficient state synchronization including shared results from multi-core engine."""
        try:
            sc = get_scanner()
            with sc.lock:
                # 1. Sync shared results from parallel workers
                shared = dict(sc.shared_results)
                for sym, res in shared.items():
                    current_ltp = sc.scanner_results.get(sym, {}).get("ltp", 0.0)
                    sc.scanner_results.setdefault(sym, {}).update(res)
                    if current_ltp > 0 and res.get("ltp", 0) != current_ltp:
                        sc.scanner_results[sym]["ltp"] = current_ltp
                    
                    if sym in sc.pulse_symbols:
                        l, c = res.get("ltp", 0), res.get("change_pct")
                        if sym not in sc.pulse_results: sc.pulse_results[sym] = {"ltp": 0, "change_pct": 0}
                        if l > 0: sc.pulse_results[sym]["ltp"] = l
                        if c is not None: sc.pulse_results[sym]["change_pct"] = c
                
                self.status_message = str(sc.status_message)
                self.processed_count = sc.processed_count
                self.total_symbols = len(sc.symbols)
                self.sync_in_progress = sc.status_message not in ["✅ Active"]
                
                res_snap = dict(sc.scanner_results)
                bench = sc.benchmark
                
                # benchmark stats
                b_res = sc.pulse_results.get(bench, {})
                if not b_res or float(b_res.get('ltp', 0)) == 0:
                    b_res = sc.scanner_results.get(bench, {})
                
                if b_res:
                    self.benchmark_ltp = f"{float(b_res.get('ltp', 0)):,.2f}"
                    change = float(b_res.get('change_pct', 0))
                    self.benchmark_change = f"{change:+.2f}%"
                    self.benchmark_is_up = change >= 0
           
            # 2. Build UI Results list
            results = []
            buy_c, brk_c, e_c, l_c, rs90_c = 0, 0, 0, 0, 0
            
            for sym, r in res_snap.items():
                if sym == bench: continue
                s = str(r.get("status", "-"))
                profile = str(r.get("profile", "-"))
                rs_val = int(r.get("rs_rating", 0))
                mrs_val = float(r.get('mrs', 0))
                
                # Stats
                if "BUY" in s: buy_c += 1
                if "BREAKOUT" in s: brk_c += 1
                if "ELITE" in profile: e_c += 1
                if "LEADER" in profile: l_c += 1
                if rs_val >= 90: rs90_c += 1
                
                if self.display_signals_only and not any(x in s for x in ["BUY", "BREAKOUT"]): 
                    continue
                
                results.append({
                    "symbol": sym.split(":")[1].split("-")[0] if ":" in sym else sym,
                    "ltp": f"₹{float(r.get('ltp',0)):,.2f}", 
                    "profile": profile,
                    "rs_rating": rs_val, 
                    "mrs": f"{mrs_val:.2f}",
                    "mrs_daily": f"{float(r.get('mrs_daily') or 0):.2f}",
                    "mrs_daily_up": float(r.get("mrs_daily") or 0) > 0,
                    "mrs_1m": f"{float(r.get('mrs_1m',0)):.2f}",
                    "mrs_3m": f"{float(r.get('mrs_3m',0)):.2f}",
                    "mrs_6m": f"{float(r.get('mrs_6m',0)):.2f}",
                    "mrs_1y": f"{float(r.get('mrs_1y',0)):.2f}",
                    "rv": f"{float(r.get('rv',0)):.2f}", 
                    "rv_up": bool(r.get("rv_up", False)),
                    "rv_down": bool(r.get("rv_down", False)),
                    "price_up": float(r.get("change_pct", 0)) > 0,
                    "price_down": float(r.get("change_pct", 0)) < 0,
                    "status": s, 
                    "p1d": str(r.get("p1d", "❌")), 
                    "p1w": str(r.get("p1w", "❌")), 
                    "p1m": str(r.get("p1m", "❌")), 
                    "p3m": str(r.get("p3m", "❌")),
                    "h52w": f"₹{float(r.get('h52w',0)):,.2f}" if r.get("h52w",0) > 0 else "N.A.",
                    "mrs_val": mrs_val,
                    "mrs_up": mrs_val > 0
                })
            
            self.buy_signals_count, self.breakout_signals_count = buy_c, brk_c
            self.elite_count, self.leader_count, self.rs_90_count = e_c, l_c, rs90_c
            
            # Pulse
            self.pulse_data = [
                {
                    "symbol": p.replace("NSE:","").replace("-INDEX",""), 
                    "ltp": f"₹{sc.pulse_results.get(p,{}).get('ltp',0):,.2f}", 
                    "change": f"{sc.pulse_results.get(p,{}).get('change_pct',0):+.2f}%", 
                    "is_positive": sc.pulse_results.get(p,{}).get('change_pct',0) >= 0
                } for p in sc.pulse_symbols
            ]
            
            results.sort(key=lambda x: x["rs_rating"], reverse=True)
            self.scanner_results = results
            self.result_count = len(results)
            self.last_sync = time.strftime("%H:%M:%S")
            self.status_message = f"✅ {sc.status_message} | {len(results)} Stocks Loaded"
            
        except Exception as e: 
            print(f"Sync Error: {e}")
