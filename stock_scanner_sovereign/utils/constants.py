# utils/constants.py
# Canonical Schema for 4-Layer Architecture (Sovereign Dashboard)

# Fixed-width binary schema for SHM (mmap). Live snapshot extras (e.g. brk_lvl) go to live_state — see docs/architecture_data_layers.md
# ensures O(1) alignment for NumPy/Polars vectorization.
SIGNAL_DTYPE = [
    ('symbol', 'S40'),      # NSE:NIFTYMIDCAP100-INDEX (max headroom)
    ('ltp', 'f8'),         # Last Transaction Price
    ('mrs', 'f8'),         # Real-time Weekly Mansfield RS (Layer 2)
    ('mrs_prev', 'f8'),    # Last Week's Baseline MRS (Layer 1/2 Sync)
    ('mrs_daily', 'f8'),   # Daily Drift of MRS (Since Market Open)
    ('rs_rating', 'i4'),   # RS Percentile (0-100)
    ('change_pct', 'f8'),  # Daily change % 
    ('profile', 'S20'),    # Trading Profile (Value/Growth)
    ('status', 'S25'),     # Master: BUY | TRENDING | NOT TRENDING (weekly mRS vs 0); not breakout tape
    ('rv', 'f8'),           # Relative Volume (Current vs Avg)
    ('heartbeat', 'f8'),   # Unix micro-pulse for staleness
    ('price_up', 'i1'),    # 1 if LTP > Previous Week's close
    ('price_down', 'i1')   # 1 if LTP < Previous Week's close
]

# Dashboard RS benchmark picker + Layer-1 universe_members checks: only these two (NIFTY50 / NIFTY500 indices).
# RS math and reconciliation use the selected index symbol with `universe_members` for the matching universe.
DASHBOARD_BENCHMARK_MAP = {
    "Nifty 50": "NSE:NIFTY50-INDEX",
    "Nifty 500": "NSE:NIFTY500-INDEX",
}

# Full index registry: SHM bench slots, master pulse, BreakoutScanner bench buffer, legacy rs_math, etc.
# Do not use this for the Reflex benchmark panel — use DASHBOARD_BENCHMARK_MAP.
BENCHMARK_MAP = {
    "Nifty 50": "NSE:NIFTY50-INDEX",
    "Nifty 100": "NSE:NIFTY100-INDEX",
    "Nifty 500": "NSE:NIFTY500-INDEX",
    "Nifty Midcap 100": "NSE:NIFTYMIDCAP100-INDEX",
    "Nifty Smallcap 100": "NSE:NIFTYSMLCAP100-INDEX",
    "Nifty Smallcap 250": "NSE:NIFTY500-INDEX",
    "SME List": "NSE:NIFTY500-INDEX",
    "Microcap 250": "NSE:NIFTYMICROCAP250-INDEX",
    "Bank Nifty": "NSE:NIFTYBANK-INDEX",
    "All NSE Stocks": "NSE:NIFTY500-INDEX"
}

SYMBOL_GROUPS = {
    "Nifty 50": "data/nifty50.csv",
    "Nifty 100": "data/nifty100.csv",
    "Nifty 500": "data/nifty500.csv",
    "Nifty Midcap 100": "data/nifty_midcap100.csv",
    "Nifty Smallcap 100": "data/nifty_smallcap100.csv",
    "Nifty Smallcap 250": "data/nifty_smallcap250.csv",
    "SME List": "data/sme_list.csv",
    "Microcap 250": "data/microcap250.csv",
    "Bank Nifty": "data/banknifty.csv",
    "All NSE Stocks": "data/NSE_EQ.csv",
}

# Sidebar display name -> Postgres `universes.universe_id` / `universe_members.universe_id`
# (must match `seed_universes.py` and `DatabaseManager.get_symbols_by_universe`).
UNIVERSE_ID_BY_DISPLAY = {
    "Nifty 50": "NIFTY_50",
    "Nifty 100": "NIFTY_100",
    "Nifty 500": "NIFTY_500",
    "Nifty Midcap 100": "MIDCAP_100",
    "Nifty Smallcap 100": "SMALLCAP_100",
    "Nifty Smallcap 250": "SMALLCAP_250",
    "SME List": "SME_LIST",
    "Microcap 250": "MICROCAP_250",
    "Bank Nifty": "BANK_NIFTY",
    "All NSE Stocks": "ALL_NSE",
}

# CSV / DB membership validation (all 8 sidebar universes).
CANONICAL_MEMBERSHIP_UNIVERSES = tuple(SYMBOL_GROUPS.keys())

UNIVERSE_OPTIONS = list(SYMBOL_GROUPS.keys())
