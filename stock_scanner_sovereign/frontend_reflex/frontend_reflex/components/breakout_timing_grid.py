import reflex as rx

from ..breakout_timing_state import BreakoutTimingState


def breakout_timing_data_grid():
    header_row = rx.table.row(
        rx.table.column_header_cell(rx.text("SYMBOL", color="white"), color="white"),
        rx.table.column_header_cell(rx.text("PRICE", color="white"), color="white"),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("RS", color="white"),
                rx.text(BreakoutTimingState.rs_rating_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutTimingState.toggle_sort_rs_rating,
            ),
            color="white",
        ),
        rx.table.column_header_cell(rx.text("CHG%", color="white"), color="white"),
        rx.table.column_header_cell(rx.text("LAST TAG D", color="white"), color="white"),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("WHEN (D) IST", color="white"),
                rx.text(BreakoutTimingState.when_d_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutTimingState.toggle_sort_when_d,
            ),
            color="white",
        ),
        rx.table.column_header_cell(rx.text("LAST TAG W", color="white"), color="white"),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("WHEN (W) IST", color="white"),
                rx.text(BreakoutTimingState.when_w_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutTimingState.toggle_sort_when_w,
            ),
            color="white",
        ),
        rx.table.column_header_cell(rx.text("RVOL", color="white"), color="white"),
        rx.table.column_header_cell(rx.text("W_MRS", color="white"), color="white"),
        rx.table.column_header_cell(rx.text("STATE D / W", color="white"), color="white"),
        rx.table.column_header_cell(rx.text("AGE D / W", color="white"), color="white"),
    )
    body = rx.table.body(
        rx.foreach(
            BreakoutTimingState.results,
            lambda r: rx.table.row(
                rx.table.cell(
                    rx.box(
                        r["symbol"],
                        color="#FFB000",
                        font_weight="bold",
                        font_size="12px",
                        cursor="pointer",
                        text_decoration="underline",
                        _hover={"color": "#00E5FF"},
                        on_click=BreakoutTimingState.open_tradingview(r["symbol"]),
                        width="100%",
                    ),
                    padding_y="0",
                ),
                rx.table.cell(r.get("ltp", "—"), color=r.get("chp_color", "#D1D1D1"), font_size="12px", padding_y="0"),
                rx.table.cell(
                    rx.text(r.get("rs_rating", "—"), color=r.get("rs_rating_color", "#D1D1D1"), font_weight="bold"),
                    font_size="12px",
                    padding_y="0",
                ),
                rx.table.cell(r.get("chp", "—"), color=r.get("chp_color", "#D1D1D1"), font_size="11px", padding_y="0"),
                rx.table.cell(
                    rx.text(r.get("timing_last_tag", "—"), color=r.get("timing_last_tag_color", "#888888")),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("timing_last_event_dt", "—"), color="#E0E0E0", font_size="10px"),
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("timing_last_tag_w", "—"), color=r.get("timing_last_tag_color_w", "#888888")),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("timing_last_event_dt_w", "—"), color="#E0E0E0", font_size="10px"),
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("rv", "—"), color=r.get("rv_color", "#D1D1D1")),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("mrs_weekly", "—"), color=r.get("mrs_color", "#D1D1D1")),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(
                        f"{r.get('timing_state_name', '—')} / {r.get('timing_state_name_w', '—')}",
                        color="#D1D1D1",
                        font_size="10px",
                    ),
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(f"{r.get('timing_age_mins', '—')} / {r.get('timing_age_mins_w', '—')}", color="#888888", font_size="10px"),
                    padding_y="0",
                ),
                height="26px",
                padding="0",
                border_bottom="1px solid #1f1f1f",
                _odd={"background_color": "#050505"},
                _even={"background_color": "#0b0b0b"},
                _hover={"background_color": "#151515"},
            ),
        ),
    )
    return rx.vstack(
        rx.table.root(
            rx.table.header(header_row),
            body,
            width="100%",
            variant="surface",
            background_color="#000000",
        ),
        rx.hstack(
            rx.button(
                "PREV",
                on_click=BreakoutTimingState.prev_page,
                size="1",
                variant="outline",
                color_scheme="gray",
                disabled=BreakoutTimingState.current_page == 1,
            ),
            rx.text(
                f"PAGE {BreakoutTimingState.current_page} / {BreakoutTimingState.total_pages}",
                size="1",
                color="#D1D1D1",
            ),
            rx.button(
                "NEXT",
                on_click=BreakoutTimingState.next_page,
                size="1",
                variant="outline",
                color_scheme="gray",
                disabled=BreakoutTimingState.current_page == BreakoutTimingState.total_pages,
            ),
            spacing="4",
            padding="10px",
            width="100%",
            justify_content="center",
            border_top="1px solid #333333",
        ),
        width="100%",
        flex="1",
        overflow_y="auto",
        padding="0",
        spacing="0",
    )
