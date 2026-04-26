import reflex as rx
from ..state import State
from utils.constants import DASHBOARD_BENCHMARK_MAP, DASHBOARD_SECTOR_OPTIONS, UNIVERSE_OPTIONS
def universe_panel():
    return rx.vstack(
        rx.text("SECURITIES / UNIVERSE", size="1", color="#D1D1D1", font_weight="bold", padding="10px 15px"),
        rx.box(
            rx.select(
                UNIVERSE_OPTIONS,
                value=State.universe,
                on_change=State.set_universe,
                position="popper",
                color="white",
                bg="#111111",
                border="1px solid #333333",
                size="1",
                width="100%",
                height="32px",
                font_size="12px",
                _focus={"border_color": "#FFB000"},
            ),
            width="100%",
            padding_x="15px",
        ),
        rx.text("SECTOR (SCREENER)", size="1", color="#D1D1D1", font_weight="bold", padding="10px 15px 4px 15px"),
        rx.box(
            rx.select(
                DASHBOARD_SECTOR_OPTIONS,
                value=State.dashboard_sector,
                on_change=State.set_dashboard_sector,
                position="popper",
                color="white",
                bg="#111111",
                border="1px solid #333333",
                size="1",
                width="100%",
                height="32px",
                font_size="12px",
                _focus={"border_color": "#00E5FF"},
            ),
            width="100%",
            padding_x="15px",
        ),
        rx.text(
            "Universe ∩ sector; picks sort by W_mRS (high→low) so the top row is strongest in that sector vs benchmark.",
            size="1",
            color="#888888",
            padding="4px 15px 8px 15px",
        ),
        rx.button("SIDECAR STRATEGY", on_click=State.open_sidecar_full_universe, variant="ghost", color="#FFB000", width="100%", text_align="left", justify_content="start", padding_x="15px", height="35px"),
        rx.button("SIDECAR BREAKOUT CLOCK", on_click=State.open_breakout_timing_full_universe, variant="ghost", color="#00E5FF", width="100%", text_align="left", justify_content="start", padding_x="15px", height="35px"),
        rx.button("SIDECAR INSIDER", on_click=lambda: rx.redirect("/insider", is_external=True), variant="ghost", color="#7CFC00", width="100%", text_align="left", justify_content="start", padding_x="15px", height="35px"),
        rx.button("SIDECAR EVENTS", on_click=lambda: rx.redirect("/events", is_external=True), variant="ghost", color="#00E5FF", width="100%", text_align="left", justify_content="start", padding_x="15px", height="35px"),
        width="100%", background_color="#000000", padding_bottom="10px"
    )
def benchmark_panel():
    return rx.vstack(
        rx.text("VALIDATION / BENCHMARK", size="1", color="#D1D1D1", font_weight="bold", padding="10px 15px"),
        rx.vstack(
            rx.foreach(list(DASHBOARD_BENCHMARK_MAP.keys()), lambda b: rx.button(
                b, on_click=lambda: State.set_benchmark(b), variant="ghost",
                color=rx.cond(State.benchmark_name == b, "#00FF00", "#D1D1D1"), width="100%", text_align="left",
                justify_content="start", padding_x="15px", height="30px", font_size="12px",
                font_weight=rx.cond(State.benchmark_name == b, "bold", "normal"),
                background_color=rx.cond(State.benchmark_name == b, "rgba(0,255,0,0.1)", "transparent"),
                _hover={"background_color": "rgba(255,255,255,0.05)"}
            )), width="100%", spacing="0"
        ), width="100%", border_top="1px solid #333333", background_color="#000000", padding_bottom="10px"
    )
