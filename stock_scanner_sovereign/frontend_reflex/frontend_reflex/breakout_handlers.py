import reflex as rx, pandas as pd
from .breakout_engine_manager import get_breakout_scanner

def update_engine_config_handler(self, form_data):
    self.timeframe = form_data.get("timeframe", "Daily")
    self.ema_fast = int(form_data.get("ema_fast", 9))
    self.ema_slow = int(form_data.get("ema_slow", 21))
    # Must match config default BREAKOUT_PIVOT_HIGH_WINDOW (20); drives pivot for BRK_LVL.
    self.breakout_period = int(form_data.get("brk_period", 20))
    get_breakout_scanner().update_params(pivot_high_window=self.breakout_period)
    self.status_message = f"Re-Configuring {self.universe}..."
    return rx.toast(f"Engine Tuned: {self.timeframe} {self.ema_fast}/{self.ema_slow} pivot={self.breakout_period}")

def download_excel_handler(self):
    df = pd.DataFrame(self.paginated_results)
    return rx.download(data=df.to_csv(index=False), filename=f"breakouts_{self.universe}.csv")
