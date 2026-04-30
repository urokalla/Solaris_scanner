import reflex as rx

from ..breakout_timing_state import BreakoutTimingDailyState, BreakoutTimingWeeklyState


def _tape_header_cells(S):
    """SYMBOL … W_MRS shared header prefix."""
    return [
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("SYMBOL", color="white"),
                rx.text(S.symbol_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_symbol,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("SCORE", color="white"),
                rx.text(S.setup_score_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_setup_score,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("PRICE", color="white"),
                rx.text(S.ltp_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_ltp,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("CHG%", color="white"),
                rx.text(S.chp_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_chp,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("RS", color="white"),
                rx.text(S.rs_rating_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_rs_rating,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("RVOL", color="white"),
                rx.text(S.rvol_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_rvol,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("W_MRS", color="white"),
                rx.text(S.wmrs_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_wmrs,
            ),
            color="white",
        ),
    ]


def _pagination(S):
    return rx.hstack(
        rx.button(
            "PREV",
            on_click=S.prev_page,
            size="1",
            variant="outline",
            color_scheme="gray",
            disabled=S.current_page == 1,
        ),
        rx.text(
            f"PAGE {S.current_page} / {S.total_pages}",
            size="1",
            color="#D1D1D1",
        ),
        rx.button(
            "NEXT",
            on_click=S.next_page,
            size="1",
            variant="outline",
            color_scheme="gray",
            disabled=S.current_page == S.total_pages,
        ),
        spacing="4",
        padding="10px",
        width="100%",
        justify_content="center",
        border_top="1px solid #333333",
    )


def breakout_timing_daily_data_grid():
    S = BreakoutTimingDailyState
    header_row = rx.table.row(
        *_tape_header_cells(S),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("LAST TAG D", color="white"),
                rx.text(S.last_tag_d_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_last_tag_d,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.text("LIVE_STRUCT_D", color="white"),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("WHEN (D) IST", color="white"),
                rx.text(S.when_d_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_when_d,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("SINCE BRK % (D)", color="#00E5FF", font_size="11px"),
                rx.text(S.pct_live_d_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_pct_live_d,
            ),
            color="white",
        ),
    )
    body = rx.table.body(
        rx.foreach(
            S.results,
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
                        on_click=S.open_tradingview(r["symbol"]),
                        width="100%",
                    ),
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(
                        r.get("setup_score_ui", "—"),
                        color=r.get("setup_score_color", "#D1D1D1"),
                        font_weight="bold",
                    ),
                    font_size="12px",
                    padding_y="0",
                ),
                rx.table.cell(r.get("ltp", "—"), color=r.get("chp_color", "#D1D1D1"), font_size="12px", padding_y="0"),
                rx.table.cell(r.get("chp", "—"), color=r.get("chp_color", "#D1D1D1"), font_size="11px", padding_y="0"),
                rx.table.cell(
                    rx.text(r.get("rs_rating", "—"), color=r.get("rs_rating_color", "#D1D1D1"), font_weight="bold"),
                    font_size="12px",
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
                        r.get("last_tag", "—"),
                        color=r.get("last_tag_color", "#888888"),
                    ),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(
                        r.get("live_struct_d", "—"),
                        color=r.get("live_struct_d_color", "#D1D1D1"),
                    ),
                    font_size="10px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("last_event_dt", "—"), color="#E0E0E0", font_size="10px"),
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(
                        r.get("brk_move_live_pct", "—"),
                        color=r.get("brk_move_live_color", "#666666"),
                        font_weight="bold",
                        font_size="10px",
                    ),
                    padding_y="0",
                ),
                height="34px",
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
        _pagination(S),
        width="100%",
        flex="1",
        overflow_y="auto",
        padding="0",
        spacing="0",
    )


def breakout_timing_weekly_data_grid():
    S = BreakoutTimingWeeklyState
    header_row = rx.table.row(
        *_tape_header_cells(S),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("LAST TAG W", color="white"),
                rx.text(S.last_tag_w_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_last_tag_w,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("WHEN (W) IST", color="white"),
                rx.text(S.when_w_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_when_w,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("SINCE BRK % (W)", color="#00E5FF", font_size="11px"),
                rx.text(S.pct_live_w_sort_arrow, color="#00E5FF", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=S.toggle_sort_pct_live_w,
            ),
            color="white",
        ),
    )
    body = rx.table.body(
        rx.foreach(
            S.results,
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
                        on_click=S.open_tradingview(r["symbol"]),
                        width="100%",
                    ),
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(
                        r.get("setup_score_ui", "—"),
                        color=r.get("setup_score_color", "#D1D1D1"),
                        font_weight="bold",
                    ),
                    font_size="12px",
                    padding_y="0",
                ),
                rx.table.cell(r.get("ltp", "—"), color=r.get("chp_color", "#D1D1D1"), font_size="12px", padding_y="0"),
                rx.table.cell(r.get("chp", "—"), color=r.get("chp_color", "#D1D1D1"), font_size="11px", padding_y="0"),
                rx.table.cell(
                    rx.text(r.get("rs_rating", "—"), color=r.get("rs_rating_color", "#D1D1D1"), font_weight="bold"),
                    font_size="12px",
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
                        f"{r.get('last_tag_w', '—')} / {r.get('timing_last_tag_w', '—')}",
                        color=r.get("last_tag_color_w", "#888888"),
                    ),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("timing_last_event_dt_w", "—"), color="#E0E0E0", font_size="10px"),
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(
                        r.get("brk_move_live_pct_w", "—"),
                        color=r.get("brk_move_live_color_w", "#666666"),
                        font_weight="bold",
                        font_size="10px",
                    ),
                    padding_y="0",
                ),
                height="34px",
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
        _pagination(S),
        width="100%",
        flex="1",
        overflow_y="auto",
        padding="0",
        spacing="0",
    )
