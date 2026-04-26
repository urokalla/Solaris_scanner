import sys
import os
import time
import argparse
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging
from sqlalchemy import text
from tqdm import tqdm

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.connection_manager import ConnectionManager
from src.db_manager import DatabaseManager
from src.parquet_manager import ParquetManager
from src.utils import setup_logging

logger = setup_logging("eod_sync", "eod_sync.log")

# Symbol scope (production default):
# - Default: ``universe_members`` for ``EOD_UNIVERSE_ID`` (compose: ALL_NSE), only ``-EQ`` / ``-INDEX``.
# - ``EOD_NIFTY500_ONLY=1``: universe forced to NIFTY_500.
# - ``EOD_INDEX_ONLY=1``: all active ``-INDEX`` in ``symbols`` (no universe join); benchmarks still merged.

IST = ZoneInfo("Asia/Kolkata")

# Benchmarks (must match Fyers — Smallcap index is NIFTYSMLCAP100, not NIFTYSMALLCAP100)
BENCHMARK_SYMBOLS = [
    "NSE:NIFTY50-INDEX",
    "NSE:NIFTY100-INDEX",
    "NSE:NIFTY500-INDEX",
    "NSE:NIFTYBANK-INDEX",
    "NSE:NIFTYMIDCAP100-INDEX",
    "NSE:NIFTYSMLCAP100-INDEX",
    "NSE:FINNIFTY-INDEX",
]

# Outcome codes for summary
APPENDED = "appended"
NO_TODAY_BAR = "no_today_bar"
NO_CANDLES = "no_candles"
NO_DATA = "no_data"
REJECTED = "rejected"  # API: invalid symbol / bad request (delisted or wrong ticker)
FAIL = "fail"

# Gap-heal knobs (interior-gap detection against NIFTY50 session calendar)
_GAP_HEAL_DAYS_DEFAULT = 30  # lookback window for gap detection
_GAP_HEAL_CALENDAR_LOOKBACK_DAYS = 45  # NIFTY50 history fetched once to derive sessions


def normalize_fyers_symbol(sym: str) -> str:
    """
    Fix common DB/CSV mistakes vs Fyers API naming.
    - Index aliases (short names in DB)
    - EQ tickers: Fyers uses hyphens (BAJAJ-AUTO), some seeds use underscores (BAJAJ_AUTO)
    """
    s = (sym or "").strip().upper()
    if not s.startswith("NSE:"):
        return s
    body = s[4:]
    index_aliases = {
        "MIDCAP100-INDEX": "NIFTYMIDCAP100-INDEX",
        "SMALLCAP100-INDEX": "NIFTYSMLCAP100-INDEX",
        "NIFTYSMALLCAP100-INDEX": "NIFTYSMLCAP100-INDEX",
    }
    if body in index_aliases:
        return "NSE:" + index_aliases[body]
    if body.endswith("-EQ") and "_" in body:
        return "NSE:" + body.replace("_", "-")
    return s


def _fetch_eod_symbol_ids(session) -> list[str]:
    nifty500_only = os.environ.get("EOD_NIFTY500_ONLY", "").strip().lower() in ("1", "true", "yes")
    index_only = os.environ.get("EOD_INDEX_ONLY", "").strip().lower() in ("1", "true", "yes")
    universe_id = (os.environ.get("EOD_UNIVERSE_ID") or "ALL_NSE").strip() or "ALL_NSE"
    if nifty500_only:
        universe_id = "NIFTY_500"

    kind_filter = (
        "AND s.symbol_id LIKE '%-INDEX'"
        if index_only
        else "AND (s.symbol_id LIKE '%-EQ' OR s.symbol_id LIKE '%-INDEX')"
    )

    if index_only:
        query = text(
            f"""
            SELECT s.symbol_id
            FROM symbols s
            WHERE s.is_active = TRUE
            {kind_filter}
            """
        )
        rows = session.execute(query).fetchall()
    else:
        query = text(
            f"""
            SELECT s.symbol_id
            FROM symbols s
            INNER JOIN universe_members um ON s.symbol_id = um.symbol_id AND um.universe_id = :uid
            WHERE s.is_active = TRUE
            {kind_filter}
            """
        )
        rows = session.execute(query, {"uid": universe_id}).fetchall()
    return [r[0] for r in rows]


