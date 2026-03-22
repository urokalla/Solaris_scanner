import os
import sys
import logging

# Add the current directory to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.db_manager import DatabaseManager
from scripts.seed_symbols import main as seed_main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize():
    logger.info("🛠️ Starting Database Initialization...")
    
    db = DatabaseManager()
    
    # 1. Create tables
    try:
        db.initialize_schema()
        logger.info("✅ Schema initialized.")
    except Exception as e:
        logger.error(f"❌ Schema initialization failed: {e}")
        sys.exit(1)
        
    # 2. Seed symbols
    try:
        logger.info("🌱 Seeding symbols (this may take a minute)...")
        seed_main()
        logger.info("✅ Seeding complete.")
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        # Don't exit here, maybe some tables were seeded
        
    logger.info("🚀 Database is ready!")

if __name__ == "__main__":
    initialize()
