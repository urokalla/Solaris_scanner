import sys, os, glob, pandas as pd, logging, requests
from sqlalchemy import text

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.db_manager import DatabaseManager
from src.utils import setup_logging

logger = setup_logging("seed_symbols", "seeds.log")

def sync_fyers_master(db):
    """Download and sync with the official Fyers NSE_CM Master."""
    url = "https://public.fyers.in/sym_details/NSE_CM.csv"
    try:
        logger.info(f"📡 Downloading official Fyers Master: {url}")
        df = pd.read_csv(url, header=None)
        with db.Session() as session:
            session.execute(text("UPDATE symbols SET is_active = FALSE"))
            for _, r in df.iterrows():
                sid, desc = str(r[9]).strip(), str(r[1]).strip()
                if sid.startswith("NSE:"):
                    session.execute(text("""
                        INSERT INTO symbols (symbol_id, description, exchange, instrument_type, is_active)
                        VALUES (:sid, :desc, 'NSE', 'EQ', TRUE)
                        ON CONFLICT (symbol_id) DO UPDATE SET description = EXCLUDED.description, is_active = TRUE
                    """), {"sid": sid, "desc": desc})
            session.commit()
        logger.info(f"✅ Synced {len(df)} symbols from official Fyers Master.")
    except Exception as e: logger.error(f"Fyers Master Sync Fail: {e}")

def seed_universes(db):
    """Seed the universes table."""
    universes = [
        ("NIFTY_50", "NIFTY 50"),
        ("BANK_NIFTY", "BANK NIFTY"),
        ("NIFTY_100", "NIFTY 100"), # Added
        ("MIDCAP_100", "MIDCAP 100"),
        ("SMALLCAP_100", "SMALLCAP 100"),
        ("MIDCAP_250", "MIDCAP 250"),
        ("MICROCAP_250", "MICROCAP_250"),
        ("NIFTY_500", "NIFTY 500"),
        ("ALL_NSE", "All NSE Listed Stocks")
    ]
    with db.Session() as session:
        for u_id, u_name in universes:
            session.execute(text("INSERT INTO universes (universe_id, universe_name) VALUES (:id, :name) ON CONFLICT (universe_id) DO NOTHING"), {"id": u_id, "name": u_name})
        session.commit()
    logger.info("Universes seeded.")

def seed_symbols_from_csv(db, file_path, universe_id):
    """Seed symbols from a CSV and link to a universe."""
    if not os.path.exists(file_path):
        logger.warning(f"File {file_path} not found. Skipping.")
        return

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return

    # Dynamic column mapping
    sym_col = next((c for c in df.columns if 'Symbol' in c or 'Ticker' in c), None)
    desc_col = next((c for c in df.columns if 'Name' in c or 'Description' in c or 'Company' in c), None)

    if not sym_col:
        logger.error(f"Could not find Symbol column in {file_path}")
        return

    with db.Session() as session:
        for idx, row in df.iterrows():
            symbol = str(row[sym_col]).strip()
            if not symbol or symbol == 'nan': continue
            
            # Format according to Fyers: NSE:SYMBOL-EQ
            # Some symbols might already have exchange prefix, handle that
            if ":" in symbol:
                fyers_symbol = symbol
            else:
                fyers_symbol = f"NSE:{symbol}-EQ"
                
            description = str(row[desc_col]) if desc_col else fyers_symbol
            
            # Insert symbol
            session.execute(text("""
                INSERT INTO symbols (symbol_id, description, exchange, instrument_type, is_active)
                VALUES (:sid, :desc, 'NSE', 'EQ', TRUE)
                ON CONFLICT (symbol_id) DO NOTHING
            """), {"sid": fyers_symbol, "desc": description})
            
            # Link to universe
            session.execute(text("""
                INSERT INTO universe_members (universe_id, symbol_id)
                VALUES (:uid, :sid)
                ON CONFLICT DO NOTHING
            """), {"uid": universe_id, "sid": fyers_symbol})
            
        session.commit()
    logger.info(f"Seeded symbols from {file_path} into universe {universe_id}.")

