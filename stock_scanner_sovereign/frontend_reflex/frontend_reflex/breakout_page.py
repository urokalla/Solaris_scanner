import reflex as rx
from .breakout_state import BreakoutState
from .components.breakout_ui import breakout_header, breakout_sidebar
from .components.breakout_grid import breakout_data_grid

def breakout_page():
    return rx.box(
        rx.hstack(
            rx.vstack(breakout_header(), breakout_sidebar(), spacing="0", width="300px", height="100vh"),
            rx.vstack(
                breakout_data_grid(),
                rx.box(rx.text(f"LAST SYNC: {BreakoutState.last_sync} | STATUS: {BreakoutState.status_message}", size="1", color="#00FF00"), width="100%", padding="4px 15px", background_color="#111111", border_top="1px solid #333333"),
                spacing="0", width="100%", height="100vh", background_color="#000000", overflow="hidden"
            ), width="100%", height="100vh", spacing="0", background_color="#000000", overflow="hidden"
        ), width="100%", height="100vh", overflow="hidden", font_family="'JetBrains Mono', monospace",
    )
