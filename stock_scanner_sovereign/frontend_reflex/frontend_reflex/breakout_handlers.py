import io
import time

import pandas as pd
import reflex as rx

from .breakout_engine_manager import get_breakout_scanner


def update_engine_config_handler(self, form_data):
    self.timeframe = form_data.get("timeframe", "Daily")
    self.ema_fast = int(form_data.get("ema_fast", 9))
    self.ema_slow = int(form_data.get("ema_slow", 21))
    # Must match config default BREAKOUT_PIVOT_HIGH_WINDOW (10); drives pivot for BRK_LVL.
    self.breakout_period = int(form_data.get("brk_period", 10))
    get_breakout_scanner().update_params(pivot_high_window=self.breakout_period)
    self.status_message = f"Re-Configuring {self.universe}..."
    return rx.toast(f"Engine Tuned: {self.timeframe} {self.ema_fast}/{self.ema_slow} pivot={self.breakout_period}")


def download_excel_handler(self):
    """
    Export all rows matching current filters/sort — not only the visible page.
    Slim columns only (avoids huge DataFrames / odd types from full result dicts).
    """
    scanner = get_breakout_scanner(universe=self.universe)
    # Same universe row set as the live grid; singleton scanner ignores `universe=` once created.
    scanner.update_universe(self.universe, None)
    view = scanner.get_ui_view(
        page=1,
        page_size=500_000,
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
    rows = view.get("results") or []
    if not rows:
        return rx.toast("Nothing to export (0 rows).")

    # Only columns that mirror the current /breakout grid (no legacy sidecar / quant extras).
    slim = []
    for r in rows:
        slim.append(
            {
                "symbol": r.get("symbol"),
                "setup_score": r.get("setup_score"),
                "ltp": r.get("ltp"),
                "chp": r.get("chp"),
                "rs_rating": r.get("rs_rating"),
                "rvol": r.get("rv"),
                "mrs_w": r.get("mrs_weekly"),
                "brk_lvl_d": r.get("brk_lvl"),
                "brk_lvl_w": r.get("brk_lvl_w"),
                "atr9x2": r.get("atr9x2_state"),
                "state_d": r.get("state_name"),
                "last_tag_d": r.get("last_tag"),
                "pct_from_b_d": r.get("brk_move_pct"),
                "b_bar_d_ist": r.get("brk_b_anchor_dt"),
                "last_tag_w": r.get("last_tag_w"),
                "pct_from_b_w": r.get("brk_move_pct_w"),
                "b_bar_w_ist": r.get("brk_b_anchor_dt_w"),
                "b_cnt_dw": f"{r.get('b_count', 0)}/{r.get('b_count_w', 0)}",
                "e9ct_dw": f"{r.get('e9t_count', 0)}/{r.get('e9t_count_w', 0)}",
                "e21c_dw": f"{r.get('e21c_count', 0)}/{r.get('e21c_count_w', 0)}",
                "rst_dw": f"{r.get('rst_count', 0)}/{r.get('rst_count_w', 0)}",
                "age_dw": f"{r.get('age_mins', '—')} / {r.get('age_mins_w', '—')}",
            }
        )
    df = pd.DataFrame(slim)
    df.columns = [
        "SYMBOL",
        "SETUP_SCORE",
        "PRICE",
        "CHG_PCT",
        "RS",
        "RVOL",
        "W_MRS",
        "BRK_LVL_D",
        "BRK_LVL_W",
        "W_ATR9x2",
        "STATE_D",
        "LAST_TAG_D",
        "PCT_FROM_B_D",
        "B_BAR_DATE_D_IST",
        "LAST_TAG_W",
        "PCT_FROM_B_W",
        "B_BAR_DATE_W_IST",
        "B_COUNT_D_W",
        "E9CT_D_W",
        "E21C_D_W",
        "RST_D_W",
        "AGE_D_W",
    ]
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Breakouts")
    fname = f"breakouts_{self.universe.replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M')}.xlsx"
    return rx.download(data=out.getvalue(), filename=fname)


def download_timing_excel_handler(self):
    """
    Export /breakout-timing rows (timing tags, WHEN IST, % from B, state) with current filters/sort.
    """
    scanner = get_breakout_scanner(universe=self.universe)
    scanner.update_universe(self.universe, None)
    view = scanner.get_ui_view(
        page=1,
        page_size=500_000,
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
    rows = view.get("results") or []
    if not rows:
        return rx.toast("Nothing to export (0 rows).")

    slim = []
    for r in rows:
        slim.append(
            {
                "symbol": r.get("symbol"),
                "setup_score": r.get("setup_score"),
                "ltp": r.get("ltp"),
                "chp": r.get("chp"),
                "rs_rating": r.get("rs_rating"),
                "rvol": r.get("rv"),
                "mrs_w": r.get("mrs_weekly"),
                "last_tag_d": r.get("timing_last_tag"),
                "when_d_ist": r.get("timing_last_event_dt"),
                "pct_from_b_d": r.get("brk_move_pct"),
                "pct_live_d": r.get("brk_move_live_pct"),
                "b_bar_d_ist": r.get("brk_b_anchor_dt"),
                "last_tag_w": r.get("timing_last_tag_w"),
                "when_w_ist": r.get("timing_last_event_dt_w"),
                "pct_from_b_w": r.get("brk_move_pct_w"),
                "pct_live_w": r.get("brk_move_live_pct_w"),
                "b_bar_w_ist": r.get("brk_b_anchor_dt_w"),
            }
        )
    df = pd.DataFrame(slim)
    df.columns = [
        "SYMBOL",
        "SETUP_SCORE",
        "PRICE",
        "CHG_PCT",
        "RS",
        "RVOL",
        "W_MRS",
        "LAST_TAG_D",
        "WHEN_D_IST",
        "PCT_FROM_B_D",
        "SINCE BRK % (D)",
        "B_BAR_DATE_D_IST",
        "LAST_TAG_W",
        "WHEN_W_IST",
        "PCT_FROM_B_W",
        "SINCE BRK % (W)",
        "B_BAR_DATE_W_IST",
    ]
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="BreakoutTiming")
    fname = f"breakout_timing_{self.universe.replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M')}.xlsx"
    return rx.download(data=out.getvalue(), filename=fname)