def seed_symbols_from_parquet(db, parquet_dir, universe_id="ALL_NSE"):
    """
    30-YEAR ENGINEER FIX: Scans Parquet files to seed the ALL_NSE universe.
    This replaces the missing all_nse_stocks.csv.
    """
    if not os.path.exists(parquet_dir):
        logger.warning(f"Parquet directory {parquet_dir} not found. Skipping.")
        return

    # Find all NSE_*.parquet files
    files = sorted(glob.glob(os.path.join(parquet_dir, "NSE_*.parquet")))
    if not files:
        logger.warning(f"No Parquet files found in {parquet_dir}.")
        return

    with db.Session() as session:
        for f in files:
            # Map filename NSE_SBIN_EQ.parquet -> NSE:SBIN-EQ
            base = os.path.basename(f)
            symbol_id = base.replace('NSE_', 'NSE:').replace('_EQ.parquet', '-EQ').replace('_INDEX.parquet', '-INDEX')
            
            # Simple description since we don't have the CSV description
            description = symbol_id.replace('NSE:', '').replace('-EQ', '').replace('-', ' ')
            
            # 1. Ensure symbol exists
            session.execute(text("""
                INSERT INTO symbols (symbol_id, description, exchange, instrument_type, is_active)
                VALUES (:sid, :desc, 'NSE', 'EQ', TRUE)
                ON CONFLICT (symbol_id) DO NOTHING
            """), {"sid": symbol_id, "desc": description})
            
            # 2. Link to ALL_NSE universe
            session.execute(text("""
                INSERT INTO universe_members (universe_id, symbol_id)
                VALUES (:uid, :sid)
                ON CONFLICT DO NOTHING
            """), {"uid": universe_id, "sid": symbol_id})
            
        session.commit()
    logger.info(f"Sync complete: Seeded {len(files)} symbols from Parquet files into universe {universe_id}.")

def seed_indices(db):
    """Seed indices directly by their Fyers symbols."""
    indices = [
        ("NSE:NIFTY50-INDEX", "NIFTY 50", "NIFTY_50"),
        ("NSE:NIFTYBANK-INDEX", "BANK NIFTY", "BANK_NIFTY"),
        ("NSE:MIDCAP100-INDEX", "MIDCAP 100", "MIDCAP_100"),
        ("NSE:SMALLCAP100-INDEX", "SMALLCAP 100", "SMALLCAP_100"),
        ("NSE:NIFTY500-INDEX", "NIFTY 500", "NIFTY_500"),
    ]
    with db.Session() as session:
        for f_sym, desc, u_id in indices:
            session.execute(text("""
                INSERT INTO symbols (symbol_id, description, exchange, instrument_type, is_active)
                VALUES (:sid, :desc, 'NSE', 'IDX', TRUE)
                ON CONFLICT (symbol_id) DO NOTHING
            """), {"sid": f_sym, "desc": desc})
            
            session.execute(text("""
                INSERT INTO universe_members (universe_id, symbol_id)
                VALUES (:uid, :sid)
                ON CONFLICT DO NOTHING
            """), {"uid": u_id, "sid": f_sym})
        session.commit()
    logger.info("Core indices seeded.")

def main():
    db = DatabaseManager()
    seed_universes(db)
    sync_fyers_master(db)
    seed_indices(db)
    
    # Mapping universes to files
    # 30-YEAR ENGINEER FIX: Use correct path based on Docker volume mount
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(os.path.join(script_dir, "../stock_scanner_sovereign/data"))
    
    mappings = [
        ("nifty50.csv", "NIFTY_50"),
        ("nifty100.csv", "NIFTY_100"),
        ("nifty_midcap100.csv", "MIDCAP_100"),
        ("nifty_smallcap100.csv", "SMALLCAP_100"),
        ("microcap250.csv", "MICROCAP_250"),
        ("nifty500.csv", "NIFTY_500")
    ]
    
    for csv_file, u_id in mappings:
        full_path = os.path.join(data_dir, csv_file)
        seed_symbols_from_csv(db, full_path, u_id)

    # --- 30-YEAR ENGINEER FIX: Auto-Sync ALL_NSE from Parquet ---
    # Since all_nse_stocks.csv is missing, we scan the actual Parquet files.
    hist_dir = os.path.abspath(os.path.join(script_dir, "../data/historical"))
    seed_symbols_from_parquet(db, hist_dir, "ALL_NSE")

if __name__ == "__main__":
    main()
