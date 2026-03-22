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


def _is_api_rejection(response: dict) -> bool:
    msg = (response.get("message") or "").lower()
    if "invalid symbol" in msg or "bad request" in msg:
        return True
    return False


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
        logger.error("Failed to connect to Fyers API.")
        sys.exit(1)

    db = DatabaseManager()
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    _default_hist = os.path.join(_root, 'data', 'historical')
    pq_manager = ParquetManager(storage_path=os.getenv('PIPELINE_DATA_DIR', _default_hist))

    with db.Session() as session:
        result = session.execute(text("SELECT symbol_id FROM symbols WHERE is_active = TRUE")).fetchall()
        db_symbols = [r[0] for r in result]

    # Dedupe after normalization (DB may list MIDCAP100-INDEX while benchmarks use NIFTYMIDCAP100-INDEX)
    all_symbols = sorted({normalize_fyers_symbol(s) for s in (db_symbols + BENCHMARK_SYMBOLS)})
    total = len(all_symbols)

    logger.info(
        f"📊 [EOD Sync] Start | symbols={total} (active DB={len(db_symbols)}, benchmarks={len(BENCHMARK_SYMBOLS)})"
    )

    counts = {APPENDED: 0, NO_TODAY_BAR: 0, NO_CANDLES: 0, NO_DATA: 0, REJECTED: 0, FAIL: 0}

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
        if args.log_every and i % args.log_every == 0:
            logger.info(
                f"… progress {i}/{total} | appended={counts[APPENDED]} rejected={counts[REJECTED]} "
                f"fail={counts[FAIL]} no_today_bar={counts[NO_TODAY_BAR]}"
            )
        time.sleep(0.1)

    okish = total - counts[FAIL]
    logger.info(
        f"✅ [EOD Sync] Done | {okish}/{total} without exception | "
        f"appended={counts[APPENDED]} no_today_bar={counts[NO_TODAY_BAR]} "
        f"no_candles={counts[NO_CANDLES]} no_data={counts[NO_DATA]} "
        f"rejected={counts[REJECTED]} fail={counts[FAIL]}"
    )
    # One line on stdout for docker / cron wrappers
    print(
        f"EOD_SYNC_RESULT ok={okish}/{total} appended={counts[APPENDED]} "
        f"rejected={counts[REJECTED]} fail={counts[FAIL]}",
        flush=True,
    )
    sys.exit(0 if counts[FAIL] == 0 else 2)


if __name__ == "__main__":
    main()
