import os, logging
try: from .database import DatabaseManager
except: from backend.database import DatabaseManager

_SYMBOL_CACHE = {}

def get_nifty_symbols(index_name):
    """Sovereign Symbol Loader: Database-First (Zero-CSV)."""
    global _SYMBOL_CACHE
    if index_name in _SYMBOL_CACHE: return _SYMBOL_CACHE[index_name]
    
    try:
        db = DatabaseManager()
        symbols = db.get_symbols_by_universe(index_name)
        logging.info(f"🔋 [Symbols] Loaded {len(symbols)} symbols for {index_name} from DB.")
        res = sorted(list(set(symbols)))
        _SYMBOL_CACHE[index_name] = res
        return res
    except Exception as e:
        logging.error(f"Symbol Loader DB Error: {e}")
        return []
