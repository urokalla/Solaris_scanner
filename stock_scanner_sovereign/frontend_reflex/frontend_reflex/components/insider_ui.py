import reflex as rx

from ..insider_state import InsiderState


def insider_header() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text("SIDECAR • INSIDER", size="4", color="#7CFC00", font_weight="bold"),
            rx.text("PIT + SAST SNAPSHOT", size="1", color="#B0BEC5"),
            align_items="start",
            spacing="0",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text("STATUS", size="1", color="#B0BEC5", font_weight="bold"),
            rx.text(InsiderState.status_message, size="2", color="#00E676"),
            rx.text(
                rx.cond(
                    InsiderState.search_query == "",
                    f"{InsiderState.total_count} rows",
                    f"{InsiderState.filtered_count} / {InsiderState.total_count} rows",
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


def insider_sidebar() -> rx.Component:
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
            placeholder="symbol / person / company",
            on_change=InsiderState.set_search_query,
            value=InsiderState.search_query,
            width="calc(100% - 20px)",
            margin="0 10px",
            border="1px solid #333333",
            bg="#111111",
            color="white",
        ),
        rx.text("Signal", size="1", color="#888888", padding="8px 12px 2px 12px"),
        rx.select(
            ["ALL", "STRONG", "BUY", "SELL", "NEUTRAL"],
            value=InsiderState.filter_signal,
            on_change=InsiderState.set_filter_signal,
            width="calc(100% - 20px)",
            margin="0 10px",
            bg="#111111",
            border="1px solid #333333",
            color="white",
        ),
        rx.text(f"Last sync: {InsiderState.last_sync}", size="1", color="#888888", padding="10px"),
        width="300px",
        height="100vh",
        border_right="1px solid #333333",
        background_color="#000000",
        spacing="0",
    )


def insider_grid() -> rx.Component:
    header = rx.table.row(
        rx.table.column_header_cell("TIME", color="white"),
        rx.table.column_header_cell("SOURCE", color="white"),
        rx.table.column_header_cell("SYMBOL", color="white"),
        rx.table.column_header_cell("PERSON", color="white"),
        rx.table.column_header_cell("CATEGORY", color="white"),
        rx.table.column_header_cell("TXN", color="white"),
        rx.table.column_header_cell("QTY", color="white"),
        rx.table.column_header_cell("VALUE (₹)", color="white"),
        rx.table.column_header_cell(
            rx.vstack(
                rx.text("SAME", color="white", font_size="11px"),
                rx.text("BUYER #", color="white", font_size="11px"),
                spacing="0",
            ),
            color="white",
        ),
        rx.table.column_header_cell("SIGNAL", color="white"),
    )
    body = rx.table.body(
        rx.foreach(
            InsiderState.filtered_rows,
            lambda r: rx.table.row(
                rx.table.cell(r["when"], color="#D1D1D1"),
                rx.table.cell(r["source"], color="#9AA0A6"),
                rx.table.cell(
                    rx.text(
                        r["symbol"],
                        color="#FFB000",
                        cursor="pointer",
                        text_decoration="underline",
                        _hover={"color": "#00E5FF"},
                        on_click=InsiderState.open_tradingview(r["symbol"]),
                    )
                ),
                rx.table.cell(r["person_name"], color="#D1D1D1"),
                rx.table.cell(r["person_category"], color="#9AA0A6"),
                rx.table.cell(r["txn_type"], color="#D1D1D1"),
                rx.table.cell(r["qty"], color="#D1D1D1"),
                rx.table.cell(r["value"], color="#D1D1D1"),
                rx.table.cell(
                    rx.text(
                        r["buy_repeat_label"],
                        color=r["buy_repeat_color"],
                        font_weight=r["buy_repeat_weight"],
                    ),
                    title="How many BUY/STRONG rows for this symbol + person in the current file",
                ),
                rx.table.cell(rx.text(r["signal"], color=r["signal_color"])),
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

