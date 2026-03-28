import os, time, psycopg2, numpy as np, logging, csv
from utils.constants import UNIVERSE_ID_BY_DISPLAY, SYMBOL_GROUPS

logger = logging.getLogger(__name__)
from psycopg2.extras import execute_values
from psycopg2.pool import ThreadedConnectionPool
from datetime import datetime
from contextlib import contextmanager


# Serialize writers to live_state (master persist + sidecar brk_lvl + EOD snapshot) — avoids PK/index deadlocks.
LIVE_STATE_XACT_LOCK_KEY = 902451837261


def acquire_live_state_xact_lock(cursor) -> None:
    cursor.execute("SELECT pg_advisory_xact_lock(%s)", (LIVE_STATE_XACT_LOCK_KEY,))


def _is_deadlock_exception(exc: BaseException) -> bool:
    try:
        from psycopg2 import errorcodes

        if getattr(exc, "pgcode", None) == errorcodes.DEADLOCK_DETECTED:
            return True
    except Exception:
        pass
    try:
        from psycopg2 import errors as pg_errors

        if isinstance(exc, pg_errors.DeadlockDetected):
            return True
    except Exception:
        pass
    return "deadlock" in str(exc).lower()

class DatabaseManager:
    _pool = None
    _brk_lvl_column_checked = False
    _mrs_prev_day_column_checked = False

    def __init__(self):
        self.host, self.port = os.getenv('DB_HOST', 'localhost'), os.getenv('DB_PORT', '5432')
        self.user, self.pwd = os.getenv('DB_USER', 'fyers_user'), os.getenv('DB_PASSWORD', 'fyers_pass')
        self.db = os.getenv('DB_NAME', 'fyers_db')
        self._init_pool()

    def _init_pool(self):
        if DatabaseManager._pool is None:
            try:
                DatabaseManager._pool = ThreadedConnectionPool(
                    5, 50, # min, max connections
                    host=self.host, port=self.port,
                    user=self.user, password=self.pwd, dbname=self.db
                )
            except Exception as e:
                logger.error(f"Error creating connection pool: {e}")

    @contextmanager
    def get_connection(self):
        if DatabaseManager._pool is None:
            logger.error("Database connection pool not initialized. Is the database service running?")
            raise ConnectionError("Database not ready.")
        conn = None
        try:
            conn = DatabaseManager._pool.getconn()
            # Pool can hand out stale/closed sockets after Postgres restart.
            if conn is None or getattr(conn, "closed", 1) != 0:
                try:
                    if conn is not None:
                        DatabaseManager._pool.putconn(conn, close=True)
                except Exception:
                    pass
                conn = DatabaseManager._pool.getconn()
            yield conn
        finally:
            try:
                if conn is not None:
                    if getattr(conn, "closed", 1) == 0:
                        DatabaseManager._pool.putconn(conn)
                    else:
                        DatabaseManager._pool.putconn(conn, close=True)
            except Exception:
                pass

    def get_historical_data(self, symbol, timeframe, limit=365):
        q = "SELECT timestamp, open, high, low, close, volume FROM prices WHERE symbol=%s AND timeframe=%s ORDER BY timestamp DESC LIMIT %s"
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(q, (symbol, timeframe, limit))
                res = cur.fetchall()
                if not res: return np.empty((0, 6))
                return np.array([[r[0].timestamp() if isinstance(r[0], datetime) else 0.0, r[1], r[2], r[3], r[4], r[5]] for r in res][::-1])

    def get_symbols_by_universe(self, universe_id):
        if not universe_id:
            universe_id = "Nifty 500"
        uid = UNIVERSE_ID_BY_DISPLAY.get(universe_id)
        if uid is None:
            uid = str(universe_id).upper().replace(" ", "_")
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT symbol_id FROM universe_members WHERE universe_id = %s", (uid,))
                rows = [r[0] for r in cur.fetchall()]
        if rows:
            return rows
        # DB fallback: allow newly-added universes to work immediately from CSV even before re-seeding tables.
        rel = SYMBOL_GROUPS.get(universe_id)
        if not rel:
            return rows
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = os.path.join(base, rel)
        if not os.path.exists(p):
            return rows
        try:
            with open(p, encoding="utf-8-sig") as f:
                r = csv.DictReader(f)
                c = next((h for h in (r.fieldnames or []) if h.lower() == "symbol"), (r.fieldnames or ["Symbol"])[0])
                out = []
                for row in r:
                    v = row.get(c)
                    s = v.strip().upper() if v else ""
                    if not s:
                        continue
                    out.append(
                        s if s.startswith("NSE:") else (f"NSE:{s}" if "INDEX" in s else f"NSE:{s}-EQ")
                    )
                return out
        except Exception:
            return rows

    def get_all_active_symbols(self):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # 30-Year Engineer Rule: Only scan Equities (-EQ), Indices (-INDEX), 
                # or raw tickers (which we default to EQ). Exclude Bonds/NCDs/Debt.
                q = """
                    SELECT symbol_id FROM symbols 
                    WHERE is_active = TRUE 
                    AND (
                        symbol_id LIKE '%-EQ' 
                        OR symbol_id LIKE '%-INDEX' 
                        OR symbol_id NOT LIKE '%:%'
                    )
                """
                cur.execute(q)
                return [r[0] for r in cur.fetchall()]

    def save_rs_ratings(self, ratings_dict):
        today = datetime.now().date()
        data = [(s, today, int(v.get('rs_rating', 0)), float(v.get('mRS', 0.0))) for s, v in ratings_dict.items()]
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, "INSERT INTO rs_ratings (symbol, date, rs_rating, mrs) VALUES %s ON CONFLICT (symbol, date) DO UPDATE SET rs_rating=EXCLUDED.rs_rating, mrs=EXCLUDED.mrs", data)
                conn.commit()
                logger.info(f"💾 [Database] Successfully persisted {len(data)} RS ratings for {today}.")

    def ensure_live_state_table(self):
        """
        Create live_state if it does not exist (fresh Postgres / new env).
        MasterScanner.persist_to_postgres and sidecar upsert_brk_lvls both require this table.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS live_state (
                            symbol VARCHAR(96) PRIMARY KEY,
                            last_price DOUBLE PRECISION,
                            mrs DOUBLE PRECISION,
                            rs_rating INTEGER,
                            status TEXT,
                            brk_lvl DOUBLE PRECISION,
                            mrs_prev_day DOUBLE PRECISION
                        )
                        """
                    )
                    conn.commit()
        except Exception as e:
            logger.warning("Database: ensure_live_state_table: %s", e)

    def ensure_live_state_brk_column(self):
        """Align Layer 3 live_state with sidecar: pivot breakout level (see docs/architecture_data_layers.md)."""
        if DatabaseManager._brk_lvl_column_checked:
            return
        try:
            self.ensure_live_state_table()
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = 'live_state' AND column_name = 'brk_lvl'
                        """
                    )
                    if cur.fetchone() is None:
                        cur.execute("ALTER TABLE live_state ADD COLUMN brk_lvl DOUBLE PRECISION")
                        conn.commit()
                        logger.info("Database: added live_state.brk_lvl")
            DatabaseManager._brk_lvl_column_checked = True
        except Exception as e:
            logger.warning("Database: ensure_live_state_brk_column: %s", e)

    def upsert_brk_lvls(self, rows):
        """rows: list of (symbol, brk_lvl). Single upsert path; existing live_state rows get brk_lvl updated."""
        if not rows:
            return
        self.ensure_live_state_table()
        # Stable row lock order vs master persist_to_postgres avoids many deadlocks on live_state PK.
        payload = sorted(((s, float(b)) for s, b in rows), key=lambda x: x[0])
        for attempt in range(5):
            try:
                with self.get_connection() as conn:
                    try:
                        with conn.cursor() as cur:
                            acquire_live_state_xact_lock(cur)
                            execute_values(
                                cur,
                                """
                                INSERT INTO live_state (symbol, brk_lvl) VALUES %s
                                ON CONFLICT (symbol) DO UPDATE SET brk_lvl = EXCLUDED.brk_lvl
                                """,
                                payload,
                            )
                        conn.commit()
                        return
                    except Exception:
                        try:
                            if conn is not None and getattr(conn, "closed", 1) == 0:
                                conn.rollback()
                        except Exception:
                            pass
                        raise
            except Exception as e:
                emsg = str(e).lower()
                is_conn_drop = isinstance(e, (psycopg2.OperationalError, psycopg2.InterfaceError)) or (
                    "connection already closed" in emsg or "server closed the connection" in emsg
                )
                if (_is_deadlock_exception(e) or is_conn_drop) and attempt < 4:
                    time.sleep(0.05 * (2**attempt))
                    continue
                logger.error("Database: upsert_brk_lvls failed: %s", e, exc_info=True)
                return

    def get_brk_lvl_map(self, symbols):
        """Return {symbol: brk_lvl} for UI hydration when in-memory sidecar row has no pivot yet."""
        if not symbols:
            return {}
        self.ensure_live_state_brk_column()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT symbol, brk_lvl FROM live_state WHERE symbol IN %s AND brk_lvl IS NOT NULL",
                        (tuple(symbols),),
                    )
                    return {r[0]: float(r[1]) for r in cur.fetchall()}
        except Exception as e:
            logger.warning("Database: get_brk_lvl_map failed: %s", e)
            return {}

    def ensure_mrs_prev_day_column(self):
        """Prior session end-of-day weekly mRS (for TRENDING vs BUY latch rules on main grid)."""
        if DatabaseManager._mrs_prev_day_column_checked:
            return
        try:
            self.ensure_live_state_table()
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = 'live_state' AND column_name = 'mrs_prev_day'
                        """
                    )
                    if cur.fetchone() is None:
                        cur.execute("ALTER TABLE live_state ADD COLUMN mrs_prev_day DOUBLE PRECISION")
                        conn.commit()
                        logger.info("Database: added live_state.mrs_prev_day")
            DatabaseManager._mrs_prev_day_column_checked = True
        except Exception as e:
            logger.warning("Database: ensure_mrs_prev_day_column: %s", e)

    def get_mrs_prev_day_map(self, symbols):
        """Return {symbol: mrs_prev_day} for grid column (prior trading day EOD snapshot)."""
        if not symbols:
            return {}
        self.ensure_mrs_prev_day_column()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT symbol, mrs_prev_day FROM live_state WHERE symbol IN %s AND mrs_prev_day IS NOT NULL",
                        (tuple(symbols),),
                    )
                    return {r[0]: float(r[1]) for r in cur.fetchall()}
        except Exception as e:
            logger.warning("Database: get_mrs_prev_day_map failed: %s", e)
            return {}

    def snapshot_mrs_prev_day_from_current_mrs(self):
        """EOD: copy current weekly mrs into mrs_prev_day for next session (IST close run once/day)."""
        self.ensure_mrs_prev_day_column()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    acquire_live_state_xact_lock(cur)
                    cur.execute("UPDATE live_state SET mrs_prev_day = mrs WHERE mrs IS NOT NULL")
                    n = cur.rowcount
                    conn.commit()
                logger.info("Database: EOD snapshot mrs_prev_day <- mrs (%s rows)", n)
        except Exception as e:
            logger.error("Database: snapshot_mrs_prev_day_from_current_mrs failed: %s", e, exc_info=True)

    _pre_thrust_table_checked = False

    def ensure_pre_thrust_table(self) -> None:
        """
        Daily snapshot table for your "pre-thrust" bucket (yesterday clues).
        Written by sidecar around 14:30 IST so you can check quickly.
        """
        if DatabaseManager._pre_thrust_table_checked:
            return
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS pre_thrust_watchlist (
                            symbol VARCHAR(96),
                            run_date DATE,
                            y_date DATE,
                            y_vol_x20 DOUBLE PRECISION,
                            y_rng_x_atr14 DOUBLE PRECISION,
                            y_compress_10d INTEGER,
                            y_compress_20d INTEGER,
                            y_near_20d_high INTEGER,
                            y_near_52w_high INTEGER,
                            y_near_multiy_high INTEGER,
                            y_score INTEGER,
                            y_label TEXT,
                            PRIMARY KEY(symbol, run_date)
                        )
                        """
                    )
                    conn.commit()
            DatabaseManager._pre_thrust_table_checked = True
        except Exception as e:
            logger.warning("Database: ensure_pre_thrust_table failed: %s", e)

    def upsert_pre_thrust_watchlist(self, rows: list[tuple]) -> None:
        """
        rows:
          (symbol, run_date, y_date, y_vol_x20, y_rng_x_atr14,
           y_compress_10d, y_compress_20d,
           y_near_20d_high, y_near_52w_high, y_near_multiy_high,
           y_score, y_label)
        """
        if not rows:
            return
        self.ensure_pre_thrust_table()
        payload = []
        for r in rows:
            if not r:
                continue
            # Ensure bools become ints for Postgres.
            symbol = str(r[0])
            payload.append(
                (
                    symbol,
                    r[1],
                    r[2],
                    float(r[3]) if r[3] is not None and np.isfinite(r[3]) else None,
                    float(r[4]) if r[4] is not None and np.isfinite(r[4]) else None,
                    int(r[5]) if r[5] is not None else 0,
                    int(r[6]) if r[6] is not None else 0,
                    int(r[7]) if r[7] is not None else 0,
                    int(r[8]) if r[8] is not None else 0,
                    int(r[9]) if r[9] is not None else 0,
                    int(r[10]) if r[10] is not None else 0,
                    str(r[11]) if r[11] is not None else None,
                )
            )
        q = """
            INSERT INTO pre_thrust_watchlist (
                symbol, run_date, y_date, y_vol_x20, y_rng_x_atr14,
                y_compress_10d, y_compress_20d,
                y_near_20d_high, y_near_52w_high, y_near_multiy_high,
                y_score, y_label
            )
            VALUES %s
            ON CONFLICT (symbol, run_date) DO UPDATE SET
                y_date = EXCLUDED.y_date,
                y_vol_x20 = EXCLUDED.y_vol_x20,
                y_rng_x_atr14 = EXCLUDED.y_rng_x_atr14,
                y_compress_10d = EXCLUDED.y_compress_10d,
                y_compress_20d = EXCLUDED.y_compress_20d,
                y_near_20d_high = EXCLUDED.y_near_20d_high,
                y_near_52w_high = EXCLUDED.y_near_52w_high,
                y_near_multiy_high = EXCLUDED.y_near_multiy_high,
                y_score = EXCLUDED.y_score,
                y_label = EXCLUDED.y_label
        """
        for attempt in range(5):
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        acquire_live_state_xact_lock(cur)
                        execute_values(cur, q, payload)
                    conn.commit()
                    return
            except Exception as e:
                if _is_deadlock_exception(e) and attempt < 4:
                    time.sleep(0.05 * (2**attempt))
                    continue
                logger.error("Database: upsert_pre_thrust_watchlist failed: %s", e, exc_info=True)
                return

