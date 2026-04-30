"""
LIVE_STRUCT_D: live structural transition ledger vs LAST_TAG D (last_tag).
Daily timing only. Uses row ema9_d / ema21_d (no EMA recompute) + same Donchian idea as B*.
No timing/CB overlay.
"""
from __future__ import annotations

import re
from datetime import date, datetime

import numpy as np

from config.settings import settings

from .breakout_logic import (
    TAG_ET9_WAIT_F21C,
    _is_e9ct_tag,
    _is_et9dn_wait_tag,
)


def _norm_b_base(last_tag: str) -> str:
    t = str(last_tag or "").strip().upper()
    if "+" in t:
        t = t.split("+", 1)[0].strip()
    return t


def _parse_b_n(last_tag: str) -> int | None:
    t = _norm_b_base(last_tag)
    if not t.startswith("B"):
        return None
    m = re.match(r"^B(\d+)$", t)
    if not m:
        return None
    return int(m.group(1))


def _next_b_target(last_tag: str, b_count: int) -> int | None:
    n = _parse_b_n(last_tag)
    if n is None and b_count:
        try:
            n = int(b_count)
        except (TypeError, ValueError):
            return None
    if n is None:
        return None
    return n + 1


def _is_e_structural(lt: str) -> bool:
    t = str(lt or "").strip().upper()
    if not t or t in ("—", "RST"):
        return False
    return bool(
        t.startswith("E21")
        or _is_e9ct_tag(t)
        or _is_et9dn_wait_tag(t)
        or (t.startswith("E") and not t.startswith("E21"))
    )


def _trending_e9_family(last_tag: str) -> bool:
    """State-1 style tags: B* or E9CT* (not ET9 wait / E21C / RST)."""
    t = _norm_b_base(last_tag)
    if not t or t == "RST":
        return False
    if _is_et9dn_wait_tag(t) or t.startswith("E21"):
        return False
    return _parse_b_n(last_tag) is not None or _is_e9ct_tag(t)


def donchian_next_b_live(
    hv: np.ndarray,
    ltp: float,
    don_len: int,
    e9: float,
    e21: float,
) -> bool:
    if hv is None or len(hv) < 6 or not np.isfinite(ltp) or ltp <= 0:
        return False
    j = len(hv) - 1
    dlen = max(2, int(don_len))
    if j < dlen + 1:
        return False
    try:
        highs = np.asarray(hv[:, 2], dtype=np.float64)
        close_ser = np.asarray(hv[:, 4], dtype=np.float64)
        trend_ok = float(ltp) > float(e9) > float(e21)
        don_c = float(np.max(highs[(j - dlen) : j]))
        don_p = float(np.max(highs[(j - dlen - 1) : (j - 1)]))
        pc = float(close_ser[j - 1])
        return bool(trend_ok and float(ltp) > don_c and pc <= don_p)
    except Exception:
        return False


def _eod_gate(now_ist: datetime, latch_day: date | None) -> bool:
    if latch_day is None:
        return False
    today = now_ist.date()
    if today > latch_day:
        return True
    if today == latch_day:
        return bool(
            settings.STRUCTURAL_SAMEDAY_AFTER_EOD_ENABLED
            and now_ist.weekday() < 5
            and (now_ist.hour, now_ist.minute)
            >= (
                settings.STRUCTURAL_SAMEDAY_AFTER_EOD_IST_HOUR,
                settings.STRUCTURAL_SAMEDAY_AFTER_EOD_IST_MINUTE,
            )
        )
    return False


