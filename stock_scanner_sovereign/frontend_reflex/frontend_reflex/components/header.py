import reflex as rx
from ..state import State
from .ticker import ticker_tape
def terminal_header():
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("SOLARIS • RS SCANNER", size="4", color="#00FF00", font_weight="bold"),
                rx.text("READY", size="1", color="#D1D1D1"),
                align_items="start", spacing="0"
            ),
            rx.spacer(),
            rx.vstack(
                rx.text("BENCHMARK", size="1", color="#D1D1D1", font_weight="bold"),
                rx.hstack(
                    rx.text(State.benchmark_name, color="#FFB000", font_weight="bold", font_size="14px"),
                    rx.text(State.benchmark_ltp, color="#00FF00", font_weight="bold", font_size="14px"),
                    rx.text(State.benchmark_change, color=rx.cond(State.benchmark_is_up, "#00FF00", "#FF3131"), font_size="12px"),
                    spacing="2", align_items="center"
                ),
                align_items="end", spacing="0"
            ),
            width="100%", padding="10px", border_bottom="1px solid #333333", background_color="#000000"
        ),
        ticker_tape(), spacing="0", width="100%"
    )
