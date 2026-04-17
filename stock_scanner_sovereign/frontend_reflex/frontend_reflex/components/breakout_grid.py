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
        height="96px",
        border_bottom="1px solid #333333",
        background_color="#000000",
        overflow="hidden",
    )


def breakout_data_grid():
    header_row = rx.table.row(
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("SIDECAR", color="white"),
                rx.text(BreakoutState.symbol_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_symbol,
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
                rx.text("BRK_LVL", color="white"),
                rx.text(BreakoutState.brk_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_brk,
            ),
            color="white",
        ),
        rx.table.column_header_cell(rx.text("BRK_W", color="white")),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("D/W EMA", color="white"),
                rx.text(BreakoutState.tf_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_tf,
            ),
            color="white",
        ),
        rx.table.column_header_cell("TREND", color="white"),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("mRS (W)", color="white"),
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
                rx.text("MRS STATUS", color="white"),
                rx.text(BreakoutState.mrs_grid_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_mrs_grid,
            ),
            color="white",
        ),
        rx.table.column_header_cell("RVCR", color="white"),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("Mn RSI2", color="white"),
                rx.text(BreakoutState.mrsi2_sort_arrow, color="#FFB000", font_size="10px"),
                rx.text("*=LTP", color="#666666", font_size="8px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_mrsi2,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("UDAI", color="white"),
                rx.text(BreakoutState.udai_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_udai,
            ),
            color="white",
        ),
        rx.table.column_header_cell(
            rx.hstack(
                rx.text("BRK STAGE", color="white"),
                rx.text(BreakoutState.stage_sort_arrow, color="#FFB000", font_size="10px"),
                spacing="1",
                align_items="center",
                cursor="pointer",
                on_click=BreakoutState.toggle_sort_stage,
            ),
            color="white",
        ),
    )
    body = rx.table.body(
        rx.foreach(
            BreakoutState.paginated_results,
            lambda r: rx.table.row(
                rx.table.cell(
                    rx.hstack(
                        rx.box(
                            r["symbol"],
                            color="#FFB000",
                            font_weight="bold",
                            font_size="12px",
                            cursor="pointer",
                            text_decoration="underline",
                            _hover={"color": "#00E5FF"},
                            on_click=BreakoutState.open_tradingview(r["symbol"]),
                            flex="1",
                            min_width="0",
                            overflow="hidden",
                        ),
                        rx.text(
                            "sc",
                            font_size="9px",
                            color="#00E5FF",
                            font_weight="bold",
                            cursor="pointer",
                            flex_shrink="0",
                            title="Screener.in — fundamentals",
                            _hover={"text_decoration": "underline"},
                            on_click=BreakoutState.open_screener_in(r["symbol"]),
                        ),
                        rx.text(
                            "i",
                            font_size="9px",
                            color="#888888",
                            cursor="pointer",
                            flex_shrink="0",
                            title="Sidecar snapshot",
                            _hover={"text_decoration": "underline"},
                            on_click=BreakoutState.sidecar_snapshot_alert(
                                r["symbol"],
                                r["ltp"],
                                r["chp"],
                                r["brk_lvl"],
                                r["mrs_weekly"],
                                r["trend_text"],
                                r["status"],
                                r.get("mrs_grid_status", "—"),
                            ),
                        ),
                        spacing="2",
                        align_items="center",
                        width="100%",
                    ),
                    padding_y="0",
                ),
                rx.table.cell(r["ltp"], color=r["chp_color"], font_size="12px", padding_y="0"),
                rx.table.cell(rx.text(r["chp"], color=r["chp_color"]), font_size="12px", padding_y="0"),
                rx.table.cell(r["brk_lvl"], color="#D1D1D1", font_size="12px", padding_y="0"),
                rx.table.cell(
                    rx.text(r.get("brk_lvl_w", "—"), color="#D1D1D1"),
                    font_size="12px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(
                        r.get("tf_ema", "—"),
                        color=rx.cond(
                            r.get("dual_tf_ema_stack_ok", False),
                            "#00FF00",
                            "#888888",
                        ),
                        title=r["ema_stack_tooltip"],
                    ),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(rx.text(r["trend_text"], color=r["trend_color"]), font_size="12px", padding_y="0"),
                rx.table.cell(rx.text(r["mrs_weekly"], color=r["mrs_color"]), font_size="12px", padding_y="0"),
                rx.table.cell(
                    rx.text(r.get("mrs_grid_status", "—"), color=r.get("mrs_grid_status_color", "#D1D1D1")),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(
                        r.get("mrs_rcvr_str", "—"),
                        color=rx.cond(r.get("mrs_rcvr_slope_up", False), "#00FFAA", "#555555"),
                    ),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(
                    rx.text(r.get("m_rsi2_ui", "—"), color=r.get("m_rsi2_color", "#D1D1D1")),
                    font_size="11px",
                    padding_y="0",
                ),
                rx.table.cell(rx.text(r.get("udai_ui", "—"), color="#D1D1D1"), font_size="11px", padding_y="0"),
                rx.table.cell(
                    rx.text(
                        r["status"],
                        color=rx.cond(
                            r["is_breakout"],
                            "#00FF00",
                            rx.cond(r["status"] == "STAGE 1", "#00E5FF", "#FFB000"),
                        ),
                    ),
                    font_size="12px",
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