def _is_api_rejection(response: dict) -> bool:
    msg = (response.get("message") or "").lower()
    if "invalid symbol" in msg or "bad request" in msg:
        return True
    return False


def _fetch_benchmark_session_dates(conn, days: int = _GAP_HEAL_CALENDAR_LOOKBACK_DAYS) -> set:
    """
    Session IST dates from NIFTY50-INDEX over the last ``days``, excluding today.
    Used as the truth-source for which trading days every symbol should have.
    """
    now_ist = datetime.now(IST)
    from_str = (now_ist - timedelta(days=days)).strftime("%Y-%m-%d")
    to_str = now_ist.strftime("%Y-%m-%d")
    try:
        resp = conn.get_history("NSE:NIFTY50-INDEX", from_str, to_str, resolution="1D")
    except Exception as e:
        logger.warning("Gap-heal: benchmark calendar fetch failed: %s", e)
        return set()
    if resp.get("s") != "ok":
        logger.warning("Gap-heal: benchmark calendar not OK: %s", resp.get("message"))
        return set()
    out: set = set()
    today = now_ist.date()
    for c in resp.get("candles", []) or []:
        try:
            d = datetime.fromtimestamp(float(c[0]), tz=IST).date()
        except Exception:
            continue
        if d < today:
            out.add(d)
    return out


def _heal_interior_gaps(conn, pq_manager, symbol: str, reference_dates: set, window_days: int) -> int:
    """
    Refetch any missing recent session bars for ``symbol`` within the last
    ``window_days``. Returns the count of bars filled.
    """
    if not reference_dates or window_days <= 0:
        return 0
    try:
        existing = pq_manager.read_data(symbol)
    except Exception as e:
        logger.warning("Gap-heal: cannot read parquet for %s: %s", symbol, e)
        return 0
    if existing.empty or "timestamp" not in existing.columns:
        return 0
    try:
        ts_series = pd.to_datetime(existing["timestamp"])
        # Parquet stores naive UTC timestamps; localize to UTC then convert to IST.
        if ts_series.dt.tz is None:
            ts_ist = ts_series.dt.tz_localize("UTC").dt.tz_convert(IST)
        else:
            ts_ist = ts_series.dt.tz_convert(IST)
    except Exception as e:
        logger.warning("Gap-heal: timestamp parse failed for %s: %s", symbol, e)
        return 0
    have_dates = set(ts_ist.dt.date.tolist())
    window_start = (datetime.now(IST) - timedelta(days=window_days)).date()
    expected = {d for d in reference_dates if d >= window_start}
    missing = sorted(expected - have_dates)
    if not missing:
        return 0
    earliest = missing[0] - timedelta(days=2)
    latest = missing[-1] + timedelta(days=1)
    from_str = earliest.strftime("%Y-%m-%d")
    to_str = latest.strftime("%Y-%m-%d")
    try:
        resp = conn.get_history(symbol, from_str, to_str, resolution="1D")
    except Exception as e:
        logger.warning("Gap-heal: fetch failed for %s: %s", symbol, e)
        return 0
    if resp.get("s") != "ok":
        return 0
    candles = resp.get("candles", []) or []
    if not candles:
        return 0
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    ts_ist_new = df["timestamp"].dt.tz_convert(IST)
    df = df.loc[ts_ist_new.dt.date.isin(set(missing))].copy()
    if df.empty:
        return 0
    df["timestamp"] = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
    try:
        pq_manager.save_data(symbol, df, overwrite=False)
    except Exception as e:
        logger.warning("Gap-heal: write failed for %s: %s", symbol, e)
        return 0
    logger.info(
        "Gap-heal: %s filled %d missing bar(s) in [%s, %s]",
        symbol,
        len(df),
        from_str,
        to_str,
    )
    return int(len(df))


