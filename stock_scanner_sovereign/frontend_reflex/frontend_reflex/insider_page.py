import reflex as rx

from .components.insider_ui import insider_grid, insider_header, insider_sidebar


def insider_page() -> rx.Component:
    return rx.box(
        rx.hstack(
            insider_sidebar(),
            rx.vstack(
                insider_header(),
                insider_grid(),
                spacing="0",
                width="100%",
                height="100vh",
                background_color="#000000",
                overflow="hidden",
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
        font_family="'JetBrains Mono', monospace",
        style={"WebkitFontSmoothing": "antialiased"},
    )

