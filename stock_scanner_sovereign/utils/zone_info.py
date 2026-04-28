"""
IST / Asia/Kolkata: stdlib `zoneinfo` (Python 3.9+), or `backports.zoneinfo` on 3.8.
"""
try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore

__all__ = ("ZoneInfo",)
