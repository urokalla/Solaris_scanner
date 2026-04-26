import reflex as rx
from ..breakout_state import BreakoutState


def breakout_alpha_feed():
    return rx.box(
        rx.hstack(
            rx.cond(
                BreakoutState.alpha_breakouts.length() == 0,
                rx.text(
                    "WAITING FOR BREAKOUT SIGNALS...",
                    color="#333333",
                    font_size="12px",
                    padding="20px",
                ),
                rx.foreach(
                    BreakoutState.alpha_breakouts,
                    lambda r: rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.text(
                                    r["symbol"],
                                    font_weight="bold",
                                    color="#FFB000",
                                    font_size="14px",
                                    cursor="pointer",
                                    text_decoration="underline",
                                    _hover={"color": "#00E5FF"},
                                    on_click=BreakoutState.open_tradingview(r["symbol"]),
                                ),
                                rx.text(
                                    "sc",
                                    font_size="10px",
                                    color="#00E5FF",
                                    font_weight="bold",
                                    cursor="pointer",
                                    margin_left="6px",
                                    on_click=BreakoutState.open_screener_in(r["symbol"]),
                                ),
                                rx.spacer(),
                                rx.badge("🔥 BREAKOUT", color_scheme="green", variant="solid", font_size="10px"),
                            ),
                            rx.hstack(
                                rx.text(r["ltp"], font_size="18px", font_weight="bold", color="#00FF00"),
                                rx.spacer(),
                                rx.vstack(
                                    rx.text(f"LIMIT {r['brk_lvl']}", font_size="11px", color="white"),
                                    rx.text(f"STOP {r['stop_price']}", font_size="11px", color="#FF3131"),
                                    rx.hstack(
                                        rx.text(f"RVOL {r.get('rv', '—')}", font_size="10px", color=r.get("rv_color", "#D1D1D1")),
                                        rx.text(f"W_MRS {r.get('mrs_weekly', '—')}", font_size="10px", color=r.get("mrs_color", "#D1D1D1")),
                                        spacing="8px",
                                    ),
                                    spacing="0",
                                    align_items="end",
                                ),
                            ),
                            spacing="2",
                            align_items="stretch",
                        ),
                        padding="12px",
                        border="1px solid #333333",
                        background_color="#111111",
                        border_radius="4px",
                        min_width="220px",
                        flex="1",
                        box_shadow="0 4px 6px rgba(0,0,0,0.3)",
                    ),
                ),
            ),
            spacing="4",
            width="100%",
            overflow_x="auto",
            padding="15px",
        ),
        width="100%",
        min_height="112px",
        border_bottom="1px solid #333333",
        background_color="#000000",
        overflow="hidden",
    )


