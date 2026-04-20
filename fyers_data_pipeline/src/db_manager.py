import os
import logging
from sqlalchemy import create_engine, MetaData, Table, Column, String, TIMESTAMP, Boolean, ForeignKey, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _running_inside_docker() -> bool:
    return os.path.isfile("/.dockerenv")


def _postgres_host_for_runtime() -> str:
    """Compose uses DB_HOST=db; that hostname only resolves on the Docker network."""
    host = os.getenv("DB_HOST", "localhost")
    if host == "db" and not _running_inside_docker():
        logger.info(
            "DB_HOST=db is for Docker Compose; using localhost for host-side Python "
            "(ensure Postgres port 5432 is published)."
        )
        return "localhost"
    return host


class DatabaseManager:
    """
    Handles connections and operations with PostgreSQL.
    """
    def __init__(self, config_path: str = None):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        repo_root = os.path.dirname(project_root)
        load_dotenv(config_path or os.path.join(project_root, "config", ".env"))
        for extra in (
            os.path.join(repo_root, "stock_scanner_sovereign", ".env"),
            os.path.join(repo_root, ".env"),
        ):
            if os.path.isfile(extra):
                load_dotenv(extra, override=True)

        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        host = _postgres_host_for_runtime()
        port = os.getenv('DB_PORT', '5432')
        name = os.getenv('DB_NAME')

        db_url = os.getenv("DATABASE_URL")
        if db_url and "@db:" in db_url and not _running_inside_docker():
            db_url = db_url.replace("@db:", "@localhost:")
            logger.info("Adjusted DATABASE_URL host db -> localhost for host-side runs.")

        if not db_url or ("localhost" in db_url and host != "localhost"):
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = MetaData()

    def ensure_symbols_pipeline_columns(self) -> None:
        """
        Idempotent DDL for columns expected by backfill / update_eod.
        create_all() does not ALTER existing tables, so older DB volumes need this.
        """
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE symbols ADD COLUMN IF NOT EXISTS last_historical_sync TIMESTAMP"
                )
            )

    def initialize_schema(self):
        """Standard Sovereign Schema: Ensures all layers have their target tables."""
        from sqlalchemy import Column, String, Float, Integer, Date, TIMESTAMP, Boolean, ForeignKey, UniqueConstraint

        # Layer 1: Core Identification
        symbols = Table('symbols', self.metadata,
            Column('symbol_id', String, primary_key=True),
            Column('symbol_token', String),
            Column('description', String),
            Column('exchange', String),
            Column('is_active', Boolean, default=True),
            Column('last_historical_sync', TIMESTAMP, nullable=True),
        )
        
        # Layer 2: Historical OHLCV (The missing 'prices' table)
        prices = Table('prices', self.metadata,
            Column('symbol', String, primary_key=True),
            Column('timestamp', TIMESTAMP, primary_key=True),
            Column('timeframe', String, primary_key=True),
            Column('open', Float),
            Column('high', Float),
            Column('low', Float),
            Column('close', Float),
            Column('volume', Float)
        )
        
        # Layer 3: Persistence/Dashboard (live_state)
        live_state = Table('live_state', self.metadata,
            Column('symbol', String, primary_key=True),
            Column('last_price', Float),
            Column('mrs', Float),
            Column('rs_rating', Integer),
            Column('status', String),
            Column('brk_lvl', Float),
            Column('mrs_prev_day', Float),
        )
        
        # Layer 4: Analytics (rs_ratings)
        rs_ratings = Table('rs_ratings', self.metadata,
            Column('symbol', String, primary_key=True),
            Column('date', Date, primary_key=True),
            Column('rs_rating', Integer),
            Column('mrs', Float)
        )

        # Helper: Universes
        universes = Table('universes', self.metadata,
            Column('universe_id', String, primary_key=True),
            Column('universe_name', String)
        )
        universe_members = Table('universe_members', self.metadata,
            Column('universe_id', String, ForeignKey('universes.universe_id'), primary_key=True),
            Column('symbol_id', String, ForeignKey('symbols.symbol_id'), primary_key=True)
        )
        
        try:
            self.metadata.create_all(self.engine)
            self.ensure_symbols_pipeline_columns()
            logger.info("📡 [DB] All Architecture-Blueprint tables initialized successfully.")
        except Exception as e:
            logger.error(f"❌ [DB] Schema initialization failed: {e}")
            raise
