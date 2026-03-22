import reflex as rx
from ..state import State
from utils.constants import DASHBOARD_BENCHMARK_MAP, UNIVERSE_OPTIONS
def universe_panel():
    return rx.vstack(
        rx.text("SECURITIES / UNIVERSE", size="1", color="#D1D1D1", font_weight="bold", padding="10px 15px"),
        rx.vstack(
            rx.foreach(UNIVERSE_OPTIONS, lambda u: rx.button(
                u, on_click=lambda: State.set_universe(u), variant="ghost",
                color=rx.cond(State.universe == u, "#FFB000", "#D1D1D1"), width="100%", text_align="left",
                justify_content="start", padding_x="15px", height="30px", font_size="12px",
                font_weight=rx.cond(State.universe == u, "bold", "normal"),
                background_color=rx.cond(State.universe == u, "rgba(255,176,0,0.1)", "transparent"),
                _hover={"background_color": "rgba(255,255,255,0.05)"}
            )), width="100%", spacing="0"
        ), 
        rx.button("SIDECAR STRATEGY", on_click=lambda: rx.redirect("/breakout"), variant="ghost", color="#FFB000", width="100%", text_align="left", justify_content="start", padding_x="15px", height="35px"),
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
