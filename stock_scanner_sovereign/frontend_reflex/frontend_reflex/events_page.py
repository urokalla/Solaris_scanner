import reflex as rx

from .components.events_ui import events_grid, events_header, events_sidebar


def events_page() -> rx.Component:
    return rx.box(
        rx.hstack(
            events_sidebar(),
            rx.vstack(
                events_header(),
                events_grid(),
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

