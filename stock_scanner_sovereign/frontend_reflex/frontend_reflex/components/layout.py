import reflex as rx
from ..state import State
from .header import terminal_header; from .sidebar import universe_panel, benchmark_panel
from .feed import elite_alpha_feed; from .grid import data_grid

def loading_marquee():
    return rx.cond(
        State.sync_in_progress,
        rx.box(rx.text("DATA LOADING . . . PROCESSING UNIVERSE . . . ", color="#FFB000", font_weight="bold", font_size="11px"), width="100%", padding="4px 10px", background_color="#111111", border_top="1px solid #333333"),
        rx.box(rx.hstack(rx.text("MARKETS OPEN | ", color="#00FF00", font_size="11px"), rx.text(State.universe, color="#00FF00", font_size="11px"), rx.text(" | ", color="#00FF00", font_size="11px"), rx.text(State.result_count, color="#00FF00", font_size="11px"), rx.text(" SECURITIES LOADED", color="#00FF00", font_size="11px"), spacing="1"), width="100%", padding="4px 10px", background_color="#111111", border_top="1px solid #333333")
    )

def sidebar():
    # Keep universe + sector <select> **outside** the scroll region. A single overflow parent
    # captures wheel events while the sector list is open → janky scrolling / jumpy menu.
    return rx.vstack(
        terminal_header(),
        universe_panel(),
        rx.box(
            benchmark_panel(),
            flex="1",
            min_height="0",
            width="100%",
            overflow_y="auto",
            overscroll_behavior="contain",
        ),
        spacing="0",
        width="300px",
        height="100vh",
        border_right="1px solid #333333",
    )

def main_content():
    return rx.vstack(
        elite_alpha_feed(),
        rx.box(data_grid(), flex="1", min_height="0", width="100%", overflow="hidden", display="flex", flex_direction="column"),
        loading_marquee(),
        spacing="0",
        width="100%",
        flex="1",
        min_height="0",
        background_color="#000000",
    )
