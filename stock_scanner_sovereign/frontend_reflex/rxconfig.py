import os

import reflex as rx

# Browser must reach this host:port for WebSocket + state (not "localhost" inside the container).
# Docker: set API_URL in compose (e.g. http://127.0.0.1:8000 same machine, or http://YOUR_LAN_IP:8000 from phone/another PC).
_api = (os.getenv("REFLEX_API_URL") or os.getenv("API_URL") or "http://localhost:8000").strip()

config = rx.Config(
    app_name="frontend_reflex",
    api_url=_api,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)