def breakout_data_grid():
    header_row = rx.table.row(
        rx.table.column_header_cell(rx.hstack(rx.text("SYMBOL", color="white"), rx.text(BreakoutState.symbol_sort_arrow, color="#FFB000", font_size="10px"), spacing="1", align_items="center", cursor="pointer", on_click=BreakoutState.toggle_sort_symbol), color="white"),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("SCORE", color="white"),
                rx.text(BreakoutState.setup_score_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_setup_score,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("PRICE", color="white"),
                rx.text(BreakoutState.ltp_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_ltp,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("CHG%", color="white"),
                rx.text(BreakoutState.chp_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_chp,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("RS", color="white"),
                rx.text(BreakoutState.rs_rating_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_rs_rating,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("RVOL", color="white"),
                rx.text(BreakoutState.rvol_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_rvol,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("W_MRS", color="white"),
                rx.text(BreakoutState.wmrs_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_wmrs,
            ),
            color="white",
        ),
        rx.table.column_header_cell(rx.text("W_ATR9x2", color="white")),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("STATE D", color="white"),
                rx.text(BreakoutState.stage_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_stage,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("LAST TAG D", color="white"),
                rx.text(BreakoutState.brk_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_brk,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.vstack(
                rx.text("% FROM B (D)", color="white", font_size="11px"),
                rx.text("close → LTP", color="#888888", font_size="9px"),
                spacing="0",
                align_items="start",
            ),
        ),
        rx.table.column_header_cell(rx.text("LAST TAG W", color="white")),
        rx.table.column_header_cell(
            rx.vstack(
                rx.text("% FROM B (W)", color="white", font_size="11px"),
                rx.text("close → LTP", color="#888888", font_size="9px"),
                spacing="0",
                align_items="start",
            ),
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("B# D/W", color="white"),
                rx.text(BreakoutState.tf_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_tf,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("E9CT# D/W", color="white"),
                rx.text(BreakoutState.mrs_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_mrs,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("E21C# D/W", color="white"),
                rx.text(BreakoutState.mrsi2_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_mrsi2,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("RST D/W", color="white"),
                rx.text(BreakoutState.stage_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_stage,
            ),
            color="white",
        ),
        rx.table.column_header_cell(rx.text("AGE D/W", color="white")),
    )
    body = rx.table.body(
        rx.foreach(
            BreakoutState.paginated_results,
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
                        on_click=BreakoutState.open_tradingview(r["symbol"]),
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
                rx.table.cell(r["ltp"], color=r["chp_color"], font_size="12px", padding_y="0"),
                rx.table.cell(
                    rx.text(r.get("chp", "—"), color=r.get("chp_color", "#D1D1D1")),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("rs_rating", "—"), color=r.get("rs_rating_color", "#D1D1D1"), font_weight="bold"),
                    font_size="12px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("rv", "—"), color=r.get("rv_color", "#D1D1D1")),
                    font_size="12px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("mrs_weekly", "—"), color=r.get("mrs_color", "#D1D1D1")),
                    font_size="12px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("atr9x2_state", "—"), color=r.get("atr9x2_color", "#D1D1D1"), font_weight="bold"),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.vstack(
                        rx.text(r.get("state_name", "LOCKED"), color="#D1D1D1", font_size="12px"),
                        rx.text(
                            r.get("post_rst_hint_d", ""),
                            color="#FFB000",
                            font_size="9px",
                            font_weight="bold",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
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
                    rx.vstack(
                        rx.text(
                            r.get("brk_move_pct", "—"),
                            color=r.get("brk_move_color", "#D1D1D1"),
                            font_weight="bold",
                            font_size="11px",
                        ),
                        rx.text(
                            r.get("brk_b_anchor_dt", "—"),
                            color="#888888",
                            font_size="9px",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.vstack(
                        rx.text(
                            r.get("last_tag_w", "—"),
                            color=r.get("last_tag_color_w", "#888888"),
                            font_size="11px",
                        ),
                        rx.text(
                            r.get("post_rst_hint_w", ""),
                            color="#FFB000",
                            font_size="9px",
                            font_weight="bold",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.vstack(
                        rx.text(
                            r.get("brk_move_pct_w", "—"),
                            color=r.get("brk_move_color_w", "#D1D1D1"),
                            font_weight="bold",
                            font_size="11px",
                        ),
                        rx.text(
                            r.get("brk_b_anchor_dt_w", "—"),
                            color="#888888",
                            font_size="9px",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    padding_y="0",
                ),
                rx.table.cell(rx.text(f"{r.get('b_count', 0)}/{r.get('b_count_w', 0)}"), font_size="11px", padding_y="0"),
                rx.table.cell(rx.text(f"{r.get('e9t_count', 0)}/{r.get('e9t_count_w', 0)}"), font_size="11px", padding_y="0"),
                rx.table.cell(rx.text(f"{r.get('e21c_count', 0)}/{r.get('e21c_count_w', 0)}"), font_size="11px", padding_y="0"),
                rx.table.cell(rx.text(f"{r.get('rst_count', 0)}/{r.get('rst_count_w', 0)}"), font_size="11px", padding_y="0"),
                rx.table.cell(
                    rx.text(f"{r.get('age_mins', '—')} / {r.get('age_mins_w', '—')}"),
                    font_size="11px",
                    padding_y="0",
                ),
                height="25px",
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
                on_click=BreakoutState.prev_page,
                size="1",
                variant="outline",
                color_scheme="gray",
                disabled=BreakoutState.current_page == 1,
            ),
            rx.text(
                f"PAGE {BreakoutState.current_page} / {BreakoutState.total_pages}",
                size="1",
                color="#D1D1D1",
            ),
            rx.button(
                "NEXT",
                on_click=BreakoutState.next_page,
                size="1",
                variant="outline",
                color_scheme="gray",
                disabled=BreakoutState.current_page == BreakoutState.total_pages,
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