def sync_symbol(conn, pq_manager, symbol_in):
    """
    Fetch last sessions of 1D bars; append only rows whose IST session date is *today*.
    Returns outcome code for progress/summary.
    """
    try:
        symbol = normalize_fyers_symbol(symbol_in)
        if symbol != symbol_in.strip().upper():
            logger.debug("Normalized symbol %r -> %r", symbol_in, symbol)

        now_ist = datetime.now(IST)
        from_date = now_ist - timedelta(days=2)

        from_str = from_date.strftime("%Y-%m-%d")
        to_str = now_ist.strftime("%Y-%m-%d")
        target_day = now_ist.date()

        response = conn.get_history(symbol, from_str, to_str, resolution="1D")

        if response.get('s') == 'ok':
            candles = response.get('candles', [])
            if not candles:
                return NO_CANDLES
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
            ts_ist = df['timestamp'].dt.tz_convert(IST)
            df = df.loc[ts_ist.dt.date == target_day].copy()
            if df.empty:
                return NO_TODAY_BAR
            df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
            pq_manager.save_data(symbol, df, overwrite=False)
            return APPENDED
        if response.get('s') == 'no_data':
            return NO_DATA
        if _is_api_rejection(response):
            logger.warning(
                "Skip %s (API): %s",
                symbol,
                response.get("message", response),
            )
            return REJECTED
        logger.error(f"Error syncing {symbol}: {response.get('message', 'Unknown Error')}")
    except Exception as e:
        logger.exception(f"Exception syncing {symbol_in}: {e}")
    return FAIL