def reconcile_live_struct_d(d: dict, now_ist: datetime) -> None:
    latch = str(d.get("lsd_latch") or "").strip()
    if not latch:
        return
    cur = str(d.get("live_struct_d") or "").strip()
    if cur and not cur.endswith("_Live_Watch"):
        return

    try:
        latch_day = date.fromisoformat(str(d.get("lsd_ist_day") or "").strip())
    except ValueError:
        latch_day = None
    if not _eod_gate(now_ist, latch_day):
        return

    lt_raw = str(d.get("last_tag") or "").strip()
    lt = _norm_b_base(lt_raw)
    last_key = str(d.get("cycle_last_bar_key") or "").strip()
    eod_key = f"{last_key}|{lt_raw}"
    if str(d.get("lsd_eod_key") or "") == eod_key:
        return

    fk = latch_day.isoformat() if latch_day else now_ist.date().isoformat()
    kind, _, rest = latch.partition(":")
    kind = kind.strip().upper()
    rest = rest.strip()

    if kind == "B":
        try:
            n = int(rest)
        except ValueError:
            d["lsd_eod_key"] = eod_key
            return
        want = f"B{n}"
        if lt == want:
            d["live_struct_d"] = f"{want}_Confirmed"
            d["lsd_sticky_confirmed"] = d["live_struct_d"]
        elif _is_e_structural(lt):
            d["live_struct_d"] = f"{lt}_Confirmed ({want}_live_aborted)"
            d["lsd_sticky_confirmed"] = d["live_struct_d"]
        else:
            d["live_struct_d"] = f"{want}_failed_on_{fk}"
    elif kind == "E":
        want = rest.upper()
        if lt_raw.upper() == want or lt == want:
            d["live_struct_d"] = f"{want}_Confirmed"
            d["lsd_sticky_confirmed"] = d["live_struct_d"]
        elif lt.startswith("B"):
            d["live_struct_d"] = f"{lt}_Confirmed ({want}_live_aborted)"
            d["lsd_sticky_confirmed"] = d["live_struct_d"]
        elif _is_e_structural(lt) and lt_raw.upper() != want and lt != want:
            d["live_struct_d"] = f"{lt}_Confirmed ({want}_live_aborted)"
            d["lsd_sticky_confirmed"] = d["live_struct_d"]
        else:
            d["live_struct_d"] = f"{want}_failed_on_{fk}"
    d["lsd_latch"] = ""
    d["lsd_ge9"] = 0
    d["lsd_e9ct_touch"] = 0
    d["lsd_under9_streak"] = 0
    d["lsd_eod_key"] = eod_key


def _clear_lsd_session(d: dict) -> None:
    d["live_struct_d"] = ""
    d["lsd_latch"] = ""
    d["lsd_ist_day"] = ""
    d["lsd_ge9"] = 0
    d["lsd_e9ct_touch"] = 0
    d["lsd_under9_streak"] = 0
    d["lsd_eod_key"] = ""
    d["lsd_prev_ltp"] = 0.0
    d["lsd_sticky_confirmed"] = ""


def _confirmed_primary_tag(live_struct_d: str) -> str:
    s = str(live_struct_d or "").strip()
    if not s:
        return ""
    i = s.find("_Confirmed")
    if i <= 0:
        return ""
    return s[:i].strip().upper()


