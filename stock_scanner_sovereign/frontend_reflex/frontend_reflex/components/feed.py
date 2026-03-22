import reflex as rx
from ..state import State
def elite_alpha_feed():
    return rx.box(
        rx.hstack(
            rx.foreach(State.alpha_signals, lambda r: rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text(r["symbol"], font_weight="bold", color="#FFB000", font_size="14px"),
                        rx.spacer(),
                        rx.badge(r["profile"], color_scheme="green", variant="solid", font_size="10px"),
                    ),
                    rx.hstack(
                        rx.text(r["ltp"], font_size="18px", font_weight="bold", color="#00FF00"),
                        rx.spacer(),
                        rx.vstack(
                            rx.text(f"RS {r['rs_rating']}", font_size="11px", color="white"),
                            rx.text(f"mRS {r['mrs_str']}", font_size="11px", color=rx.cond(r["mrs_up"], "#00FF00", "#FF3131")),
                            spacing="0", align_items="end"
                        ),
                    ),
                    spacing="2", align_items="stretch"
                ),
                padding="12px", border="1px solid #333333", background_color="#111111",
                border_radius="4px", min_width="220px", flex="1", box_shadow="0 4px 6px rgba(0,0,0,0.3)"
            )),
            spacing="4", width="100%", overflow_x="auto", padding="15px"
        ),
        width="100%", border_bottom="1px solid #333333", background_color="#000000"
    )
