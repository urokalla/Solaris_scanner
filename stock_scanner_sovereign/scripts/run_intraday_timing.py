#!/usr/bin/env python3
"""
CLI for live CB timing (daily + weekly).

Logic is a verbatim copy of backend/breakout_logic.py (helpers + _update_live_timing_breakout_status).
Re-embed when that function changes. This file stays import-light so it runs on older Python too.

Example:
  python scripts/run_intraday_timing.py --ltp 1520 --brk 1500 --last-tag B2
  python scripts/run_intraday_timing.py --at "2026-04-24T15:31" --ltp 1520 --brk 1500 \\
      --cb-pending-day-d 2026-04-24 --cb-pending-tag-d CBBUY --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# India has no DST; fixed offset avoids zoneinfo / backports on older Python.
_IST = timezone(timedelta(hours=5, minutes=30))
TAG_ET9_WAIT_F21C = "ET9DNWF21C"


def _cbuy_tag(idx: int) -> str:
    n = max(1, int(idx))
    return "CBBUY" if n == 1 else "CB{}BUY".format(n)


def _infer_b_count_from_tag(tag_val: Any) -> int:
    t = str(tag_val or "").strip().upper()
    if not t.startswith("B"):
        return 0
    digits = []
    for ch in t[1:]:
        if ch.isdigit():
            digits.append(ch)
        else:
            break
    if not digits:
        return 1
    try:
        return max(1, int("".join(digits)))
    except Exception:
        return 1


def _timing_state_from_tag(tag_val: str, pending: bool) -> str:
    t = str(tag_val or "").strip().upper()
    if t.startswith("CB"):
        return "LIVE BREAKOUT" if pending else "CONFIRMED BREAKOUT"
    if t.startswith("B"):
        return "POST-BREAKOUT" if "+" in t else "CONFIRMED BREAKOUT"
    if t == TAG_ET9_WAIT_F21C or t.startswith(("E9CT", "E21C", "RST")):
        return "POST-BREAKOUT"
    return "LOCKED"


def _update_live_timing_breakout_status(
    r: dict, ltp: float, now_dt: datetime, quote_event_ts=None
) -> None:
    now_ts = float(now_dt.timestamp())
    try:
        _qts = float(quote_event_ts) if quote_event_ts is not None else 0.0
    except (TypeError, ValueError):
        _qts = 0.0
    cross_ts = _qts if _qts > 0.0 else now_ts
    today = now_dt.date().isoformat()
    cutoff_reached = (now_dt.hour, now_dt.minute) >= (15, 30)
    week_id = "{}-W{:02d}".format(int(now_dt.isocalendar()[0]), int(now_dt.isocalendar()[1]))
    is_weekly_finalize_slot = now_dt.weekday() == 4 and cutoff_reached

    if str(r.get("cb_live_entry_day_d") or "") and str(r.get("cb_live_entry_day_d")) != today:
        r["cb_live_entry_px_d"] = 0.0
        r["cb_live_entry_day_d"] = ""
    if str(r.get("cb_live_entry_week_w") or "") and str(r.get("cb_live_entry_week_w")) != week_id:
        r["cb_live_entry_px_w"] = 0.0
        r["cb_live_entry_week_w"] = ""

    d_brk = float(r.get("brk_lvl") or 0.0)
    d_pending_day = str(r.get("cb_pending_day_d") or "")
    d_pending_tag = str(r.get("cb_pending_tag_d") or "")
    d_pending_ts = float(r.get("cb_pending_ts_d") or 0.0)
    d_last_confirm_day = str(r.get("cb_last_confirm_day_d") or "")
    confirmed_b_count_d = int(r.get("b_count", 0) or 0)
    if confirmed_b_count_d <= 0:
        confirmed_b_count_d = _infer_b_count_from_tag(r.get("last_tag"))
    cb_count_d = int(r.get("cb_count_d", 0) or 0)
    if cb_count_d < confirmed_b_count_d:
        cb_count_d = confirmed_b_count_d
        r["cb_count_d"] = cb_count_d

    if d_brk > 0 and ltp > d_brk and d_pending_day != today and d_last_confirm_day != today:
        d_pending_day = today
        d_pending_tag = _cbuy_tag(max(cb_count_d, confirmed_b_count_d) + 1)
        d_pending_ts = cross_ts
        r["cb_live_entry_px_d"] = float(ltp)
        r["cb_live_entry_day_d"] = today

    if d_pending_day == today and cutoff_reached:
        if d_brk > 0 and ltp > d_brk:
            cb_count_d += 1
            r["cb_count_d"] = cb_count_d
            r["timing_last_tag"] = _cbuy_tag(cb_count_d)
            _fin_d = float(d_pending_ts or 0.0)
            r["timing_last_event_ts"] = _fin_d if _fin_d > 0 else now_ts
            r["cb_last_confirm_day_d"] = today
        d_pending_day = ""
        d_pending_tag = ""
        d_pending_ts = 0.0

    if d_pending_day == today and d_pending_tag:
        r["timing_last_tag"] = d_pending_tag
        r["timing_last_event_ts"] = d_pending_ts if d_pending_ts > 0 else now_ts
    else:
        r.setdefault("timing_last_tag", str(r.get("last_tag") or "—"))
        r.setdefault("timing_last_event_ts", float(r.get("last_event_ts", 0.0) or 0.0))
        if not d_pending_day:
            _ltu = str(r.get("last_tag") or "").strip().upper()
            _cycle_resets_timing = (
                _ltu.startswith("RST")
                or _ltu == TAG_ET9_WAIT_F21C
                or _ltu.startswith(("E9CT", "E21C"))
            )
            if str(r.get("cb_last_confirm_day_d") or "") != today or _cycle_resets_timing:
                r["timing_last_tag"] = str(r.get("last_tag") or "—")
                r["timing_last_event_ts"] = float(r.get("last_event_ts", 0.0) or 0.0)
                r["cb_live_entry_px_d"] = 0.0
                r["cb_live_entry_day_d"] = ""

    r["cb_pending_day_d"] = d_pending_day
    r["cb_pending_tag_d"] = d_pending_tag
    r["cb_pending_ts_d"] = d_pending_ts

    w_brk = float(r.get("brk_lvl_w") or 0.0)
    w_pending_week = str(r.get("cb_pending_week_w") or "")
    w_pending_tag = str(r.get("cb_pending_tag_w") or "")
    w_pending_ts = float(r.get("cb_pending_ts_w") or 0.0)
    w_last_confirm_week = str(r.get("cb_last_confirm_week_w") or "")
    confirmed_b_count_w = int(r.get("b_count_w", 0) or 0)
    if confirmed_b_count_w <= 0:
        confirmed_b_count_w = _infer_b_count_from_tag(r.get("last_tag_w"))
    cb_count_w = int(r.get("cb_count_w", 0) or 0)
    if cb_count_w < confirmed_b_count_w:
        cb_count_w = confirmed_b_count_w
        r["cb_count_w"] = cb_count_w

    if w_brk > 0 and ltp > w_brk and w_pending_week != week_id and w_last_confirm_week != week_id:
        w_pending_week = week_id
        w_pending_tag = _cbuy_tag(max(cb_count_w, confirmed_b_count_w) + 1)
        w_pending_ts = cross_ts
        r["cb_live_entry_px_w"] = float(ltp)
        r["cb_live_entry_week_w"] = week_id

    if w_pending_week == week_id and is_weekly_finalize_slot:
        if w_brk > 0 and ltp > w_brk:
            cb_count_w += 1
            r["cb_count_w"] = cb_count_w
            r["timing_last_tag_w"] = _cbuy_tag(cb_count_w)
            _fin_w = float(w_pending_ts or 0.0)
            r["timing_last_event_ts_w"] = _fin_w if _fin_w > 0 else now_ts
            r["cb_last_confirm_week_w"] = week_id
        w_pending_week = ""
        w_pending_tag = ""
        w_pending_ts = 0.0

    if w_pending_week == week_id and w_pending_tag:
        r["timing_last_tag_w"] = w_pending_tag
        r["timing_last_event_ts_w"] = w_pending_ts if w_pending_ts > 0 else now_ts
    else:
        r.setdefault("timing_last_tag_w", str(r.get("last_tag_w") or "—"))
        r.setdefault("timing_last_event_ts_w", float(r.get("last_event_ts_w", 0.0) or 0.0))
        if not w_pending_week:
            _ltuw = str(r.get("last_tag_w") or "").strip().upper()
            _cycle_resets_timing_w = (
                _ltuw.startswith("RST")
                or _ltuw == TAG_ET9_WAIT_F21C
                or _ltuw.startswith(("E9CT", "E21C"))
            )
            if str(r.get("cb_last_confirm_week_w") or "") != week_id or _cycle_resets_timing_w:
                r["timing_last_tag_w"] = str(r.get("last_tag_w") or "—")
                r["timing_last_event_ts_w"] = float(r.get("last_event_ts_w", 0.0) or 0.0)
                r["cb_live_entry_px_w"] = 0.0
                r["cb_live_entry_week_w"] = ""

    r["cb_pending_week_w"] = w_pending_week
    r["cb_pending_tag_w"] = w_pending_tag
    r["cb_pending_ts_w"] = w_pending_ts


def _parse_at(s: Optional[str]) -> datetime:
    if not s:
        return datetime.now(_IST)
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_IST)
    return dt.astimezone(_IST) if dt.tzinfo != _IST else dt


def main() -> int:
    p = argparse.ArgumentParser(description="Run intraday CB timing update on a mock row dict.")
    p.add_argument("--at", help='IST wall time as ISO, e.g. "2026-04-24T14:05" (default: now IST)')
    p.add_argument("--ltp", type=float, required=True)
    p.add_argument("--brk", type=float, default=0.0, dest="brk_lvl", help="Daily brk_lvl")
    p.add_argument("--brk-w", type=float, default=0.0, dest="brk_lvl_w", help="Weekly brk_lvl_w")
    p.add_argument("--last-tag", default="B1", help="Strategy last_tag (daily)")
    p.add_argument("--last-tag-w", default="", help="Strategy last_tag_w (weekly); default: same as --last-tag")
    p.add_argument("--b-count", type=int, default=0, help="Override b_count; 0 = infer from last_tag")
    p.add_argument("--b-count-w", type=int, default=0, help="Override b_count_w; 0 = infer from last_tag_w")
    p.add_argument("--cb-count-d", type=int, default=0)
    p.add_argument("--cb-count-w", type=int, default=0)
    p.add_argument("--cb-pending-day-d", default="", help="cb_pending_day_d (YYYY-MM-DD)")
    p.add_argument("--cb-pending-tag-d", default="", help="cb_pending_tag_d")
    p.add_argument("--cb-pending-week-w", default="", help="cb_pending_week_w (e.g. 2026-W17)")
    p.add_argument("--cb-pending-tag-w", default="", help="cb_pending_tag_w")
    p.add_argument("--cb-last-confirm-day-d", default="", help="cb_last_confirm_day_d")
    p.add_argument("--cb-last-confirm-week-w", default="", help="cb_last_confirm_week_w")
    p.add_argument("--last-event-ts", type=float, default=0.0)
    p.add_argument("--last-event-ts-w", type=float, default=0.0)
    p.add_argument("--json", action="store_true", help="Print full row subset as JSON")
    args = p.parse_args()

    now = _parse_at(args.at)
    last_w = args.last_tag_w or args.last_tag

    r = {
        "brk_lvl": args.brk_lvl,
        "brk_lvl_w": args.brk_lvl_w,
        "last_tag": args.last_tag,
        "last_tag_w": last_w,
        "last_event_ts": args.last_event_ts,
        "last_event_ts_w": args.last_event_ts_w,
        "b_count": args.b_count,
        "b_count_w": args.b_count_w,
        "cb_count_d": args.cb_count_d,
        "cb_count_w": args.cb_count_w,
        "cb_pending_day_d": args.cb_pending_day_d,
        "cb_pending_tag_d": args.cb_pending_tag_d,
        "cb_pending_ts_d": 0.0,
        "cb_last_confirm_day_d": args.cb_last_confirm_day_d,
        "cb_pending_week_w": args.cb_pending_week_w,
        "cb_pending_tag_w": args.cb_pending_tag_w,
        "cb_pending_ts_w": 0.0,
        "cb_last_confirm_week_w": args.cb_last_confirm_week_w,
    }

    _update_live_timing_breakout_status(r, args.ltp, now)

    pending_d = bool(r.get("cb_pending_day_d")) and str(r.get("cb_pending_tag_d") or "")
    pending_w = bool(r.get("cb_pending_week_w")) and str(r.get("cb_pending_tag_w") or "")
    state_d = _timing_state_from_tag(str(r.get("timing_last_tag") or ""), bool(pending_d))
    state_w = _timing_state_from_tag(str(r.get("timing_last_tag_w") or ""), bool(pending_w))

    keys = (
        "timing_last_tag",
        "timing_last_event_ts",
        "timing_last_tag_w",
        "timing_last_event_ts_w",
        "cb_pending_day_d",
        "cb_pending_tag_d",
        "cb_last_confirm_day_d",
        "cb_count_d",
        "cb_pending_week_w",
        "cb_pending_tag_w",
        "cb_last_confirm_week_w",
        "cb_count_w",
    )
    out = {k: r.get(k) for k in keys}

    if args.json:
        print(json.dumps({"at_ist": now.isoformat(), **out, "state_d": state_d, "state_w": state_w}, indent=2))
    else:
        print("at_ist={}".format(now.isoformat()))
        print(
            "STATE_D={}  LAST_TAG_D={!r}  pending_d={!r}".format(
                state_d, r.get("timing_last_tag"), pending_d
            )
        )
        print(
            "STATE_W={}  LAST_TAG_W={!r}  pending_w={!r}".format(
                state_w, r.get("timing_last_tag_w"), pending_w
            )
        )
        for k, v in out.items():
            print("  {}: {}".format(k, v))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
