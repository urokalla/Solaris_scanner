import asyncio
import json
import logging
import time

from config.settings import settings

from .breakout_engine_manager import get_breakout_scanner

_LOG = logging.getLogger("BreakoutTimingPoll")


def _normalize_clock_tf(v: str) -> str:
    s = str(v or "").strip().lower()
    if s in ("d", "day", "daily"):
        return "daily"
    if s in ("w", "week", "weekly"):
        return "weekly"
    # Defensive default: daily clock is the primary page and should never run blank.
    return "daily"


def _results_signature(rows: list[dict]) -> str:
    # Only include stable, user-visible fields to avoid churn from non-UI metadata noise.
    keys = (
        "symbol",
        "last_tag",
        "live_struct_d",
        "lsd_latch",
        "ltp",
        "chp",
        "rv",
        "wmrs",
        "setup_score",
        "last_ts",
        "last_ts_w",
        "pct_from_b_d",
        "pct_live_d",
        "pct_from_b_w",
        "pct_live_w",
    )
    payload = [{k: r.get(k) for k in keys} for r in (rows or [])]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


async def poll_breakout_timing_handler(self):
    next_live_struct_refresh_ts = 0.0
    next_diag_log_ts = 0.0
    while True:
        await asyncio.sleep(max(0.5, float(settings.DASHBOARD_POLL_INTERVAL_SEC)))
        try:
            async with self:
                scanner = get_breakout_scanner(universe=self.universe, role="timing")
                _ctf = _normalize_clock_tf(getattr(self, "clock_timeframe", ""))
                _universe = self.universe
                _search_query = self.search_query
                _filter_profile = self.filter_profile
                _filter_brk_stage = self.filter_brk_stage
                _filter_mrs_grid = self.filter_mrs_grid
                _filter_wmrs_slope = getattr(self, "filter_wmrs_slope", "ALL")
                _filter_m_rsi2 = self.filter_m_rsi2
                _sort_timing_key = self.sort_timing_key
                _sort_timing_desc = self.sort_timing_desc
                _timing_filter = self.timing_filter
                _current_page = int(self.current_page)
                _page_size = int(self.page_size)
                _prev_results = list(self.results or [])
                _prev_results_sig = str(getattr(self, "results_signature", "") or "")
                _prev_sig = str(getattr(self, "last_non_empty_signature", "") or "")
                _prev_non_empty = list(getattr(self, "last_non_empty_results", []) or [])
                _live_total = int(getattr(self, "live_struct_rows_raw", 0) or 0)
                view = scanner.get_ui_view(
                    page=_current_page,
                    page_size=_page_size,
                    search=_search_query,
                    profile=_filter_profile,
                    brk_stage=_filter_brk_stage,
                    filter_mrs_grid=_filter_mrs_grid,
                    wmrs_slope=_filter_wmrs_slope,
                    filter_m_rsi2=_filter_m_rsi2,
                    preset="ALL",
                    sort_key=_sort_timing_key,
                    sort_desc=_sort_timing_desc,
                    timing_filter=_timing_filter,
                    mode="timing",
                    clock_timeframe=_ctf,
                )
                new_results = view.get("results", [])
                new_total = int(view.get("total_count", 0) or 0)
                _eod_sync_status = str(view.get("eod_sync_status", "EOD_SYNC_UNKNOWN") or "EOD_SYNC_UNKNOWN")
                _eod_expected_date = str(view.get("eod_expected_date", "-") or "-")
                _eod_fresh_count = int(view.get("eod_fresh_count", 0) or 0)
                _eod_total_count = int(view.get("eod_total_count", 0) or 0)
                _eod_stale_count = int(view.get("eod_stale_count", 0) or 0)
                _eod_sync_pct = float(view.get("eod_sync_pct", 0.0) or 0.0)
                _eod_last_checked_ist = str(view.get("eod_last_checked_ist", "-") or "-")
            # Keep this count accurate but do not query full-universe LIVE_STRUCT on every poll.
            _now_ts = float(time.time())
            if _now_ts >= next_live_struct_refresh_ts:
                try:
                    _live_view = scanner.get_ui_view(
                        page=1,
                        page_size=1,
                        search="",
                        profile="ALL",
                        brk_stage="ALL",
                        filter_mrs_grid="ALL",
                        wmrs_slope="ALL",
                        filter_m_rsi2="ALL",
                        preset="ALL",
                        sort_key="last_ts",
                        sort_desc=True,
                        timing_filter="LIVE_STRUCT_ONLY",
                        mode="timing",
                        clock_timeframe=_ctf,
                    )
                    _live_total = int(_live_view.get("total_count", 0) or 0)
                except Exception:
                    pass
                next_live_struct_refresh_ts = _now_ts + 5.0

            query_sig = "|".join(
                [
                    str(_ctf),
                    str(_universe),
                    str(_search_query or ""),
                    str(_filter_profile or "ALL"),
                    str(_filter_brk_stage or "ALL"),
                    str(_filter_mrs_grid or "ALL"),
                    str(_filter_wmrs_slope or "ALL"),
                    str(_filter_m_rsi2 or "ALL"),
                    str(_timing_filter or "ALL"),
                    str(_sort_timing_key or ""),
                    str(bool(_sort_timing_desc)),
                    str(int(_current_page)),
                    str(int(_page_size)),
                ]
            )
            new_current_page = _current_page
            if new_total > 0 and not new_results and int(_current_page) > 1:
                new_current_page = 1
                view = scanner.get_ui_view(
                    page=1,
                    page_size=_page_size,
                    search=_search_query,
                    profile=_filter_profile,
                    brk_stage=_filter_brk_stage,
                    filter_mrs_grid=_filter_mrs_grid,
                    wmrs_slope=_filter_wmrs_slope,
                    filter_m_rsi2=_filter_m_rsi2,
                    preset="ALL",
                    sort_key=_sort_timing_key,
                    sort_desc=_sort_timing_desc,
                    timing_filter=_timing_filter,
                    mode="timing",
                    clock_timeframe=_ctf,
                )
                new_results = view.get("results", [])
                new_total = int(view.get("total_count", 0) or 0)
            new_last_sig = _prev_sig
            new_last_non_empty = _prev_non_empty
            if new_results:
                new_last_sig = query_sig
                new_last_non_empty = list(new_results)
            elif query_sig == _prev_sig and bool(_prev_non_empty):
                new_results = list(_prev_non_empty)
                new_total = len(new_results)
            new_results_sig = _results_signature(new_results)
            changed = new_results_sig != _prev_results_sig
            async with self:
                self.current_page = int(new_current_page)
                self.last_non_empty_signature = new_last_sig
                self.last_non_empty_results = new_last_non_empty
                self.results_signature = new_results_sig
                self.total_count = new_total
                self.live_struct_rows = _live_total
                self.live_struct_rows_raw = _live_total
                self.eod_sync_status = _eod_sync_status
                self.eod_expected_date = _eod_expected_date
                self.eod_fresh_count = _eod_fresh_count
                self.eod_total_count = _eod_total_count
                self.eod_stale_count = _eod_stale_count
                self.eod_sync_pct = _eod_sync_pct
                self.eod_last_checked_ist = _eod_last_checked_ist
                if changed:
                    self.results = new_results
                self.status_message = "✅ Active" if self.total_count > 0 else "📡 Syncing..."
                if changed:
                    self.last_sync = time.strftime("%H:%M:%S")
            if _LOG.isEnabledFor(logging.DEBUG):
                try:
                    _sample = []
                    for _r in (new_results or []):
                        _lsd = str(_r.get("live_struct_d") or "").strip()
                        _lat = str(_r.get("lsd_latch") or "").strip()
                        if _lsd or _lat:
                            _sample.append(
                                (
                                    str(_r.get("symbol") or ""),
                                    str(_r.get("last_tag") or ""),
                                    _lsd or "—",
                                    _lat or "—",
                                )
                            )
                        if len(_sample) >= 3:
                            break
                    _LOG.debug(
                        "[poll] tf=%s uni=%s total=%s live_total=%s page=%s changed=%s sample=%s",
                        _ctf,
                        _universe,
                        int(new_total),
                        int(_live_total),
                        int(new_current_page),
                        bool(changed),
                        _sample,
                    )
                except Exception:
                    pass
            if _now_ts >= next_diag_log_ts:
                try:
                    _LOG.info(
                        "[poll-diag] tf=%s uni=%s timing_filter=%s total=%s live_total=%s page=%s changed=%s",
                        _ctf,
                        _universe,
                        _timing_filter,
                        int(new_total),
                        int(_live_total),
                        int(new_current_page),
                        bool(changed),
                    )
                    if int(_live_total) == 0 and str(_ctf) == "daily":
                        _LOG.warning(
                            "[poll-diag] daily LIVE_STRUCT_ONLY is 0. eod=%s fresh=%s/%s stale=%s",
                            _eod_sync_status,
                            int(_eod_fresh_count),
                            int(_eod_total_count),
                            int(_eod_stale_count),
                        )
                except Exception:
                    pass
                next_diag_log_ts = _now_ts + 15.0
        except Exception as e:
            async with self:
                self.status_message = f"ERR poll: {type(e).__name__}"
                self.last_sync = time.strftime("%H:%M:%S")
            _LOG.exception("[poll] exception")
