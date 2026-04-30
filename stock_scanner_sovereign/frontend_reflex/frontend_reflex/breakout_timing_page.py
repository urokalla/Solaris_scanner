import reflex as rx

from .breakout_timing_state import BreakoutTimingDailyState, BreakoutTimingWeeklyState
from .components.breakout_timing_grid import (
    breakout_timing_daily_data_grid,
    breakout_timing_weekly_data_grid,
)
from .components.breakout_timing_ui import (
    breakout_timing_daily_header,
    breakout_timing_daily_sidebar,
    breakout_timing_weekly_header,
    breakout_timing_weekly_sidebar,
)


def _clock_shell(sidebar, header, grid, footer_lines: str):
    return rx.box(
        rx.hstack(
            rx.vstack(header, sidebar, spacing="0", width="300px", height="100vh"),
            rx.vstack(
                rx.box(
                    grid,
                    width="100%",
                    flex="1",
                    min_height="0",
                    overflow_x="auto",
                    overflow_y="auto",
                ),
                rx.box(
                    rx.text(footer_lines, size="1", color="#00FF00"),
                    width="100%",
                    padding="4px 15px",
                    background_color="#111111",
                    border_top="1px solid #333333",
                ),
                spacing="0",
                width="100%",
                height="100vh",
                background_color="#000000",
                overflow="hidden",
                display="flex",
                flex_direction="column",
            ),
            width="100%",
            height="100vh",
            spacing="0",
            background_color="#000000",
            overflow="hidden",
        ),
        width="100%",
        min_height="100vh",
        background_color="#000000",
        overflow="hidden",
        font_family="'JetBrains Mono', monospace",
        style={"WebkitFontSmoothing": "antialiased"},
    )


def breakout_clock_daily_page():
    foot = (
        f"LAST SYNC: {BreakoutTimingDailyState.last_sync} | STATUS: {BreakoutTimingDailyState.status_message} | "
        "Daily clock: LAST TAG D / WHEN (D) / SINCE BRK % (D). "
        "% FROM B = B-bar close → LTP; SINCE BRK % (D) = LTP vs frozen break (brk_b_anchor_level); at RST = LTP vs brk_lvl."
    )
    return _clock_shell(
        breakout_timing_daily_sidebar(),
        breakout_timing_daily_header(),
        breakout_timing_daily_data_grid(),
        foot,
    )


def breakout_clock_weekly_page():
    foot = (
        f"LAST SYNC: {BreakoutTimingWeeklyState.last_sync} | STATUS: {BreakoutTimingWeeklyState.status_message} | "
        "Weekly clock: LAST TAG W / WHEN (W) / SINCE BRK % (W). "
        "WHEN = bar timestamp (IST) for last weekly cycle tag update."
    )
    return _clock_shell(
        breakout_timing_weekly_sidebar(),
        breakout_timing_weekly_header(),
        breakout_timing_weekly_data_grid(),
        foot,
    )


def breakout_timing_legacy_redirect_page():
    return rx.box(
        rx.center(rx.text("Redirecting to Daily Breakout Clock…", color="#888888"), height="100vh"),
        width="100%",
        min_height="100vh",
        background_color="#000000",
    )
