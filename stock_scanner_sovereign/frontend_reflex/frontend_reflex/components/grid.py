import reflex as rx
from ..state import State

_PROFILE_TABS = ["ALL", "ELITE", "LEADER", "RISING", "LAGGARD", "FADING", "BASELINE"]

# Compact table: Radix Table uses --table-cell-padding (large by default); we override on table.root.
_TC = {"padding_x": "2px", "padding_y": "0px", "line_height": "1.15"}
_TH = {**_TC, "font_size": "11px"}
_TD = {**_TC, "font_size": "11px"}
_TABLE_COMPACT_STYLE = {
    "table_layout": "fixed",
    "width": "100%",
    "border_collapse": "collapse",
    "border_spacing": "0",
    "--table-cell-padding": "0 1px",
}


def _col_style(width: str, ellipsis: bool = True) -> dict:
    """Fixed column width under table-layout:fixed; optional ellipsis when text overflows."""
    d = {"width": width, "max_width": width, "min_width": "0"}
    if ellipsis:
        d.update(
            {
                "overflow": "hidden",
                "text_overflow": "ellipsis",
                "white_space": "nowrap",
            }
        )
    return d


# Fixed widths for every column (table-layout:fixed). Percentages sum to 100% so no stray “air” in one column.
_COL = {
    "ticker": _col_style("22%"),
    "price": _col_style("7%"),
    "chg": _col_style("5%"),
    "rt": _col_style("5%"),
    "wmrs": _col_style("7%"),
    "prev": _col_style("7%"),
    "dmrs": _col_style("7%"),
    "rvol": _col_style("7%"),
    "brk": _col_style("6%"),
    "prf": _col_style("6%"),
    "rcvr": _col_style("5%"),
    "status": _col_style("15%"),
}


