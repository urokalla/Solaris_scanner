import os, psycopg2, numpy as np, logging
from utils.constants import UNIVERSE_ID_BY_DISPLAY

logger = logging.getLogger(__name__)
from psycopg2.extras import execute_values
from psycopg2.pool import ThreadedConnectionPool
from datetime import datetime
from contextlib import contextmanager

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
        conn = DatabaseManager._pool.getconn()
        try:
            yield conn
        finally:
            DatabaseManager._pool.putconn(conn)

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
                return [r[0] for r in cur.fetchall()]

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

    def ensure_live_state_brk_column(self):
        """Align Layer 3 live_state with sidecar: pivot breakout level (see docs/architecture_data_layers.md)."""
        if DatabaseManager._brk_lvl_column_checked:
            return
        try:
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
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    execute_values(
                        cur,
                        """
                        INSERT INTO live_state (symbol, brk_lvl) VALUES %s
                        ON CONFLICT (symbol) DO UPDATE SET brk_lvl = EXCLUDED.brk_lvl
                        """,
                        [(s, float(b)) for s, b in rows],
                    )
                    conn.commit()
        except Exception as e:
            logger.error("Database: upsert_brk_lvls failed: %s", e, exc_info=True)

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
                    cur.execute("UPDATE live_state SET mrs_prev_day = mrs WHERE mrs IS NOT NULL")
                    n = cur.rowcount
                    conn.commit()
                logger.info("Database: EOD snapshot mrs_prev_day <- mrs (%s rows)", n)
        except Exception as e:
            logger.error("Database: snapshot_mrs_prev_day_from_current_mrs failed: %s", e, exc_info=True)
