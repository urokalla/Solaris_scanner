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
            width="100%", padding="10px", border_bottom="1px solid #333333", background_color="#000080"
        ), spacing="0", width="100%"
    )
def breakout_sidebar():
    options = ["Nifty 50", "Nifty 100", "Nifty 500", "All NSE Stocks"]
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
        ), width="100%", height="100%", border_right="1px solid #333333", background_color="#000000"
    )