def main():
    ap = argparse.ArgumentParser(description="Append today’s 1D EOD bar per symbol (incremental).")
    ap.add_argument(
        "--no-tqdm",
        action="store_true",
        help="Disable progress bar (plain logs only)",
    )
    ap.add_argument(
        "--log-every",
        type=int,
        default=100,
        metavar="N",
        help="Log INFO line every N symbols (default 100, 0=off)",
    )
    args = ap.parse_args()

    conn = ConnectionManager()
    if not conn.connect():
        # Token missing / expired / malformed — don't spam stacktraces. Emit a clear one-line
        # marker on stdout so the pipeline scheduler can back off cleanly and retry later once
        # the operator drops in a fresh token. Exit 0 so there's no confusing "failed" in docker.
        logger.warning(
            "EOD skipped: Fyers connect failed (token likely expired or missing at %s). "
            "Refresh it and the next scheduler tick will pick it up automatically.",
            os.getenv("FYERS_ACCESS_TOKEN_PATH", "<default>"),
        )
        print("EOD_SYNC_RESULT skipped reason=token_expired", flush=True)
        sys.exit(0)

    # Early token health probe — catches JWTs that pass basic decode but are stale. Same handling
    # as above: log, print a marker, exit 0.
    try:
        probe = conn.get_history("NSE:NIFTY50-INDEX",
                                 (datetime.now(IST) - timedelta(days=5)).strftime("%Y-%m-%d"),
                                 datetime.now(IST).strftime("%Y-%m-%d"),
                                 resolution="1D")
        if isinstance(probe, dict) and probe.get("s") != "ok":
            msg = (probe.get("message") or "").lower()
            if "expire" in msg or "invalid" in msg or "unauthor" in msg or "token" in msg:
                logger.warning(
                    "EOD skipped: Fyers token appears invalid/expired (%s). Refresh access_token.txt.",
                    probe.get("message"),
                )
                print("EOD_SYNC_RESULT skipped reason=token_expired", flush=True)
                sys.exit(0)
    except Exception as e:
        logger.warning("EOD token probe errored (%s) — continuing; per-symbol calls will retry.", e)

    db = DatabaseManager()
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    _default_hist = os.path.join(_root, 'data', 'historical')
    pq_manager = ParquetManager(storage_path=os.getenv('PIPELINE_DATA_DIR', _default_hist))

    nifty500_only = os.environ.get("EOD_NIFTY500_ONLY", "").strip().lower() in ("1", "true", "yes")
    index_only = os.environ.get("EOD_INDEX_ONLY", "").strip().lower() in ("1", "true", "yes")
    eod_univ = (os.environ.get("EOD_UNIVERSE_ID") or "ALL_NSE").strip() or "ALL_NSE"
    if nifty500_only:
        eod_univ = "NIFTY_500"

    with db.Session() as session:
        db_symbols = _fetch_eod_symbol_ids(session)

    # Dedupe after normalization (DB may list MIDCAP100-INDEX while benchmarks use NIFTYMIDCAP100-INDEX)
    all_symbols = sorted({normalize_fyers_symbol(s) for s in (db_symbols + BENCHMARK_SYMBOLS)})
    total = len(all_symbols)

    try:
        heal_days = int(os.environ.get("EOD_HEAL_DAYS", str(_GAP_HEAL_DAYS_DEFAULT)))
    except ValueError:
        heal_days = _GAP_HEAL_DAYS_DEFAULT
    heal_enabled = heal_days > 0
    # One benchmark fetch gives the calendar used for every symbol.
    reference_dates: set = _fetch_benchmark_session_dates(conn) if heal_enabled else set()

    logger.info(
        "📊 [EOD Sync] Start | symbols=%s (DB=%s, benchmarks=%s) | universe=%s | "
        "EOD_NIFTY500_ONLY=%s EOD_INDEX_ONLY=%s | heal_days=%s (cal=%d)",
        total,
        len(db_symbols),
        len(BENCHMARK_SYMBOLS),
        eod_univ,
        nifty500_only,
        index_only,
        heal_days if heal_enabled else "off",
        len(reference_dates),
    )

    counts = {APPENDED: 0, NO_TODAY_BAR: 0, NO_CANDLES: 0, NO_DATA: 0, REJECTED: 0, FAIL: 0}
    healed_bars = 0
    healed_symbols = 0

    use_tqdm = not args.no_tqdm and os.getenv("EOD_NO_TQDM", "").lower() not in ("1", "true", "yes")

    iterator = enumerate(all_symbols, start=1)
    if use_tqdm:
        iterator = tqdm(
            iterator,
            total=total,
            desc="EOD sync",
            unit="sym",
            file=sys.stderr,
            mininterval=0.5,
            dynamic_ncols=True,
        )

    for i, symbol in iterator:
        code = sync_symbol(conn, pq_manager, symbol)
        counts[code] = counts.get(code, 0) + 1
        if heal_enabled and code not in (REJECTED,):
            filled = _heal_interior_gaps(conn, pq_manager, symbol, reference_dates, heal_days)
            if filled:
                healed_bars += filled
                healed_symbols += 1
                # Extra delay after heal fetch to stay inside API quota.
                time.sleep(0.15)
        if args.log_every and i % args.log_every == 0:
            logger.info(
                f"… progress {i}/{total} | appended={counts[APPENDED]} rejected={counts[REJECTED]} "
                f"fail={counts[FAIL]} no_today_bar={counts[NO_TODAY_BAR]} "
                f"healed_bars={healed_bars} healed_sym={healed_symbols}"
            )
        time.sleep(0.1)

    okish = total - counts[FAIL]
    logger.info(
        f"✅ [EOD Sync] Done | {okish}/{total} without exception | "
        f"appended={counts[APPENDED]} no_today_bar={counts[NO_TODAY_BAR]} "
        f"no_candles={counts[NO_CANDLES]} no_data={counts[NO_DATA]} "
        f"rejected={counts[REJECTED]} fail={counts[FAIL]} "
        f"healed_bars={healed_bars} healed_sym={healed_symbols}"
    )
    # One line on stdout for docker / cron wrappers
    print(
        f"EOD_SYNC_RESULT ok={okish}/{total} appended={counts[APPENDED]} "
        f"rejected={counts[REJECTED]} fail={counts[FAIL]} "
        f"healed_bars={healed_bars} healed_sym={healed_symbols}",
        flush=True,
    )
    sys.exit(0 if counts[FAIL] == 0 else 2)


if __name__ == "__main__":
    main()