def data_grid():
    return rx.vstack(
        rx.vstack(
            rx.hstack(
                rx.input(
                    placeholder="Search Symbol…",
                    on_change=State.set_search_query,
                    size="1",
                    width="160px",
                    border="1px solid #2a2a2a",
                    bg="#0d0d0d",
                    color="white",
                    _focus={"border_color": "#FFB000", "box_shadow": "0 0 0 1px rgba(255,176,0,0.25)"},
                ),
                rx.select(
                    ["ALL", "BUY NOW", "TRENDING", "NOT TRENDING"],
                    value=State.filter_status,
                    on_change=State.set_filter_status,
                    color="white",
                    bg="#111111",
                    border="1px solid #333",
                    size="1",
                    width="120px",
                ),
                rx.select(
                    ["ALL", "0.5", "1.0", "1.5", "2.0", "3.0"],
                    value=State.filter_mrs,
                    on_change=State.set_filter_mrs,
                    color="white",
                    bg="#111111",
                    border="1px solid #333",
                    size="1",
                    width="72px",
                ),
                rx.select(
                    ["ALL", "1.5", "2.0", "3.0", "5.0"],
                    value=State.filter_rv,
                    on_change=State.set_filter_rv,
                    color="white",
                    bg="#111111",
                    border="1px solid #333",
                    size="1",
                    width="80px",
                ),
                rx.select(
                    ["ALL", "Below0↑"],
                    value=State.filter_mrs_rcvr,
                    on_change=State.set_filter_mrs_rcvr,
                    color="white",
                    bg="#111111",
                    border="1px solid #333",
                    size="1",
                    width="88px",
                ),
                rx.button(
                    "EXPORT EXCEL",
                    on_click=State.download_excel,
                    size="1",
                    bg="#00FF00",
                    color="black",
                    font_weight="bold",
                    _hover={"bg": "#00CC00"},
                ),
                width="100%",
                padding="8px 6px 4px 6px",
                align_items="center",
                spacing="3",
                justify_content="start",
                flex_wrap="wrap",
            ),
            rx.hstack(
                rx.text("PROFILE", font_size="10px", color="#888888", margin_right="6px", align_self="center"),
                rx.foreach(
                    _PROFILE_TABS,
                    lambda p: rx.button(
                        p,
                        size="1",
                        variant="outline",
                        height="26px",
                        min_width="52px",
                        font_size="11px",
                        padding_x="6px",
                        on_click=lambda: State.set_filter_profile(p),
                        cursor="pointer",
                        border_color=rx.cond(State.filter_profile == p, "#FFB000", "#333333"),
                        color=rx.cond(State.filter_profile == p, "#FFB000", "#888888"),
                        bg=rx.cond(State.filter_profile == p, "rgba(255,176,0,0.12)", "transparent"),
                        _hover={"border_color": "#666666"},
                    ),
                ),
                width="100%",
                padding="4px 6px 8px 6px",
                align_items="center",
                spacing="2",
                flex_wrap="wrap",
                border_bottom="1px solid #2a2a2a",
            ),
            spacing="0",
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("TICKER", color="white", **_TH, **_COL["ticker"]),
                    rx.table.column_header_cell("PRICE", color="white", **_TH, **_COL["price"]),
                    rx.table.column_header_cell("CHG%", color="white", **_TH, **_COL["chg"]),
                    rx.table.column_header_cell(
                        rx.hstack(
                            rx.text("RT", color="white"),
                            rx.text(State.grid_sort_arrow_rs, color="#FFB000", font_size="9px"),
                            spacing="1",
                            align_items="center",
                            cursor="pointer",
                            on_click=lambda: State.toggle_grid_sort("rs_rating"),
                        ),
                        **_TH,
                        **_COL["rt"],
                    ),
                    rx.table.column_header_cell(
                        rx.hstack(
                            rx.text("W_mRS", color="white"),
                            rx.text(State.grid_sort_arrow_mrs, color="#FFB000", font_size="9px"),
                            spacing="1",
                            align_items="center",
                            cursor="pointer",
                            on_click=lambda: State.toggle_grid_sort("mrs"),
                        ),
                        **_TH,
                        **_COL["wmrs"],
                    ),
                    rx.table.column_header_cell("Prev", color="white", **_TH, **_COL["prev"]),
                    rx.table.column_header_cell(
                        rx.hstack(
                            rx.text("D_mRS", color="white"),
                            rx.text(State.grid_sort_arrow_dmrs, color="#FFB000", font_size="9px"),
                            spacing="1",
                            align_items="center",
                            cursor="pointer",
                            on_click=lambda: State.toggle_grid_sort("mrs_daily"),
                        ),
                        **_TH,
                        **_COL["dmrs"],
                    ),
                    rx.table.column_header_cell(
                        rx.hstack(
                            rx.text("RVOL", color="white"),
                            rx.text(State.grid_sort_arrow_rv, color="#FFB000", font_size="9px"),
                            spacing="1",
                            align_items="center",
                            cursor="pointer",
                            on_click=lambda: State.toggle_grid_sort("rv"),
                        ),
                        **_TH,
                        **_COL["rvol"],
                    ),
                    rx.table.column_header_cell("BRK", color="white", **_TH, **_COL["brk"]),
                    rx.table.column_header_cell("PRF", color="white", **_TH, **_COL["prf"]),
                    rx.table.column_header_cell("STATUS", color="white", **_TH, **_COL["status"]),
                ),
                background_color="#0a0a4a",
                style={"position": "sticky", "top": 0, "z_index": 4},
            ),
            rx.table.body(
                rx.foreach(
                    State.paginated_results,
                    lambda r: rx.table.row(
                        rx.table.cell(
                            rx.box(
                                rx.text(r["symbol"], title=r["symbol"]),
                                cursor="pointer",
                                text_decoration="underline",
                                _hover={"color": "#00E5FF"},
                                on_click=State.open_tradingview(r["symbol"]),
                            ),
                            color="#FFB000",
                            font_weight="bold",
                            **_TD,
                            **_COL["ticker"],
                        ),
                        rx.table.cell(
                            rx.text(r["ltp"], title=r["ltp"]),
                            color=rx.cond(
                                r["chg_up"],
                                "#00FF00",
                                rx.cond(r["chg_down"], "#FF3131", "#D1D1D1"),
                            ),
                            **_TD,
                            **_COL["price"],
                        ),
                        rx.table.cell(
                            rx.text(
                                r["p1d"],
                                color=rx.cond(
                                    r["chg_up"],
                                    "#00FF00",
                                    rx.cond(r["chg_down"], "#FF3131", "#D1D1D1"),
                                ),
                                font_size="11px",
                                title=r["p1d"],
                            ),
                            **_TD,
                            **_COL["chg"],
                        ),
                        rx.table.cell(
                            rx.text(r["rs_rating"], title=r["rs_rating"]),
                            color="#FFB000",
                            **_TD,
                            **_COL["rt"],
                        ),
                        rx.table.cell(
                            rx.text(r["mrs_str"], color=rx.cond(r["mrs_up"], "#00FF00", "#FF3131"), title=r["mrs_str"]),
                            **_TD,
                            **_COL["wmrs"],
                        ),
                        rx.table.cell(
                            rx.text(r["mrs_prev_day_str"], title=r["mrs_prev_day_str"]),
                            color="#AAAAAA",
                            **_TD,
                            **_COL["prev"],
                        ),
                        rx.table.cell(
                            rx.text(r["mrs_daily_str"], color=rx.cond(r["mrs_daily_up"], "#00FF00", "#FF3131"), title=r["mrs_daily_str"]),
                            **_TD,
                            **_COL["dmrs"],
                        ),
                        rx.table.cell(
                            rx.text(
                                f"{r['rv']}x",
                                color=rx.cond(r["rv_up"], "#00FF00", rx.cond(r["rv_down"], "#FF3131", "#D1D1D1")),
                            ),
                            **_TD,
                            **_COL["rvol"],
                        ),
                        rx.table.cell(
                            rx.text(r["brk_lvl_str"], title=r["brk_lvl_str"]),
                            color="#D1D1D1",
                            **_TD,
                            **_COL["brk"],
                        ),
                        rx.table.cell(
                            rx.text(r["profile"], title=r["profile"]),
                            color="#666666",
                            **_TD,
                            **_COL["prf"],
                        ),
                        rx.table.cell(
                            rx.text(
                                r["status"],
                                title=r["status"],
                                color=rx.cond(
                                    r["status"] == "BUY NOW",
                                    "#00FF00",
                                    rx.cond(
                                        r["status"] == "TRENDING",
                                        "#88FFAA",
                                        rx.cond(r["status"] == "NOT TRENDING", "#FF6666", "#D1D1D1"),
                                    ),
                                ),
                            ),
                            **_TD,
                            **_COL["status"],
                        ),
                        height="18px",
                        min_height="18px",
                        padding="0",
                        line_height="1.15",
                        border_bottom="1px solid #111111",
                        _hover={"background_color": "rgba(255,255,255,0.04)"},
                    ),
                )
            ),
            width="100%",
            variant="surface",
            style=_TABLE_COMPACT_STYLE,
        ),
        rx.hstack(
            rx.button("PREV", on_click=State.prev_page, size="1", variant="outline", color_scheme="gray", disabled=State.current_page == 1),
            rx.text(f"PAGE {State.current_page} / {State.total_pages}", size="1", color="#D1D1D1"),
            rx.button("NEXT", on_click=State.next_page, size="1", variant="outline", color_scheme="gray", disabled=State.current_page == State.total_pages),
            spacing="4",
            padding="10px",
            width="100%",
            justify_content="center",
            border_top="1px solid #333333",
        ),
        width="100%",
        flex="1",
        min_height="0",
        overflow_y="auto",
        padding="0",
        spacing="0",
    )
