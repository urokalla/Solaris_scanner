import reflex as rx
from ..breakout_state import BreakoutState
def breakout_header():
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("SOLARIS • BREAKOUT STRATEGY", size="4", color="#00FF00", font_weight="bold"),
                rx.text("ISOLATED SIDECAR ENGINE", size="1", color="#D1D1D1"),
                align_items="start", spacing="0"
            ),
            rx.spacer(),
            rx.vstack(
                rx.text("ENGINE STATUS", size="1", color="#D1D1D1", font_weight="bold"),
                rx.hstack(
                    rx.text(BreakoutState.status_message, color="#FFB000", font_weight="bold", font_size="14px"),
                    rx.text(f"{BreakoutState.result_count} SYMBOLS", color="#00FF00", font_weight="bold", font_size="12px"),
                    spacing="2", align_items="center"
                ),
                align_items="end", spacing="0"
            ),
            width="100%", padding="10px", border_bottom="1px solid #333333", background_color="#000000"
        ), spacing="0", width="100%"
    )
def breakout_sidebar():
    options = ["Nifty 50", "Nifty 100", "Nifty 500", "All NSE Stocks"]
    brk_options = [
        "ALL",
        "BUY NOW",
        "BREAKOUT",
        "NEAR BRK",
        "STAGE 2",
        "STAGE 4",
        "N.A.",
    ]
    return rx.vstack(
        rx.text("TACTICAL / UNIVERSE", size="1", color="#D1D1D1", font_weight="bold", padding="10px 15px"),
        rx.vstack(
            rx.foreach(options, lambda u: rx.button(
                u, on_click=lambda: BreakoutState.set_universe(u), variant="ghost",
                color=rx.cond(BreakoutState.universe == u, "#FFB000", "#D1D1D1"), width="100%", text_align="left",
                justify_content="start", padding_x="15px", height="30px", font_size="12px",
                font_weight=rx.cond(BreakoutState.universe == u, "bold", "normal"),
                background_color=rx.cond(BreakoutState.universe == u, "rgba(255,176,0,0.1)", "transparent"),
                _hover={"background_color": "rgba(255,255,255,0.05)"}
            )), width="100%", spacing="0"
        ),
        rx.box(height="8px"),
        rx.text("FILTERS", size="1", color="#D1D1D1", font_weight="bold", padding="8px 15px 4px 15px"),
        rx.vstack(
            rx.text("Symbol contains", size="1", color="#888888", padding_left="15px"),
            rx.input(
                placeholder="e.g. RELIANCE",
                on_change=BreakoutState.set_search_query,
                size="1",
                width="100%",
                max_width="260px",
                margin_left="15px",
                margin_right="15px",
                border="1px solid #333333",
                bg="#111111",
                color="white",
                height="32px",
                font_size="12px",
                _focus={"border_color": "#FFB000"},
            ),
            rx.text("BRK STAGE", size="1", color="#888888", padding_top="8px", padding_left="15px"),
            rx.select(
                brk_options,
                value=BreakoutState.filter_brk_stage,
                on_change=BreakoutState.set_filter_brk_stage,
                color="white",
                bg="#111111",
                border="1px solid #333333",
                size="1",
                width="100%",
                max_width="260px",
                margin_left="15px",
                margin_right="15px",
                height="32px",
            ),
            spacing="1",
            width="100%",
        ),
        width="100%", height="100%", border_right="1px solid #333333", background_color="#000000"
    )
