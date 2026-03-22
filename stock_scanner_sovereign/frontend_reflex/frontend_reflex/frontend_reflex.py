import reflex as rx
import sys, os
from .state import State
from .components import sidebar, main_content
from .engine import get_scanner
from .breakout_page import breakout_page
from .breakout_state import BreakoutState

def index() -> rx.Component:
    return rx.box(
        rx.hstack(
            sidebar(),
            rx.box(
                main_content(),
                flex="1",
                min_width="0",
                min_height="0",
                height="100vh",
                display="flex",
                flex_direction="column",
            ),
            width="100%",
            height="100vh",
            spacing="0",
            align_items="stretch",
            background_color="#000000",
        ),
        width="100%",
        min_height="100vh",
        font_family="'JetBrains Mono', monospace",
        style={"WebkitFontSmoothing": "antialiased"},
    )

app = rx.App(
    theme=rx.theme(
        appearance="dark",
        has_background=True,
        accent_color="amber",
        gray_color="slate",
        radius="none",
    ),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap",
    ],
)
app.add_page(index, title="SOLARIS • RS SCANNER", on_load=State.on_load)
app.add_page(breakout_page, route="/breakout", title="SIDECAR • BREAKOUT STRATEGY", on_load=BreakoutState.on_load)
