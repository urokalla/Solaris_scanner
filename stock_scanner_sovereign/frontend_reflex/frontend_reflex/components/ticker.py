import reflex as rx
from ..state import State
def ticker_tape():
    return rx.box(
        rx.hstack(
            rx.foreach(
                State.pulse_data,
                lambda item: rx.hstack(
                    rx.text(item["symbol"], font_weight="bold", color="#D1D1D1", font_size="10px"),
                    rx.text(item["ltp"], font_weight="bold", color="#888888", font_size="10px"),
                    rx.text(
                        item["p1d"],
                        color=rx.cond(item["chg_up"], "#00FF00", rx.cond(item["chg_down"], "#FF3131", "#888888")),
                        font_size="10px",
                        font_weight="bold",
                    ),
                    padding_right="25px", spacing="2"
                )
            ),
            spacing="4", padding="4px 10px", align_items="center",
        ),
        width="100%", background_color="#000000", border_bottom="1px solid #222222", overflow_x="hidden", white_space="nowrap"
    )
