import io
import time

import pandas as pd
import reflex as rx

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
    """
    Export all rows matching current filters/sort — not only the visible page.
    Slim columns only (avoids huge DataFrames / odd types from full result dicts).
    """
    scanner = get_breakout_scanner(universe=self.universe)
    view = scanner.get_ui_view(
        page=1,
        page_size=500_000,
        search=self.search_query,
        brk_stage=self.filter_brk_stage,
        filter_mrs_grid=self.filter_mrs_grid,
        filter_m_rsi2=self.filter_m_rsi2,
        preset="ALL",
        sort_key=self.sort_sidecar_key,
        sort_desc=self.sort_sidecar_desc,
    )
    rows = view.get("results") or []
    if not rows:
        return rx.toast("Nothing to export (0 rows).")

    slim = []
    for r in rows:
        slim.append(
            {
                "symbol": r.get("symbol"),
                "ltp": r.get("ltp"),
                "chp": r.get("chp"),
                "brk_lvl": r.get("brk_lvl"),
                "brk_lvl_w": r.get("brk_lvl_w"),
                "tf_ema": r.get("tf_ema"),
                "ema_d": r.get("ema_d_str"),
                "ema_w": r.get("ema_w_str"),
                "trend": r.get("trend_text"),
                "mrs_w": r.get("mrs_weekly"),
                "mrs_status": r.get("mrs_grid_status"),
                "mn_rsi2": r.get("m_rsi2_ui"),
                "udai": r.get("udai_ui"),
                "brk_stage": r.get("status"),
            }
        )
    df = pd.DataFrame(slim)
    df.columns = [
        "SYMBOL",
        "PRICE",
        "CHG_PCT",
        "BRK_LVL",
        "BRK_W",
        "TF_EMA",
        "EMA_D",
        "EMA_W",
        "TREND",
        "MRS_W",
        "MRS_STATUS",
        "MN_RSI2",
        "UDAI",
        "BRK_STAGE",
    ]
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Breakouts")
    fname = f"breakouts_{self.universe.replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M')}.xlsx"
    return rx.download(data=out.getvalue(), filename=fname)
