import reflex as rx

from ..events_state import EventsState


def events_header() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text("SIDECAR • EVENTS", size="4", color="#00E5FF", font_weight="bold"),
            rx.text("NIFTY500 • snapshot CSV (no live NSE)", size="1", color="#B0BEC5"),
            align_items="start",
            spacing="0",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text("STATUS", size="1", color="#B0BEC5", font_weight="bold"),
            rx.text(
                EventsState.status_message,
                size="2",
                color=rx.cond(EventsState.status_message.contains("⚠️"), "#FF6E6E", "#00E676"),
            ),
            rx.text(
                rx.cond(
                    EventsState.search_query == "",
                    f"{EventsState.total_count} rows",
                    f"{EventsState.filtered_count} / {EventsState.total_count} rows",
                ),
                size="1",
                color="#B0BEC5",
            ),
            align_items="end",
            spacing="0",
        ),
        width="100%",
        padding="10px 14px",
        border_bottom="1px solid #333333",
        background_color="#000000",
    )


def events_sidebar() -> rx.Component:
    return rx.vstack(
        rx.button(
            "← BACK TO SCANNER",
            on_click=lambda: rx.redirect("/"),
            variant="outline",
            color_scheme="gray",
            width="calc(100% - 20px)",
            margin="10px",
        ),
        rx.text("FILTER", size="1", color="#B0BEC5", font_weight="bold", padding="6px 12px"),
        rx.input(
            placeholder="symbol / keyword",
            on_change=EventsState.set_search_query,
            value=EventsState.search_query,
            width="calc(100% - 20px)",
            margin="0 10px",
            border="1px solid #333333",
            bg="#111111",
            color="white",
            _focus={"border_color": "#00E5FF"},
        ),
        rx.text(f"Last sync: {EventsState.last_sync}", size="1", color="#888888", padding="10px"),
        width="300px",
        height="100vh",
        border_right="1px solid #333333",
        background_color="#000000",
        spacing="0",
    )


def events_grid() -> rx.Component:
    header = rx.table.row(
        rx.table.column_header_cell("SYMBOL", color="white"),
        rx.table.column_header_cell("TIME", color="white"),
        rx.table.column_header_cell("SUBJECT", color="white"),
        rx.table.column_header_cell("TAG", color="white"),
        rx.table.column_header_cell("PDF", color="white"),
    )
    body = rx.table.body(
        rx.foreach(
            EventsState.filtered_rows,
            lambda r: rx.table.row(
                rx.table.cell(r["symbol"], color="#FFB000"),
                rx.table.cell(r["an_dt"], color="#D1D1D1"),
                rx.table.cell(r["desc"], color="#D1D1D1"),
                rx.table.cell(rx.text(r["tag"], color=r["tag_color"])),
                rx.table.cell(
                    rx.cond(
                        r["attchmntFile"] != "",
                        rx.link("open", href=r["attchmntFile"], is_external=True, color="#00E5FF"),
                        rx.text("—", color="#666666"),
                    )
                ),
                _odd={"background_color": "#050505"},
                _even={"background_color": "#0b0b0b"},
                _hover={"background_color": "#151515"},
            ),
        )
    )
    return rx.box(
        rx.table.root(rx.table.header(header), body, width="100%"),
        width="100%",
        height="100vh",
        overflow_y="auto",
        background_color="#000000",
    )