def update_live_struct_d_row(
    d: dict,
    hv: np.ndarray | None,
    don_len: int,
    now_ist: datetime,
) -> None:
    """Mutates d in place; caller persists keys into self.results for timing+daily."""
    today_s = now_ist.date().isoformat()
    latch_day_s = str(d.get("lsd_ist_day") or "").strip()

    lt0 = str(d.get("last_tag") or "").strip().upper()
    if lt0 == "RST":
        _clear_lsd_session(d)
        return

    reconcile_live_struct_d(d, now_ist)

    # Guardrail: finalized outcomes are informational and must not stick across structural state
    # changes. If LAST_TAG no longer matches the finalized primary tag, clear the stale outcome.
    cur_post = str(d.get("live_struct_d") or "").strip()
    if cur_post and ("_Confirmed" in cur_post or "_failed_on_" in cur_post):
        _p = _confirmed_primary_tag(cur_post)
        _lt_now = _norm_b_base(str(d.get("last_tag") or ""))
        if _p and _lt_now and _p != _lt_now:
            d["live_struct_d"] = ""
            d["lsd_latch"] = ""
            d["lsd_ist_day"] = ""
            d["lsd_ge9"] = 0
            d["lsd_e9ct_touch"] = 0
            d["lsd_under9_streak"] = 0
            d["lsd_eod_key"] = ""
            d["lsd_sticky_confirmed"] = ""

    # Sticky confirmed mode: retain latest confirmed value while it matches LAST_TAG D truth.
    cur_post = str(d.get("live_struct_d") or "").strip()
    if not cur_post:
        _sticky = str(d.get("lsd_sticky_confirmed") or "").strip()
        if _sticky:
            _sp = _confirmed_primary_tag(_sticky)
            _lt_now = _norm_b_base(str(d.get("last_tag") or ""))
            if _sp and _lt_now and _sp == _lt_now:
                d["live_struct_d"] = _sticky
            else:
                d["lsd_sticky_confirmed"] = ""

    if latch_day_s and latch_day_s != today_s:
        try:
            _ld = date.fromisoformat(latch_day_s)
        except ValueError:
            _ld = None
        cur_after = str(d.get("live_struct_d") or "").strip()
        if _ld and cur_after.endswith("_Live_Watch"):
            # Reconcile runs earlier; if watch is still present on a new day, treat it as unresolved and clear.
            d["live_struct_d"] = ""
            d["lsd_latch"] = ""
            d["lsd_ist_day"] = ""
            d["lsd_ge9"] = 0
            d["lsd_e9ct_touch"] = 0
            d["lsd_under9_streak"] = 0
            d["lsd_prev_ltp"] = 0.0

    cur = str(d.get("live_struct_d") or "").strip()
    if cur and any(x in cur for x in ("_Confirmed", "_failed_on_", "(")):
        return

    ltp = float(d.get("ltp") or 0.0)
    e9, e21 = d.get("ema9_d"), d.get("ema21_d")
    if hv is None or len(hv) < 6 or ltp <= 0.0 or e9 is None or e21 is None:
        return
    try:
        e9f = float(e9)
        e21f = float(e21)
    except (TypeError, ValueError):
        return

    st = int(d.get("cycle_state") or 0)
    last_tag = str(d.get("last_tag") or "")
    bct = int(d.get("b_count") or 0)
    prev_ltp = float(d.get("lsd_prev_ltp") or 0.0)
    have_prev = prev_ltp > 0.0

    if str(d.get("lsd_latch") or "").strip():
        d["lsd_prev_ltp"] = ltp
        return
    if cur.endswith("_Live_Watch"):
        d["lsd_prev_ltp"] = ltp
        return

    if st == 1 and _parse_b_n(last_tag) is not None:
        n_next = _next_b_target(last_tag, bct)
        # Require an intraday cross (prev<=don, now>don) to avoid stale "already above" arms.
        crossed_now = False
        if have_prev:
            try:
                highs = np.asarray(hv[:, 2], dtype=np.float64)
                j = len(hv) - 1
                dlen = max(2, int(don_len))
                if j >= dlen + 1:
                    don_c = float(np.max(highs[(j - dlen) : j]))
                    crossed_now = bool(prev_ltp <= don_c and ltp > don_c)
            except Exception:
                crossed_now = False
        if n_next and crossed_now and donchian_next_b_live(hv, ltp, don_len, e9f, e21f):
            d["lsd_latch"] = f"B:{n_next}"
            d["lsd_ist_day"] = today_s
            d["live_struct_d"] = f"B{n_next}_Breakout_Live_Watch"
            d["lsd_prev_ltp"] = ltp
            return

    ge9 = int(d.get("lsd_ge9") or 0)
    touch = int(d.get("lsd_e9ct_touch") or 0)
    streak = int(d.get("lsd_under9_streak") or 0)

    if ltp >= e9f:
        d["lsd_ge9"] = 1
        if touch and st == 1 and _trending_e9_family(last_tag):
            n_e = int(d.get("e9t_count") or 0) + 1
            want = f"E9CT{n_e}"
            d["lsd_latch"] = f"E:{want}"
            d["lsd_ist_day"] = today_s
            d["live_struct_d"] = f"{want}_Live_Watch"
            d["lsd_e9ct_touch"] = 0
            d["lsd_under9_streak"] = 0
            d["lsd_prev_ltp"] = ltp
            return
        d["lsd_under9_streak"] = 0
    elif st == 1 and _trending_e9_family(last_tag):
        if ge9:
            d["lsd_e9ct_touch"] = 1
            d["lsd_under9_streak"] = streak + 1
            if int(d.get("lsd_under9_streak") or 0) >= 2:
                d["lsd_latch"] = f"E:{TAG_ET9_WAIT_F21C}"
                d["lsd_ist_day"] = today_s
                d["live_struct_d"] = f"{TAG_ET9_WAIT_F21C}_Live_Watch"
                d["lsd_e9ct_touch"] = 0
                d["lsd_under9_streak"] = 0
                d["lsd_prev_ltp"] = ltp
                return

    # Require reclaim cross above both EMAs on this poll, not merely "currently above".
    if (
        (st == 2 or _is_et9dn_wait_tag(_norm_b_base(last_tag)))
        and ltp > e9f
        and ltp > e21f
        and (not have_prev or prev_ltp <= max(e9f, e21f))
    ):
        n21 = int(d.get("e21c_count") or 0) + 1
        want = f"E21C{n21}"
        d["lsd_latch"] = f"E:{want}"
        d["lsd_ist_day"] = today_s
        d["live_struct_d"] = f"{want}_Live_Watch"
        d["lsd_prev_ltp"] = ltp
        return
    d["lsd_prev_ltp"] = ltp
