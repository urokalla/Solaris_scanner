import reflex as rx

from .breakout_timing_state import BreakoutTimingState
from .components.breakout_timing_grid import breakout_timing_data_grid
from .components.breakout_timing_ui import breakout_timing_header, breakout_timing_sidebar


def breakout_timing_page():
    return rx.box(
        rx.hstack(
            rx.vstack(breakout_timing_header(), breakout_timing_sidebar(), spacing="0", width="300px", height="100vh"),
            rx.vstack(
                rx.box(
                    breakout_timing_data_grid(),
                    width="100%",
                    flex="1",
                    min_height="0",
                    overflow_x="auto",
                    overflow_y="auto",
                ),
                rx.box(
                    rx.text(
                        f"LAST SYNC: {BreakoutTimingState.last_sync} | STATUS: {BreakoutTimingState.status_message} | "
                        "WHEN = bar timestamp (IST) for the last daily / weekly cycle tag update.",
                        size="1",
                        color="#00FF00",
                    ),
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
